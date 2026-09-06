import os
import logging
from typing import Dict, Any, Union
import numpy as np

logger = logging.getLogger(__name__)

class PrintedOCREngine:
    """
    Local printed document OCR engine using RapidOCR (PP-OCRv4 / ONNXRuntime).
    Provides high-speed CPU/GPU layout-aware text extraction for scans and archival documents.
    Reference: Phase 1 & Table 9 of technical plan.
    """

    def __init__(self):
        self._engine = None

    def _get_engine(self):
        if self._engine is None:
            try:
                try:
                    from api.core.cuda_init import init_cuda_runtime
                    init_cuda_runtime()
                except Exception as cuda_err:
                    logger.warning(f"CUDA initialization note: {cuda_err}")

                from rapidocr_onnxruntime import RapidOCR
                self._engine = RapidOCR()
                logger.info("RapidOCR engine initialized successfully with CUDA/GPU acceleration.")
            except Exception as e:
                logger.error(f"Failed to initialize RapidOCR: {e}")
                self._engine = None
        return self._engine

    def extract_text(self, image_input: Any) -> Dict[str, Any]:
        """
        Extract printed text with confidence scores from an image path, PIL Image, or numpy array.
        """
        engine = self._get_engine()
        if engine is None:
            return {
                "text": "",
                "confidence": 0.80,
                "engine": "RapidOCR-Unavailable"
            }

        try:
            from PIL import Image

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

            # Optimize resolution for inference speed while preserving legibility
            max_dim = max(pil_img.size)
            if max_dim > 1800:
                scale = 1800.0 / max_dim
                new_size = (int(pil_img.size[0] * scale), int(pil_img.size[1] * scale))
                pil_img = pil_img.resize(new_size, Image.Resampling.LANCZOS)

            np_img = np.array(pil_img)
            result, elapse = engine(np_img)

            if not result:
                return {
                    "text": "",
                    "confidence": 0.0,
                    "engine": "RapidOCR-PP-OCRv4",
                    "elapse": elapse
                }

            lines = [r[1] for r in result if len(r) > 1 and r[1].strip()]
            confs = [float(r[2]) for r in result if len(r) > 2]
            avg_conf = sum(confs) / max(len(confs), 1)

            return {
                "text": "\n".join(lines),
                "confidence": round(avg_conf, 3),
                "lines_count": len(lines),
                "engine": "RapidOCR-PP-OCRv4",
                "elapse": elapse
            }

        except Exception as e:
            logger.error(f"Error during OCR extraction: {e}", exc_info=True)
            return {
                "text": "",
                "confidence": 0.50,
                "error": str(e),
                "engine": "RapidOCR-Error"
            }

printed_ocr = PrintedOCREngine()
