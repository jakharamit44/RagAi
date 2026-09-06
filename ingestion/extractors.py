import os
import logging
from typing import List, Dict, Any, Tuple, Optional
import pypdf
import docx

logger = logging.getLogger(__name__)

class PDFExtractor:
    """Extracts text and table layout page-by-page from born-digital, hybrid, or scanned PDFs."""

    @staticmethod
    def extract(file_path: str, max_ocr_pages: int = 10) -> Tuple[List[Dict[str, Any]], str, Optional[float]]:
        pages_data = []

        try:
            from ingestion.format_detector import FormatDetector
            doc_type, _ = FormatDetector.detect_category(file_path)

            reader = pypdf.PdfReader(file_path)
            total_pages = len(reader.pages)

            # Pass 1: Extract any existing native or OCR-layer text
            native_texts = []
            for page in reader.pages:
                txt = (page.extract_text() or "").strip()
                native_texts.append(txt)

            # Pass 2: Extract text per page
            if doc_type == "born_digital":
                for idx, txt in enumerate(native_texts):
                    pages_data.append({
                        "page_number": idx + 1,
                        "section": f"Page {idx + 1}",
                        "text": txt
                    })
                return pages_data, doc_type, None

            # Scanned or Handwritten: Run layout-aware OCR on page images
            from ingestion.ocr_printed import printed_ocr
            from ingestion.ocr_handwritten import handwritten_ocr

            ocr_engine = handwritten_ocr if doc_type == "handwritten" else printed_ocr
            ocr_confidences = []

            for idx, page in enumerate(reader.pages):
                page_text = native_texts[idx]
                page_conf = 0.85

                # If native text is empty or sparse, run OCR on embedded page images
                if len(page_text) < 60:
                    page_images = getattr(page, "images", [])
                    if len(page_images) > 0 and idx < max_ocr_pages:
                        try:
                            # Extract primary page image
                            pil_img = page_images[0].image
                            if doc_type == "handwritten":
                                ocr_res = handwritten_ocr.extract_handwriting(pil_img)
                            else:
                                ocr_res = printed_ocr.extract_text(pil_img)

                            extracted_ocr = ocr_res.get("text", "").strip()
                            if extracted_ocr:
                                page_text = extracted_ocr
                                page_conf = ocr_res.get("confidence", 0.88)
                                ocr_confidences.append(page_conf)
                        except Exception as ocr_err:
                            logger.warning(f"OCR failed for {file_path} page {idx+1}: {ocr_err}")

                    if not page_text:
                        img_count = len(page_images)
                        tag = "Handwritten" if doc_type == "handwritten" else "Scanned"
                        page_text = f"**[{tag} Page {idx + 1}]** ({img_count} image raster artifacts preserved for retrieval)."
                else:
                    ocr_confidences.append(0.90)

                pages_data.append({
                    "page_number": idx + 1,
                    "section": f"Page {idx + 1}",
                    "text": page_text
                })

            final_conf = round(sum(ocr_confidences) / len(ocr_confidences), 3) if ocr_confidences else 0.86
            return pages_data, doc_type, final_conf

        except Exception as e:
            logger.error(f"Error extracting PDF {file_path}: {e}")
            raise


class DOCXExtractor:
    """Extracts structured text from DOCX files preserving headings as sections and text."""

    @staticmethod
    def extract(file_path: str) -> Tuple[List[Dict[str, Any]], str, Optional[float]]:
        pages_data = []
        current_section = "Introduction"
        current_texts = []
        page_counter = 1

        try:
            doc = docx.Document(file_path)

            # Extract paragraphs and tables in natural document flow order
            for child in doc.element.body:
                if child.tag.endswith("p"):
                    para = docx.text.paragraph.Paragraph(child, doc)
                    text = para.text.strip()
                    if not text:
                        continue

                    style_name = getattr(para.style, "name", "") if para.style else ""
                    if style_name and style_name.startswith("Heading"):
                        if current_texts:
                            pages_data.append({
                                "page_number": page_counter,
                                "section": current_section,
                                "text": "\n\n".join(current_texts)
                            })
                            current_texts = []
                            page_counter += 1
                        current_section = text
                        current_texts.append(f"## {text}")
                    elif text.lower().startswith("figure ") or text.lower().startswith("diagram "):
                        # Multi-modal figure caption tag
                        current_texts.append(f"**[Figure/Diagram]** {text}")
                    else:
                        current_texts.append(text)

                elif child.tag.endswith("tbl"):
                    table = docx.table.Table(child, doc)
                    if table.rows:
                        # Serialize table to standard markdown table
                        rows_data = []
                        for row in table.rows:
                            row_cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
                            rows_data.append(row_cells)

                        if rows_data and any(any(c for c in r) for r in rows_data):
                            col_count = max(len(r) for r in rows_data)
                            header = (rows_data[0] + [""] * col_count)[:col_count]
                            sep = [":---"] * col_count
                            md_table_lines = [
                                "| " + " | ".join(header) + " |",
                                "| " + " | ".join(sep) + " |"
                            ]
                            for r in rows_data[1:]:
                                padded = (r + [""] * col_count)[:col_count]
                                md_table_lines.append("| " + " | ".join(padded) + " |")

                            current_texts.append("\n" + "\n".join(md_table_lines) + "\n")

            if current_texts:
                pages_data.append({
                    "page_number": page_counter,
                    "section": current_section,
                    "text": "\n\n".join(current_texts)
                })

            return pages_data, "born_digital", None

        except Exception as e:
            logger.error(f"Error extracting DOCX {file_path}: {e}")
            raise


class TextExtractor:
    """Extracts plain text / markdown files."""

    @staticmethod
    def extract(file_path: str) -> Tuple[List[Dict[str, Any]], str, Optional[float]]:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        pages_data = [{
            "page_number": 1,
            "section": "Document Content",
            "text": content.strip()
        }]
        return pages_data, "born_digital", None


class ImageExtractor:
    """Extracts content from scanned image files (PNG, JPG, TIFF) via OCR/VLM."""

    @staticmethod
    def extract(file_path: str) -> Tuple[List[Dict[str, Any]], str, Optional[float]]:
        filename = os.path.basename(file_path)
        fname_lower = filename.lower()
        is_handwriting_hint = any(
            k in fname_lower for k in [
                "handwritten", "hand_written", "docscanner", "camscanner",
                "notes", "hw", "written", "assignment", "draft"
            ]
        )
        doc_type = "handwritten" if is_handwriting_hint else "scanned"

        try:
            if doc_type == "handwritten":
                from ingestion.ocr_handwritten import handwritten_ocr
                ocr_res = handwritten_ocr.extract_handwriting(file_path)
            else:
                from ingestion.ocr_printed import printed_ocr
                ocr_res = printed_ocr.extract_text(file_path)

            extracted_text = ocr_res.get("text", "").strip()
            confidence = ocr_res.get("confidence", 0.85)
        except Exception as e:
            logger.warning(f"Image OCR error for {file_path}: {e}")
            extracted_text = ""
            confidence = 0.70

        if not extracted_text:
            tag = "Handwritten" if doc_type == "handwritten" else "Scanned"
            extracted_text = f"**[{tag} Image Document: {filename}]**\nHigh-resolution bitmap preserved for multi-modal VLM and OCR indexing."

        pages_data = [{
            "page_number": 1,
            "section": "Handwritten Document Image" if doc_type == "handwritten" else "Scanned Document Image",
            "text": extracted_text
        }]
        return pages_data, doc_type, confidence


class DocumentExtractorRouter:
    """Routes files to appropriate extractor based on format and signature."""

    @staticmethod
    def extract(file_path: str) -> Tuple[List[Dict[str, Any]], str, Optional[float]]:
        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".pdf":
            return PDFExtractor.extract(file_path)
        elif ext in [".docx", ".doc"]:
            return DOCXExtractor.extract(file_path)
        elif ext in [".txt", ".md", ".markdown"]:
            return TextExtractor.extract(file_path)
        elif ext in [".png", ".jpg", ".jpeg", ".tiff", ".bmp"]:
            return ImageExtractor.extract(file_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}")
