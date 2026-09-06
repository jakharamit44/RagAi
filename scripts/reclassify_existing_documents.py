import os
import sys
sys.path.insert(0, os.path.abspath("."))
import sqlite3
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('reclassify')

from ingestion.format_detector import FormatDetector
from ingestion.extractors import PDFExtractor

DB_PATH = 'university_rag.db'

def reclassify_and_reextract():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('SELECT id, title, source_path, doc_type, ocr_confidence FROM documents')
    docs = cursor.fetchall()
    logger.info(f'Loaded {len(docs)} documents from database.')

    breakdown = {'born_digital': 0, 'scanned': 0, 'handwritten': 0}
    reclassified_records = []

    for doc_id, title, source_path, old_type, old_conf in docs:
        if not source_path or not os.path.exists(source_path):
            continue

        try:
            new_type, engine_type = FormatDetector.detect_category(source_path)
            breakdown[new_type] = breakdown.get(new_type, 0) + 1

            new_conf = None
            if new_type in ['scanned', 'handwritten']:
                if old_type == new_type and old_conf is not None:
                    new_conf = old_conf
                else:
                    logger.info(f'Processing OCR for [{new_type}]: {title[:35]}...')
                    pages_data, detected_type, computed_conf = PDFExtractor.extract(source_path, max_ocr_pages=10)
                    new_conf = computed_conf or old_conf or 0.88

                    cursor.execute('SELECT id, page_number FROM chunks WHERE document_id = ? ORDER BY page_number ASC', (doc_id,))
                    chunk_rows = cursor.fetchall()
                    page_text_map = {p['page_number']: p['text'] for p in pages_data}

                    for chunk_id, page_num in chunk_rows:
                        if page_num in page_text_map and page_text_map[page_num].strip():
                            updated_text = page_text_map[page_num]
                            cursor.execute('UPDATE chunks SET text = ? WHERE id = ?', (updated_text, chunk_id))

            cursor.execute(
                'UPDATE documents SET doc_type = ?, ocr_confidence = ? WHERE id = ?',
                (new_type, new_conf, doc_id)
            )

            reclassified_records.append({
                'title': title,
                'old_type': old_type,
                'new_type': new_type,
                'confidence': new_conf
            })
            logger.info(f'  -> {title[:35]}: {old_type} => {new_type} (conf: {new_conf})')

        except Exception as e:
            logger.error(f'Error processing {title}: {e}', exc_info=True)

    conn.commit()
    conn.close()

    print('\n' + '='*80)
    print('RECLASSIFICATION SUMMARY')
    print('='*80)
    for r in reclassified_records:
        conf_val = r.get('confidence')
        conf_str = f"({conf_val*100:.1f}%)" if conf_val else "      "
        print(f"{r['title'][:42]:<44} | {r['old_type']:12} => {r['new_type']:12} {conf_str}")

    print('-'*80)
    bd = breakdown.get('born_digital', 0)
    sc = breakdown.get('scanned', 0)
    hw = breakdown.get('handwritten', 0)
    print(f'Total: {len(reclassified_records)} files | Born-Digital: {bd} | Scanned: {sc} | Handwritten: {hw}')
    print('='*80)

if __name__ == '__main__':
    reclassify_and_reextract()