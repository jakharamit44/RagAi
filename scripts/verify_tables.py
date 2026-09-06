import sqlite3

def check():
    conn = sqlite3.connect("university_rag.db")
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    print("Database tables verified:")
    for t in sorted(tables):
        count = conn.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
        print(f"  - {t} (rows: {count})")
    conn.close()

if __name__ == "__main__":
    check()
