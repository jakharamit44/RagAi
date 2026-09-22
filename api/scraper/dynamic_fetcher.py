"""
Dynamic Web Fetcher with DevExpress ASP.NET and Scrapling / Playwright Integration.
Handles client-side JavaScript rendering, DevExpress ASPxGridView multi-page pagination,
and bot protection for academic university portals.
"""

import asyncio
import logging
import re
import urllib.parse
from typing import Dict, Any, List, Optional, Tuple, Set
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Check Playwright availability
PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    pass

# Check Scrapling availability
SCRAPLING_AVAILABLE = False
try:
    import scrapling
    from scrapling import Selector
    SCRAPLING_AVAILABLE = True
except ImportError:
    pass


class DynamicWebFetcher:
    """
    High-fidelity dynamic browser fetcher.
    Executes client-side JavaScript, steps through DevExpress ASPxGridView paginated tables,
    and captures all hidden notices, examination datesheets, and document links.
    """

    def __init__(self, headless: bool = True):
        self.headless = headless
        self._browser = None
        self._playwright = None

    @staticmethod
    def is_devexpress_or_dynamic_url(url: str) -> bool:
        """Determines if a URL is an ASP.NET WebForms / DevExpress dynamic page."""
        lower = url.lower()
        if any(k in lower for k in [
            "eventpage.aspx",
            "results.mdu.ac.in",
            "result",
            "depthome.aspx",
            "officers.aspx",
            "syllabus.aspx",
            "syallbus.aspx"
        ]):
            return True
        return False

    @staticmethod
    def detect_devexpress_grid_in_html(html_text: str) -> bool:
        """Quickly detects if raw HTML contains DevExpress ASPxGridView controls."""
        if not html_text:
            return False
        lower = html_text.lower()
        return ("aspxclientgridview" in lower or
                "dxgvtable" in lower or
                "dxgvcontrol" in lower or
                "aspxgridview" in lower)

    async def fetch_page_rendered_html(
        self,
        url: str,
        timeout_ms: int = 30000,
        wait_for_selector: Optional[str] = None
    ) -> Optional[str]:
        """
        Fetches a single web page with full JavaScript execution and returns the rendered HTML.
        """
        if not PLAYWRIGHT_AVAILABLE:
            logger.warning("Playwright is not available for dynamic page fetch.")
            return None

        browser = None
        context = None
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=self.headless)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                )
                page = await context.new_page()
                await page.goto(url, wait_until="networkidle", timeout=timeout_ms)

                if wait_for_selector:
                    try:
                        await page.wait_for_selector(wait_for_selector, timeout=5000)
                    except Exception:
                        pass

                html = await page.content()
                return html
        except Exception as e:
            logger.error(f"Dynamic fetch error for {url}: {e}")
            return None
        finally:
            if context:
                try:
                    await context.close()
                except Exception:
                    pass
            if browser:
                try:
                    await browser.close()
                except Exception:
                    pass

    @staticmethod
    def _extract_grid_rows(html: str, base_url: str) -> Tuple[List[List[str]], List[Dict[str, Any]], Set[str]]:
        """Extracts rows, cell links, and document URLs from an ASPxGridView table."""
        rows = []
        all_rows = []
        doc_links = set()
        soup = BeautifulSoup(html, "html.parser")
        main_table = soup.find(id=re.compile(r"ASPxGridView\d*_DXMainTable", re.I)) or soup.find(class_=re.compile(r"dxgvTable", re.I))
        if main_table:
            for tr in main_table.find_all("tr"):
                if tr.find("th") or "dxgvHeader" in tr.get("class", []):
                    continue
                tds = tr.find_all("td")
                if len(tds) < 3:
                    continue
                cells = []
                row_pdf = ""
                for td in tds:
                    a = td.find("a", href=True)
                    if a:
                        href = urllib.parse.urljoin(base_url, a["href"])
                        text = a.get_text(strip=True) or "Download"
                        if ".pdf" in href.lower():
                            row_pdf = href
                            doc_links.add(href)
                        elif any(ext in href.lower() for ext in [".docx", ".doc", ".xlsx"]):
                            doc_links.add(href)
                        cells.append(f"[{text}]({href})")
                    else:
                        clean_text = td.get_text(separator=" ", strip=True).replace("|", "\\|")
                        cells.append(clean_text)
                if any(cells) and len(cells) >= 3:
                    if "Sr No" not in cells[0] and "Sr." not in cells[0] and len("".join(cells).strip()) > 5:
                        rows.append(cells)
                        all_rows.append({"cells": cells, "pdf_url": row_pdf})
        return rows, all_rows, doc_links

    async def fetch_devexpress_grid_all_pages(
        self,
        url: str,
        max_pages: int = 15,
        timeout_ms: int = 30000
    ) -> Dict[str, Any]:
        """
        Navigates to an ASP.NET DevExpress page (e.g. EventPage.aspx?id=2),
        identifies the ASPxGridView control, automatically steps through all available pages,
        and aggregates all table rows and PDF/DOC document links across every page.
        """
        if not PLAYWRIGHT_AVAILABLE:
            logger.warning("Playwright unavailable. Skipping DevExpress multi-page extraction.")
            return {"success": False, "reason": "playwright_unavailable"}

        result: Dict[str, Any] = {
            "success": False,
            "title": "",
            "total_grid_pages": 1,
            "pages_extracted": 0,
            "total_rows": 0,
            "markdown_table": "",
            "discovered_doc_links": [],
            "all_rows": [],
            "merged_html": ""
        }

        all_doc_links: Set[str] = set()
        aggregated_rows: List[List[str]] = []
        seen_row_signatures: Set[str] = set()
        html_snapshots: List[str] = []

        browser = None
        context = None
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=self.headless)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                )
                page = await context.new_page()

                logger.info(f"Dynamic navigation to DevExpress portal: {url}")
                await page.goto(url, wait_until="networkidle", timeout=timeout_ms)

                page_title = await page.title()
                result["title"] = page_title.strip() if page_title else "University Portal"

                # Extract initial page (page 1) rows immediately
                init_html = await page.content()
                html_snapshots.append(init_html)
                p_rows, p_all, p_links = self._extract_grid_rows(init_html, url)
                for r, ar in zip(p_rows, p_all):
                    sig = "||".join(r[:3])
                    if sig not in seen_row_signatures:
                        seen_row_signatures.add(sig)
                        aggregated_rows.append(r)
                        result["all_rows"].append(ar)
                all_doc_links.update(p_links)

                # Inspect DevExpress ASPxGridView controls on page
                grid_info = await page.evaluate("""() => {
                    if (typeof ASPxClientControl === 'undefined') return null;
                    const collection = ASPxClientControl.GetControlCollection();
                    if (!collection) return null;
                    
                    const candidates = [
                        'ContentPlaceHolder1_EventAdmin_ASPxGridView1',
                        'ASPxGridView1',
                        'gvDatesheet',
                        'gvNotices'
                    ];
                    
                    for (const name of candidates) {
                        const grid = collection.GetByName(name);
                        if (grid && typeof grid.GetPageCount === 'function') {
                            return {
                                name: name,
                                pageCount: grid.GetPageCount(),
                                pageIndex: grid.GetPageIndex(),
                                uniqueID: grid.uniqueID
                            };
                        }
                    }
                    
                    for (const key in collection.elements) {
                        const ctrl = collection.elements[key];
                        if (ctrl && typeof ctrl.GetPageCount === 'function') {
                            return {
                                name: ctrl.name || key,
                                pageCount: ctrl.GetPageCount(),
                                pageIndex: ctrl.GetPageIndex(),
                                uniqueID: ctrl.uniqueID
                            };
                        }
                    }
                    return null;
                }""")

                total_pages = 1
                grid_name = None
                if grid_info:
                    total_pages = min(grid_info.get("pageCount", 1), max_pages)
                    grid_name = grid_info.get("name")
                    result["total_grid_pages"] = grid_info.get("pageCount", 1)
                    logger.info(f"Detected DevExpress grid '{grid_name}' with {grid_info.get('pageCount')} total pages. Crawling up to {total_pages} pages.")

                # Iterate through pages using NextPage() and capture rows at each page step
                for page_idx in range(1, total_pages):
                    if not grid_name:
                        break
                    try:
                        prev_row_count = await page.evaluate("() => document.querySelectorAll('.dxgvDataRow_iOS, [class*=\"dxgvDataRow\"]').length")
                        
                        await page.evaluate(f"() => ASPxClientControl.GetControlCollection().GetByName('{grid_name}').NextPage()")
                        
                        try:
                            await page.wait_for_function(
                                f"() => document.querySelectorAll('.dxgvDataRow_iOS, [class*=\"dxgvDataRow\"]').length > {prev_row_count}",
                                timeout=8000
                            )
                        except Exception:
                            await page.wait_for_timeout(1200)

                        # Extract rows from current page step
                        curr_html = await page.content()
                        p_rows, p_all, p_links = self._extract_grid_rows(curr_html, url)
                        new_found = 0
                        for r, ar in zip(p_rows, p_all):
                            sig = "||".join(r[:3])
                            if sig not in seen_row_signatures:
                                seen_row_signatures.add(sig)
                                aggregated_rows.append(r)
                                result["all_rows"].append(ar)
                                new_found += 1
                        all_doc_links.update(p_links)
                        if new_found == 0 and page_idx > 2:
                            logger.info(f"No new unique rows at page {page_idx}, stopping pagination.")
                            break
                    except Exception as nav_err:
                        logger.warning(f"Error paging DevExpress grid with NextPage(): {nav_err}")
                        break

                result["pages_extracted"] = total_pages
                result["total_rows"] = len(aggregated_rows)
                result["discovered_doc_links"] = sorted(list(all_doc_links))

                # Build consolidated Markdown table across all collected pages
                if aggregated_rows:
                    max_cols = max(len(r) for r in aggregated_rows)
                    header = ["Sr No", "Notification / Datesheet Title", "Notice No", "Date", "Download", "Department / Branch"]
                    while len(header) < max_cols:
                        header.append(f"Col {len(header)+1}")
                    header = header[:max_cols]

                    table_lines = [
                        "| " + " | ".join(header) + " |",
                        "| " + " | ".join(["---"] * max_cols) + " |"
                    ]
                    for r in aggregated_rows:
                        padded_row = list(r)
                        while len(padded_row) < max_cols:
                            padded_row.append("")
                        table_lines.append("| " + " | ".join(padded_row[:max_cols]) + " |")

                    result["markdown_table"] = "\n".join(table_lines)

                result["merged_html"] = html_snapshots[0] if html_snapshots else ""
                result["success"] = True

        except Exception as e:
            logger.error(f"Failed to fetch DevExpress grid from {url}: {e}")
            result["success"] = False
            result["reason"] = str(e)
        finally:
            if context:
                try:
                    await context.close()
                except Exception:
                    pass
            if browser:
                try:
                    await browser.close()
                except Exception:
                    pass

        return result


# Singleton instance
dynamic_fetcher = DynamicWebFetcher()
