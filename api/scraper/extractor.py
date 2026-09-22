import re
import logging
import urllib.parse
from typing import Dict, Any, List, Tuple, Optional, Set
from bs4 import BeautifulSoup
import trafilatura
from .url_normalizer import UrlNormalizer

from .banner_ocr import banner_ocr_pipeline
import httpx

logger = logging.getLogger(__name__)

class PageExtractor:
    """
    Extracts high-fidelity academic content, Markdown tables, banner image announcements via OCR,
    and document links from HTML web pages.
    Combines Trafilatura (boilerplate stripping) with BeautifulSoup (fallback, link harvesting, and banner OCR).
    """

    @staticmethod
    async def extract_html_content(
        html_bytes: bytes,
        page_url: str,
        content_type: str = "text/html",
        allowed_domains: Optional[List[str]] = None,
        ocr_banners: bool = True,
        client: Optional[httpx.AsyncClient] = None
    ) -> Dict[str, Any]:
        """
        Extracts clean text/markdown, metadata, and banner OCR announcements from raw HTML.
        Handles BOM, UTF-8, fallback encodings, and visual announcements.
        """
        # Guard against binary archives, executables, or oversized payloads being treated as HTML
        if len(html_bytes) > 5 * 1024 * 1024:
            logger.warning(f"Skipping oversized payload ({len(html_bytes)/(1024*1024):.1f} MB) for HTML parsing: {page_url}")
            return {"title": "Oversized Asset", "text": "", "banner_announcements": []}

        # Check binary magic signatures
        binary_sigs = (b"Rar!", b"PK\x03\x04", b"7z\xbc\xaf\x27\x1c", b"\x1f\x8b", b"BZh", b"\xfd7zXZ", b"MZ", b"%PDF")
        if any(html_bytes.startswith(sig) for sig in binary_sigs) or b"\x00" in html_bytes[:1024]:
            logger.info(f"Skipping binary non-HTML payload detected at {page_url}")
            return {"title": "Binary Asset", "text": "", "banner_announcements": []}

        # 1. Decode HTML handling possible UTF-8 BOM
        try:
            html_text = html_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            try:
                # Strictly try utf-8 errors=replace rather than indiscriminate latin-1
                html_text = html_bytes.decode("utf-8", errors="replace")
            except Exception:
                return {"title": "Unreadable Content", "text": "", "banner_announcements": []}

        # 2. Extract and refine title
        title = ""
        soup = None
        try:
            soup = BeautifulSoup(html_text, "html.parser")
            title_tag = soup.find("title")
            if title_tag and title_tag.string:
                title = title_tag.string.strip()
        except Exception as e:
            logger.debug(f"Soup title parse note: {e}")

        # 3. Trafilatura boilerplate-free extraction
        clean_markdown = None
        try:
            clean_markdown = trafilatura.extract(
                html_text,
                url=page_url,
                include_tables=True,
                include_links=True,
                include_images=False,
                output_format="markdown",
                favor_recall=True,
                deduplicate=True
            )
        except Exception as e:
            logger.warning(f"Trafilatura extraction warning for {page_url}: {e}")

        # 4. Fallback to BeautifulSoup if Trafilatura yields sparse text
        if not clean_markdown or len(clean_markdown.strip()) < 80:
            if soup is None:
                soup = BeautifulSoup(html_text, "html.parser")
            
            # Remove script, style, nav, footer
            for element in soup(["script", "style", "nav", "footer", "header", "noscript"]):
                element.decompose()

            # Find main content container if available
            main_elem = soup.find("main") or soup.find("article") or soup.find(id=re.compile(r"content|main|body", re.I)) or soup.body
            if main_elem:
                clean_markdown = main_elem.get_text(separator="\n", strip=True)
            else:
                clean_markdown = soup.get_text(separator="\n", strip=True)

        # 4.5. ASP.NET University Portal & Structured Container Enrichment
        # Trafilatura frequently drops ASP.NET sidebar cards, officer profile blocks (#vcCont),
        # tables, and dynamic form panels. We inspect and recover these vital academic details.
        if soup is not None:
            recovered_blocks = []
            
            # (a) Refine generic "M.D University" titles using breadcrumbs, ASP.NET headings, or specific routes
            lower_title = title.lower().strip()
            if not title or lower_title in ["m.d university", "mdu rohtak", "maharshi dayanand university", ""]:
                # Check department header first (DeptOfficeHeader_lblDeptName, etc.)
                dept_hdr = soup.find(id=re.compile(r"lblDeptName|lbldeptname", re.I))
                dept_name_str = dept_hdr.get_text(strip=True) if dept_hdr else ""

                # Check breadcrumbs next - standard across ASP.NET and modern CMS
                breadcrumb_elem = soup.find(class_=re.compile(r"breadcrumb|bread-crumb|crumbs", re.I)) or soup.find(id=re.compile(r"breadcrumb|crumbs", re.I))
                if breadcrumb_elem:
                    crumbs = [c.get_text(strip=True) for c in breadcrumb_elem.find_all(["li", "a", "span"]) if c.get_text(strip=True)]
                    crumbs = [c for c in crumbs if c not in [">", "/", "|", "»", "\\", "Home", "home"] and len(c) > 1]
                    if crumbs:
                        title = " - ".join(crumbs[-2:]) + " | MDU Rohtak"

                if not title or title.lower().strip() in ["m.d university", "mdu rohtak", "subscribe to alerts", "subscribe to alerts | mdu rohtak"]:
                    if "officers.aspx" in page_url.lower():
                        if "oid=1" in page_url.lower():
                            title = "Vice-Chancellor Office - Prof. Milap Punia | MDU Rohtak"
                        elif "oid=3" in page_url.lower():
                            title = "Chancellor Office - Prof. Ashim Kumar Ghosh | MDU Rohtak"
                        elif "oid=4" in page_url.lower():
                            title = "Registrar Office - Prof. Sandeep Bansal | MDU Rohtak"
                        elif "oid=5" in page_url.lower():
                            title = "Dean Academic Affairs | MDU Rohtak"
                        else:
                            title = "University Officers & Deans | MDU Rohtak"
                    elif "eventpage.aspx?id=2" in page_url.lower():
                        title = "Examination Datesheet | MDU Rohtak"
                    elif "eventpage.aspx?id=1015" in page_url.lower():
                        title = "Exam Notifications & Amendments | MDU Rohtak"
                    elif "eventpage.aspx?id=1018" in page_url.lower():
                        title = "Examination Schedule | MDU Rohtak"
                    elif "eventpage.aspx?id=1019" in page_url.lower():
                        title = "Exam Question Papers | MDU Rohtak"
                    elif "eventpage.aspx?id=1079" in page_url.lower():
                        title = "Important Key Dates for Admission and Notices | MDU Rohtak"
                    elif "dept=43" in page_url.lower():
                        title = "Centre for Distance and Online Education (CDOE / DDE) | MDU Rohtak"
                    elif "dept=44" in page_url.lower() or (dept_name_str and "computer centre" in dept_name_str.lower()):
                        title = "University Computer Centre (UCC) - Prof. Yudhvir Singh | MDU Rohtak"
                    elif dept_name_str:
                        title = f"{dept_name_str} | MDU Rohtak"
                    elif "admission" in page_url.lower():
                        title = "MDU Admissions Portal & Academic Programs"
                    else:
                        officer_name_elem = soup.find(id=re.compile(r"lblpaname|lblName", re.I))
                        officer_title_elem = soup.find(id=re.compile(r"lblOffice|lblDesig", re.I))
                        if officer_name_elem and officer_name_elem.get_text(strip=True):
                            name_str = officer_name_elem.get_text(strip=True)
                            desig_str = officer_title_elem.get_text(strip=True) if officer_title_elem else "Officer"
                            title = f"{desig_str} - {name_str} | MDU Rohtak"
                        else:
                            h1 = soup.find("h1") or soup.find("h2") or soup.find(id=re.compile(r"lblHeading|lblTitle|PageTitle", re.I))
                            if h1 and h1.get_text(strip=True):
                                title = f"{h1.get_text(strip=True)} | MDU Rohtak"

            # (b) Helper for markdown table conversion with full hyperlink retention
            def _is_calendar_or_nav_table(tbl) -> bool:
                tbl_id = (tbl.get("id") or "").lower()
                tbl_class = " ".join(tbl.get("class", [])).lower()
                if any(k in tbl_id or k in tbl_class for k in ["calendar", "datepicker", "dxecalendar", "dxcalendar", "radcalendar", "rcmaintable", "dxm-", "radmenu"]):
                    return True
                # Skip DevExpress filter row editors, popups, and dropdown lists
                if any(k in tbl_id or k in tbl_class for k in ["dxfreditor", "_ddd_c", "_ddd_l", "dxgvloadingpanel", "dxse"]):
                    return True
                tbl_text = tbl.get_text(separator=" ", strip=True).lower()
                if "sun mon tue wed thu fri sat" in tbl_text:
                    return True
                if "jan feb mar apr may jun jul aug sep oct nov dec" in tbl_text and "loading" in tbl_text:
                    return True
                return False

            def _cell_to_markdown(cell, base_url: str) -> str:
                """Converts a table cell to markdown, preserving clickable hyperlinks."""
                links = []
                for a in cell.find_all("a", href=True):
                    href = a["href"].strip()
                    if href and not href.lower().startswith("javascript:"):
                        full_url = urllib.parse.urljoin(base_url, href)
                        text = a.get_text(separator=" ", strip=True) or "Download"
                        links.append(f"[{text}]({full_url})")
                
                cell_text = cell.get_text(separator=" ", strip=True).replace("|", "\\|")
                if links:
                    # If anchor text is already in cell_text, substitute or append
                    return " ".join(links) if len(cell_text) < 40 else f"{cell_text} (" + ", ".join(links) + ")"
                return cell_text

            def _table_to_markdown(tbl) -> str:
                if _is_calendar_or_nav_table(tbl):
                    return ""
                rows = []
                for tr in tbl.find_all("tr"):
                    # Ignore DevExpress filter row editors
                    tr_class = " ".join(tr.get("class", [])).lower()
                    if "dxfreditor" in tr_class or "dxgvfilterrow" in tr_class:
                        continue
                    cells = [_cell_to_markdown(td, page_url) for td in tr.find_all(["th", "td"])]
                    if any(cells) and any(len(c.strip()) > 0 for c in cells):
                        rows.append(cells)
                if not rows:
                    return ""
                max_cols = max(len(r) for r in rows)
                if max_cols == 0:
                    return ""
                for r in rows:
                    while len(r) < max_cols:
                        r.append("")
                header = rows[0]
                lines = ["| " + " | ".join(header) + " |", "| " + " | ".join(["---"] * max_cols) + " |"]
                for r in rows[1:]:
                    lines.append("| " + " | ".join(r) + " |")
                return "\n".join(lines)

            # (c) Extract officer profile container (#vcCont)
            vc_cont = soup.find(id="vcCont")
            if vc_cont:
                # Capture all tables in vcCont
                for tbl in vc_cont.find_all("table"):
                    t_md = _table_to_markdown(tbl)
                    if t_md and t_md[:40] not in (clean_markdown or ""):
                        recovered_blocks.append(f"\n{t_md}\n")
                vc_raw = vc_cont.get_text(separator="\n", strip=True)
                if vc_raw:
                    lines = [ln.strip() for ln in vc_raw.split("\n") if ln.strip()]
                    clean_vc_lines = "\n".join(lines)
                    if clean_vc_lines and clean_vc_lines[:100] not in (clean_markdown or ""):
                        recovered_blocks.append(f"\n### University Leadership & Office Directory\n{clean_vc_lines}\n")

            # (c2) Extract Telerik / ASP.NET Multi-Tab Views (RadMultiPage) & Staff/Director Profiles
            multipage = soup.find(id=re.compile(r"RadMultiPage|ctl00.*MultiPage", re.I)) or soup.find(class_=re.compile(r"RadMultiPage", re.I))
            if multipage:
                tab_blocks = []
                for view in multipage.find_all(class_=re.compile(r"rmpView", re.I)):
                    view_id = view.get("id", "")
                    clean_name = re.sub(r"^.*?_", "", view_id)
                    clean_name = re.sub(r"([a-z])([A-Z])", r"\1 \2", clean_name).strip().title()

                    cards = []
                    for p_elem in view.find_all(id=re.compile(r"lblpaname|lblName|lblOfficer|lblDesig", re.I)):
                        p_name = re.sub(r"[\ue000-\uf8ff]", "", p_elem.get_text(strip=True))
                        if not p_name or len(p_name) < 2:
                            continue
                        parent = p_elem.find_parent(class_=re.compile(r"col-|row|card|box|panel|teacher", re.I)) or p_elem.parent
                        p_lines = [re.sub(r"[\ue000-\uf8ff]", "", ln).strip() for ln in parent.get_text(separator="\n", strip=True).split("\n") if len(ln.strip()) > 1]

                        biodata_a = parent.find("a", href=re.compile(r"biodata|profile|resume", re.I))
                        biodata_url = urllib.parse.urljoin(page_url, biodata_a["href"]) if biodata_a and biodata_a.get("href") else ""

                        card_str = f"**{p_name}**\n" + "\n".join([f"- {ln}" for ln in p_lines if ln != p_name and len(ln) > 1])
                        if biodata_url:
                            card_str += f"\n- Bio-Data: {biodata_url}"
                        if card_str not in cards:
                            cards.append(card_str)

                    view_copy = BeautifulSoup(str(view), "html.parser")
                    for el in view_copy(["script", "style", "table"]):
                        el.decompose()
                    view_raw = re.sub(r"[\ue000-\uf8ff]", "", view_copy.get_text(separator="\n", strip=True))
                    view_lines = [ln.strip() for ln in view_raw.split("\n") if len(ln.strip()) > 1]
                    view_summary = "\n".join(view_lines)

                    tab_parts = [f"### Tab: {clean_name}"]
                    if cards:
                        tab_parts.append("#### Department Officers, Faculty & Staff Profiles\n" + "\n\n".join(cards))
                    if view_summary and len(view_summary) > 40:
                        tab_parts.append("#### Details & Academic Information\n" + view_summary[:2000])

                    tab_blocks.append("\n\n".join(tab_parts))

                if tab_blocks:
                    joined_tabs = "\n\n".join(tab_blocks)
                    recovered_blocks.append(f"\n## Department Multi-Tab Sections & Directory\n{joined_tabs}\n")

            # (d) Extract Department / CDOE panels (e.g. DepartmentAboutUs, Home overview)
            dept_panel = soup.find(id=re.compile(r"DepartmentAboutUs|lblAboutDept|DeptMain", re.I))
            if dept_panel:
                d_raw = dept_panel.get_text(separator="\n", strip=True)
                if len(d_raw) > 80 and d_raw[:80] not in (clean_markdown or ""):
                    recovered_blocks.append(f"\n### Department Overview & Academic Programmes\n{d_raw}\n")

            # (e) Universal Table Extraction: Capture ANY table across MDU portals (schedules, fee matrices, seat intake, cutoffs, syllabus lists)
            seen_tables = set()
            for tbl in soup.find_all("table"):
                if vc_cont and tbl.find_parent(id="vcCont"):
                    continue
                rows = tbl.find_all("tr")
                if len(rows) < 2:
                    continue
                t_md = _table_to_markdown(tbl)
                if t_md and len(t_md.strip()) > 20 and t_md[:40] not in seen_tables:
                    seen_tables.add(t_md[:40])
                    # Check if table headers/first rows are already preserved in markdown
                    check_snip = rows[0].get_text(separator=" ", strip=True)[:35]
                    if not check_snip or check_snip not in (clean_markdown or "") or "|" not in (clean_markdown or ""):
                        recovered_blocks.append(f"\n### Official Schedules, Programmes & Table Data\n{t_md}\n")

            # (f) Official Portal Links & Document Resources Harvesting
            official_links = []
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                text = a.get_text(strip=True)
                if not text or len(text) < 3:
                    continue
                # Target key portal destinations and academic documents
                if any(k in href.lower() for k in ["samarth.edu.in", "admission", "student.mdu", "result", "exam", ".pdf", ".docx", ".xlsx"]):
                    full_url = urllib.parse.urljoin(page_url, href)
                    if full_url.startswith("http") and (text, full_url) not in official_links:
                        official_links.append((text, full_url))

            if official_links:
                links_md = "\n".join([f"- [{lbl}]({url})" for lbl, url in official_links[:25]])
                recovered_blocks.append(f"\n### Official Portal Links & Documents\n{links_md}\n")

            if recovered_blocks:
                clean_markdown = ((clean_markdown or "").strip() + "\n\n" + "\n".join(recovered_blocks)).strip()

        if not title:
            # Fallback title from first H1 or URL
            if soup:
                h1 = soup.find("h1")
                if h1 and h1.text:
                    title = h1.text.strip()
            if not title:
                title = page_url.split("/")[-1].split("?")[0] or "University Web Page"

        # 5. Banner and Slider Image Announcement OCR
        banner_announcements = []
        if ocr_banners:
            try:
                domains = allowed_domains or [UrlNormalizer.extract_root_domain(page_url) or "mdu.ac.in"]
                banner_announcements = await banner_ocr_pipeline.extract_banner_announcements(
                    html_text=html_text,
                    page_url=page_url,
                    allowed_domains=domains,
                    client=client
                )
                if banner_announcements:
                    banner_md = banner_ocr_pipeline.format_announcements_markdown(banner_announcements)
                    clean_markdown = (clean_markdown or "") + banner_md
            except Exception as ocr_err:
                logger.warning(f"Banner OCR processing note for {page_url}: {ocr_err}")

        return {
            "title": title,
            "text": clean_markdown or "",
            "char_count": len(clean_markdown or ""),
            "page_url": page_url,
            "banner_announcements": banner_announcements
        }

    @staticmethod
    def harvest_links(
        html_bytes: bytes,
        page_url: str,
        allowed_domains: List[str]
    ) -> Tuple[List[str], List[str]]:
        """
        Discovers all valid internal web page links (including subdomains) and downloadable academic documents.
        Returns:
            (valid_page_links, downloadable_doc_links)
        """
        page_links: Set[str] = set()
        doc_links: Set[str] = set()

        try:
            try:
                html_text = html_bytes.decode("utf-8-sig")
            except UnicodeDecodeError:
                html_text = html_bytes.decode("latin-1", errors="replace")

            soup = BeautifulSoup(html_text, "html.parser")

            # 1. Harvest from <a> tags
            for a_tag in soup.find_all("a", href=True):
                raw_href = a_tag["href"]
                normalized = UrlNormalizer.normalize(raw_href, base_url=page_url)
                if not normalized:
                    continue

                link_text = (a_tag.get_text() or "").strip()
                has_download_attr = a_tag.has_attr("download")

                # Detect if anchor text or attribute strongly signals a document
                is_doc = UrlNormalizer.is_document_url(normalized)
                if not is_doc and (has_download_attr or re.search(r"\b(?:pdf|download|syllabus|datesheet|circular|notice)\b", link_text, re.I)):
                    # Check if target URL has document keywords
                    if re.search(r"\.(?:pdf|docx?|xlsx?|pptx?)(?:[?#]|$)", raw_href, re.I):
                        is_doc = True

                if is_doc:
                    if UrlNormalizer.is_allowed_domain(normalized, allowed_domains):
                        doc_links.add(normalized)
                else:
                    if UrlNormalizer.is_skippable_url(normalized):
                        continue
                    if UrlNormalizer.is_allowed_domain(normalized, allowed_domains):
                        page_links.add(normalized)

            # 2. Harvest from onclick attributes (e.g. window.open('...pdf') or location.href='...pdf')
            for tag in soup.find_all(attrs={"onclick": True}):
                onclick_val = tag["onclick"]
                matches = re.findall(r"(?:window\.open|location\.href)\s*=\s*['\"]([^'\"]+)['\"]", onclick_val)
                matches += re.findall(r"window\.open\s*\(\s*['\"]([^'\"]+)['\"]", onclick_val)
                for raw_link in matches:
                    norm = UrlNormalizer.normalize(raw_link, base_url=page_url)
                    if norm and UrlNormalizer.is_document_url(norm) and UrlNormalizer.is_allowed_domain(norm, allowed_domains):
                        doc_links.add(norm)

            # 3. Inspect iframe src or embed src for PDFs
            for frame in soup.find_all(["iframe", "embed", "object"], src=True):
                norm = UrlNormalizer.normalize(frame["src"], base_url=page_url)
                if norm and UrlNormalizer.is_document_url(norm) and UrlNormalizer.is_allowed_domain(norm, allowed_domains):
                    doc_links.add(norm)

            # Also check <object data="...">
            for obj in soup.find_all("object", data=True):
                norm = UrlNormalizer.normalize(obj["data"], base_url=page_url)
                if norm and UrlNormalizer.is_document_url(norm) and UrlNormalizer.is_allowed_domain(norm, allowed_domains):
                    doc_links.add(norm)

        except Exception as e:
            logger.error(f"Error harvesting links from {page_url}: {e}")

        return sorted(list(page_links)), sorted(list(doc_links))
