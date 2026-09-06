import os
import sys
import sqlite3

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def check():
    conn = sqlite3.connect("university_rag.db")
    rows = conn.execute("SELECT id, section, text FROM chunks WHERE lower(text) LIKE '%principles%'").fetchall()
    print(f"Chunks containing 'principles': {len(rows)}")
    for r in rows:
        print(f"  Sec: {r[1]} | Len: {len(r[2])} | Text: {r[2][:100]}")
    conn.close()

if __name__ == "__main__":
    check()
