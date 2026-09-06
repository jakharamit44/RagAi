import logging
from .celery_app import celery_app
from ingestion.ocr_printed import printed_ocr
from ingestion.ocr_handwritten import handwritten_ocr

logger = logging.getLogger(__name__)

@celery_app.task(
    name="tasks.run_ocr", 
    bind=True, 
    acks_late=True, 
    max_retries=3, 
    autoretry_for=(Exception,), 
    retry_backoff=True
)
def run_ocr_task(self, file_path: str, doc_type: str = "printed"):
    """
    Asynchronously run OCR on scanned or handwritten images/PDFs.
    Reference: Phase 8 of technical plan.
    """
    logger.info(f"Starting OCR task for {file_path} (type: {doc_type})")
    if doc_type == "handwritten":
        result = handwritten_ocr.extract_handwriting(file_path)
    else:
        result = printed_ocr.extract_text(file_path)
    return result
