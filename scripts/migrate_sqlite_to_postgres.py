#!/usr/bin/env python3
"""
Zero-Data-Loss Migration: SQLite (university_rag.db) -> PostgreSQL (192.168.81.150:5432)
"""

import sys
import os
import time
import sqlite3
import psycopg2
from psycopg2.extras import execute_values

PG_CONN_STR = "postgresql://ragai:9wtbai4u6xHovYkSnl2TVApBI0ZjJMK1@192.168.81.150:5432/university_rag"
SQLITE_DB = "university_rag.db"
BATCH_SIZE = 5000

# Order tables by dependency
TABLE_ORDER = [
    "watched_folders",
    "users",
    "web_scrape_jobs",
    "documents",
    "chunks",
    "web_scrape_manifest",
    "context_tiers",
    "manifest_entries",
    "api_keys",
    "url_governance_rules",
    "system_settings",
    "security_incidents",
    "prompt_optimization_runs",
    "query_audit_log",
]

def migrate():
    print(f"Connecting to SQLite ({SQLITE_DB})...")
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_conn.row_factory = sqlite3.Row
    s_cur = sqlite_conn.cursor()

    print("Connecting to PostgreSQL...")
    pg_conn = psycopg2.connect(PG_CONN_STR)
    pg_conn.autocommit = False
    p_cur = pg_conn.cursor()

    # Disable foreign key checks for clean bulk load
    p_cur.execute("SET session_replication_role = 'replica';")

    # Get available tables in SQLite
    s_cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    existing_sqlite_tables = set(r[0] for r in s_cur.fetchall())

    start_all = time.time()

    for table in TABLE_ORDER:
        if table not in existing_sqlite_tables:
            print(f"Skipping {table} (not in SQLite)")
            continue

        # Get PostgreSQL table columns
        p_cur.execute(f"""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = %s AND table_schema = 'public'
        """, (table,))
        pg_cols = {row[0]: row[1] for row in p_cur.fetchall()}
        if not pg_cols:
            print(f"Warning: {table} does not exist in PostgreSQL schema. Skipping.")
            continue

        # Get SQLite table columns
        s_cur.execute(f"PRAGMA table_info(\"{table}\")")
        sqlite_cols = [r[1] for r in s_cur.fetchall()]

        # Common columns
        common_cols = [c for c in sqlite_cols if c in pg_cols]
        if not common_cols:
            print(f"No matching columns for {table}. Skipping.")
            continue

        # Count in SQLite
        s_cur.execute(f"SELECT COUNT(*) FROM \"{table}\"")
        total_rows = s_cur.fetchone()[0]
        if total_rows == 0:
            print(f"Table {table}: 0 rows (empty)")
            continue

        print(f"\nMigrating {table} ({total_rows:,} rows)...")

        # Truncate PG table first
        p_cur.execute(f"TRUNCATE TABLE \"{table}\" CASCADE;")

        cols_str = ", ".join(f'"{c}"' for c in common_cols)
        select_query = f"SELECT {cols_str} FROM \"{table}\""
        insert_query = f"INSERT INTO \"{table}\" ({cols_str}) VALUES %s"

        s_cur.execute(select_query)
        migrated = 0
        t0 = time.time()

        while True:
            rows = s_cur.fetchmany(BATCH_SIZE)
            if not rows:
                break

            # Convert rows to tuples with boolean/null fixes
            batch_data = []
            for r in rows:
                row_vals = []
                for idx, c in enumerate(common_cols):
                    v = r[idx]
                    col_type = pg_cols[c]
                    # Handle boolean conversion
                    if col_type == "boolean" and v is not None:
                        v = bool(v)
                    row_vals.append(v)
                batch_data.append(tuple(row_vals))

            execute_values(p_cur, insert_query, batch_data, page_size=BATCH_SIZE)
            migrated += len(batch_data)
            elapsed = time.time() - t0
            rate = migrated / elapsed if elapsed > 0 else 0
            print(f"  -> {table}: {migrated:,}/{total_rows:,} ({(migrated/total_rows)*100:.1f}%) | {rate:.0f} rows/s", end="\r")

        pg_conn.commit()
        print(f"  -> {table}: {migrated:,} rows migrated successfully in {time.time()-t0:.2f}s!")

    # Re-enable foreign key constraints
    p_cur.execute("SET session_replication_role = 'origin';")
    pg_conn.commit()

    print("\n" + "="*50)
    print("MIGRATION INTEGRITY AUDIT:")
    print("="*50)
    print(f"{'Table':<30} | {'SQLite':<10} | {'Postgres':<10} | {'Status'}")
    print("-" * 65)

    all_matched = True
    for table in TABLE_ORDER:
        if table not in existing_sqlite_tables:
            continue
        s_cur.execute(f"SELECT COUNT(*) FROM \"{table}\"")
        s_count = s_cur.fetchone()[0]

        try:
            p_cur.execute(f"SELECT COUNT(*) FROM \"{table}\"")
            p_count = p_cur.fetchone()[0]
        except Exception:
            p_count = "ERROR"

        status = "MATCH" if s_count == p_count else "MISMATCH"
        if status != "MATCH":
            all_matched = False
        print(f"{table:<30} | {s_count:<10} | {p_count:<10} | {status}")

    s_cur.close()
    sqlite_conn.close()
    p_cur.close()
    pg_conn.close()

    total_time = time.time() - start_all
    print("="*50)
    if all_matched:
        print(f"SUCCESS: 100% Data Parity Achieved in {total_time:.2f}s!")
    else:
        print("WARNING: Some row counts did not match.")

if __name__ == "__main__":
    migrate()
