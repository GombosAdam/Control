"""
Migration 005: Float → Numeric phase 1 — add _new columns + copy data.
Zero-downtime: existing columns untouched, code still reads old columns.
Idempotent — safe to re-run.
"""
import psycopg2
from common.config import settings


# (table, column, numeric_type)
COLUMNS = [
    ("budget_lines", "planned_amount", "NUMERIC(18,2)"),
    ("accounting_entries", "amount", "NUMERIC(18,2)"),
    ("purchase_orders", "amount", "NUMERIC(18,2)"),
    ("purchase_order_lines", "quantity", "NUMERIC(18,2)"),
    ("purchase_order_lines", "unit_price", "NUMERIC(18,2)"),
    ("purchase_order_lines", "net_amount", "NUMERIC(18,2)"),
    ("invoices", "net_amount", "NUMERIC(18,2)"),
    ("invoices", "vat_amount", "NUMERIC(18,2)"),
    ("invoices", "gross_amount", "NUMERIC(18,2)"),
    ("invoices", "vat_rate", "NUMERIC(5,2)"),
    ("invoices", "ocr_confidence", "NUMERIC(5,4)"),
    ("invoices", "ai_confidence", "NUMERIC(5,4)"),
    ("invoices", "similarity_score", "NUMERIC(5,4)"),
    ("invoice_lines", "quantity", "NUMERIC(18,2)"),
    ("invoice_lines", "unit_price", "NUMERIC(18,2)"),
    ("invoice_lines", "net_amount", "NUMERIC(18,2)"),
    ("invoice_lines", "vat_rate", "NUMERIC(5,2)"),
    ("invoice_lines", "vat_amount", "NUMERIC(18,2)"),
    ("invoice_lines", "gross_amount", "NUMERIC(18,2)"),
    ("partners", "total_amount", "NUMERIC(18,2)"),
]


def run():
    conn = psycopg2.connect(settings.DATABASE_URL_SYNC)
    conn.autocommit = False
    cur = conn.cursor()

    try:
        for table, column, num_type in COLUMNS:
            new_col = f"{column}_new"

            # Add _new column
            cur.execute(f"""
                DO $$ BEGIN
                    ALTER TABLE {table} ADD COLUMN {new_col} {num_type};
                EXCEPTION WHEN duplicate_column THEN NULL;
                END $$;
            """)

            # Copy data
            cur.execute(f"""
                UPDATE {table}
                SET {new_col} = {column}::{num_type}
                WHERE {new_col} IS NULL AND {column} IS NOT NULL
            """)
            print(f"  {table}.{column} → {new_col}: {cur.rowcount} rows copied")

        conn.commit()
        print("Migration 005 complete: _new Numeric columns created and data copied.")

    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    run()
