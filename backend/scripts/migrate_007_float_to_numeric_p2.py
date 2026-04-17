"""
Migration 007: Float → Numeric phase 2 — column swap.
Run AFTER code deploy (models already point to Numeric types).
Idempotent — safe to re-run.
"""
import psycopg2
from common.config import settings


# (table, column, numeric_type, nullable, default)
COLUMNS = [
    ("budget_lines", "planned_amount", "NUMERIC(18,2)", False, None),
    ("accounting_entries", "amount", "NUMERIC(18,2)", False, None),
    ("purchase_orders", "amount", "NUMERIC(18,2)", False, None),
    ("purchase_order_lines", "quantity", "NUMERIC(18,2)", False, None),
    ("purchase_order_lines", "unit_price", "NUMERIC(18,2)", False, None),
    ("purchase_order_lines", "net_amount", "NUMERIC(18,2)", False, None),
    ("invoices", "net_amount", "NUMERIC(18,2)", True, None),
    ("invoices", "vat_amount", "NUMERIC(18,2)", True, None),
    ("invoices", "gross_amount", "NUMERIC(18,2)", True, None),
    ("invoices", "vat_rate", "NUMERIC(5,2)", True, None),
    ("invoices", "ocr_confidence", "NUMERIC(5,4)", True, None),
    ("invoices", "ai_confidence", "NUMERIC(5,4)", True, None),
    ("invoices", "similarity_score", "NUMERIC(5,4)", True, None),
    ("invoice_lines", "quantity", "NUMERIC(18,2)", True, None),
    ("invoice_lines", "unit_price", "NUMERIC(18,2)", True, None),
    ("invoice_lines", "net_amount", "NUMERIC(18,2)", True, None),
    ("invoice_lines", "vat_rate", "NUMERIC(5,2)", True, None),
    ("invoice_lines", "vat_amount", "NUMERIC(18,2)", True, None),
    ("invoice_lines", "gross_amount", "NUMERIC(18,2)", True, None),
    ("partners", "total_amount", "NUMERIC(18,2)", False, "0"),
]


def run():
    conn = psycopg2.connect(settings.DATABASE_URL_SYNC)
    conn.autocommit = False
    cur = conn.cursor()

    try:
        for table, column, num_type, nullable, default in COLUMNS:
            new_col = f"{column}_new"
            old_col = f"{column}_old"

            # Check if _new column exists (migration 005 ran)
            cur.execute("""
                SELECT 1 FROM information_schema.columns
                WHERE table_name = %s AND column_name = %s
            """, (table, new_col))
            if not cur.fetchone():
                print(f"  Skipping {table}.{column} — no _new column found (run migrate_005 first)")
                continue

            # Check if swap already done (old column gone or _new gone)
            cur.execute("""
                SELECT data_type FROM information_schema.columns
                WHERE table_name = %s AND column_name = %s
            """, (table, column))
            col_info = cur.fetchone()
            if col_info and col_info[0] == 'numeric':
                # Already numeric, clean up _new if still there
                cur.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS {new_col};")
                print(f"  {table}.{column} already numeric, cleaned up _new")
                continue

            # Final sync: copy any rows written since phase 1
            cur.execute(f"""
                UPDATE {table}
                SET {new_col} = {column}::{num_type}
                WHERE {column} IS NOT NULL AND (
                    {new_col} IS NULL OR {new_col} != {column}::{num_type}
                )
            """)

            # Swap: rename old → _old, _new → column
            cur.execute(f"ALTER TABLE {table} RENAME COLUMN {column} TO {old_col};")
            cur.execute(f"ALTER TABLE {table} RENAME COLUMN {new_col} TO {column};")

            # Set NOT NULL if needed
            if not nullable:
                if default is not None:
                    cur.execute(f"UPDATE {table} SET {column} = {default} WHERE {column} IS NULL;")
                cur.execute(f"ALTER TABLE {table} ALTER COLUMN {column} SET NOT NULL;")

            # Drop old column
            cur.execute(f"ALTER TABLE {table} DROP COLUMN {old_col};")

            print(f"  Swapped {table}.{column}: Float → Numeric")

        conn.commit()
        print("Migration 007 complete: All Float columns swapped to Numeric.")

    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    run()
