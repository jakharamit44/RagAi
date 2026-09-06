import os
from typing import Tuple

class FormatDetector:
    """
    Detects file MIME type, text density, image presence, and routes to appropriate parser / OCR engine.
    Differentiates between born_digital, scanned, and handwritten documents.
    Reference: Phase 1 & Section 246 of technical plan.
    """

    @staticmethod
    def detect_category(file_path: str) -> Tuple[str, str]:
        """
        Returns: (doc_type, recommended_engine)
        doc_type: 'born_digital' | 'scanned' | 'handwritten'
        """
        ext = os.path.splitext(file_path)[1].lower()
        fname_lower = os.path.basename(file_path).lower()

        is_handwriting_hint = any(
            k in fname_lower for k in [
                "handwritten", "hand_written", "handwriting", "hw_notes",
                "handwritten_notes", "notes_handwritten", "exam_copy", "answer_sheet"
            ]
        )

        if ext in [".docx", ".doc", ".pptx", ".xlsx", ".txt", ".md"]:
            return "born_digital", "native_structured"

        if ext in [".png", ".jpg", ".jpeg", ".tiff", ".bmp"]:
            if is_handwriting_hint:
                return "handwritten", "rapidocr_handwritten"
            return "scanned", "rapidocr_printed"

        if ext == ".pdf":
            try:
                import pypdf
                reader = pypdf.PdfReader(file_path)
                total_pages = len(reader.pages)
                if total_pages == 0:
                    return "born_digital", "pypdf"

                # Check PDF producer and creator metadata
                meta = reader.metadata or {}
                prod = str(meta.get("/Producer", "")).lower()
                creator = str(meta.get("/Creator", "")).lower()
                scanner_producers = [
                    "scanner", "fine reader", "finereader", "abbyy", "epson",
                    "canon", "pdf-xchange", "ilovepdf", "pdfium", "corel",
                    "adobe scan", "camscanner", "docscanner"
                ]
                is_scan_producer = any(sp in prod or sp in creator for sp in scanner_producers)

                pages_to_check = min(3, total_pages)
                has_full_page_raster = False
                total_native_chars = 0
                total_images = 0
                total_fonts = 0

                for idx in range(pages_to_check):
                    page = reader.pages[idx]
                    txt = (page.extract_text() or "").strip()
                    total_native_chars += len(txt)

                    # Check embedded vector fonts
                    try:
                        res = page.get("/Resources", {})
                        if "/Font" in res:
                            total_fonts += len(res["/Font"].keys())
                    except Exception:
                        pass

                    imgs = getattr(page, "images", [])
                    total_images += len(imgs)
                    for im in imgs:
                        try:
                            w, h = im.image.width, im.image.height
                            # True full-page scan check (high resolution raster covering the page)
                            if (w >= 600 and h >= 600 and (w * h) >= 400000) or (w >= 1000 and h >= 1000):
                                has_full_page_raster = True
                                break
                        except Exception:
                            pass
                    if has_full_page_raster:
                        break

                avg_native_chars = total_native_chars / max(pages_to_check, 1)

                if has_full_page_raster or is_scan_producer:
                    if is_handwriting_hint:
                        return "handwritten", "rapidocr_handwritten"
                    return "scanned", "rapidocr_printed"
                elif total_fonts >= 2 and avg_native_chars >= 50:
                    return "born_digital", "pypdf"
                elif avg_native_chars < 50 and total_images > 0:
                    if is_handwriting_hint:
                        return "handwritten", "rapidocr_handwritten"
                    return "scanned", "rapidocr_printed"
                else:
                    return "born_digital", "pypdf"

            except Exception:
                if is_handwriting_hint:
                    return "handwritten", "rapidocr_handwritten"
                return "born_digital", "pypdf"

        return "born_digital", "text_fallback"
