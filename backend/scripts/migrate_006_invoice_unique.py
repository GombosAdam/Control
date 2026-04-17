"""
Migration 006: Partial unique index on invoices (partner_id, invoice_number).
Idempotent — safe to re-run.
"""
import psycopg2
from common.config import settings


def run():
    conn = psycopg2.connect(settings.DATABASE_URL_SYNC)
    conn.autocommit = True  # CREATE INDEX CONCURRENTLY needs autocommit
    cur = conn.cursor()

    try:
        cur.execute("""
            CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS uq_invoice_partner_number
            ON invoices (partner_id, invoice_number)
            WHERE invoice_number IS NOT NULL
              AND is_duplicate = false
              AND partner_id IS NOT NULL;
        """)
        print("Migration 006 complete: Partial unique index on invoices created.")

    except Exception as e:
        print(f"Error: {e}")
        # If index creation failed, it may be INVALID — drop and retry
        cur.execute("DROP INDEX IF EXISTS uq_invoice_partner_number;")
        raise e
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    run()
