import os
import sys
import pypdf
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingestion.ocr_printed import printed_ocr

pdf_dir = r"D:\PDFs"
target_files = [
    '4_06-10-2026_19-06-13_DocScanner 10-Jun-2026 5-11 pm.pdf',
    '4_06-10-2026_20-49-07_Extension in last date for submission of online application form for admission to 2-Year PG Programs, 3-Year LL.B, (Hons), B.P.Ed. under NEP-2020 for the session 2026-27.pdf',
    '4_06-12-2026_17-14-13_PG Notification IV.pdf',
    '4_09-04-2023_12-37-29_Notification regardin partial modification in schedule of exams.pdf',
    '4_10-01-2025_23-27-17_Schedule of Exams for session 2025-26.pdf',
    '4_12-15-2021_16-53-58_Additional Schedule.pdf',
    '4_01-15-2025_16-55-31_phd course work schedule.pdf',
    '4_01-15-2025_16-57-10_itep schedule.pdf',
    '4_02-17-2026_18-03-08_MainRevised Schedule.pdf',
    '4_06-10-2026_12-44-15_NNotification UG PG.pdf',
    'notification_Enhancement_rate_Youth_Welfare_2010_2011.pdf',
    'notification_exam.pdf',
    '1st meeting of Court held on 29th march, 1978.pdf',
    '2nd meeting of Court held on 25th November, 1978.pdf'
]

for tf in target_files:
    fp = os.path.join(pdf_dir, tf)
    if not os.path.exists(fp):
        continue
    reader = pypdf.PdfReader(fp)
    p = reader.pages[0]
    imgs = getattr(p, "images", [])
    if imgs:
        arr = np.array(imgs[0].image.convert("RGB"))
        ocr_res = printed_ocr.extract_text(arr)
        lines = [line.strip() for line in ocr_res.get("text", "").splitlines() if line.strip()]
        sample = " | ".join(lines[:4])
        print(f"{tf[:38]:<40} | lines:{len(lines):>2} | conf:{ocr_res.get('confidence')} | sample: {sample[:80]}")
