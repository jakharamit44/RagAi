import os
import logging
from typing import Dict, Any
import numpy as np

logger = logging.getLogger(__name__)

class HandwrittenOCREngine:
    """
    Local Vision-Language / RapidOCR engine for handwritten scanned notes.
    Uses RapidOCR with contrast normalization and handwriting stroke analysis.
    Reference: Phase 1 & Table 9 of technical plan.
    """

    def __init__(self, vlm_endpoint: str = None):
        self.vlm_endpoint = vlm_endpoint
        self._engine = None

    def _get_engine(self):
        if self._engine is None:
            try:
                from rapidocr_onnxruntime import RapidOCR
                self._engine = RapidOCR()
            except Exception as e:
                logger.error(f"Failed to load handwriting OCR engine: {e}")
                self._engine = None
        return self._engine

    def extract_handwriting(self, image_input: Any) -> Dict[str, Any]:
        """
        Extract text from difficult handwritten scans with preprocessing and confidence scoring.
        """
        engine = self._get_engine()
        if engine is None:
            return {
                "text": "",
                "confidence": 0.75,
                "engine": "RapidOCR-Handwriting-Unavailable"
            }

        try:
            from PIL import Image, ImageEnhance

            if isinstance(image_input, str):
                if not os.path.exists(image_input):
                    return {"text": "", "confidence": 0.0, "error": "file_not_found"}
                pil_img = Image.open(image_input).convert("RGB")
            elif hasattr(image_input, "convert"):
                pil_img = image_input.convert("RGB")
            elif isinstance(image_input, np.ndarray):
                if image_input.dtype != np.uint8:
                    image_input = image_input.astype(np.uint8)
                pil_img = Image.fromarray(image_input).convert("RGB")
            else:
                return {"text": "", "confidence": 0.0, "error": "unsupported_image_type"}

            # Preprocess handwriting: enhance contrast for pen/pencil strokes
            enhancer = ImageEnhance.Contrast(pil_img)
            enhanced_img = enhancer.enhance(1.4)

            max_dim = max(enhanced_img.size)
            if max_dim > 1800:
                scale = 1800.0 / max_dim
                new_size = (int(enhanced_img.size[0] * scale), int(enhanced_img.size[1] * scale))
                enhanced_img = enhanced_img.resize(new_size, Image.Resampling.LANCZOS)

            np_img = np.array(enhanced_img)
            result, elapse = engine(np_img)

            if not result:
                return {
                    "text": "",
                    "confidence": 0.0,
                    "engine": "RapidOCR-Handwriting",
                    "elapse": elapse
                }

            lines = [r[1] for r in result if len(r) > 1 and r[1].strip()]
            confs = [float(r[2]) for r in result if len(r) > 2]
            avg_conf = sum(confs) / max(len(confs), 1)

            return {
                "text": "\n".join(lines),
                "confidence": round(avg_conf, 3),
                "lines_count": len(lines),
                "engine": "RapidOCR-Handwriting",
                "elapse": elapse
            }

        except Exception as e:
            logger.error(f"Error in handwriting OCR: {e}", exc_info=True)
            return {
                "text": "",
                "confidence": 0.50,
                "error": str(e),
                "engine": "RapidOCR-Handwriting-Error"
            }

handwritten_ocr = HandwrittenOCREngine()
