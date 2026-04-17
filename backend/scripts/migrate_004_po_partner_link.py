"""
Migration 004: PurchaseOrder → Partner FK + backfill from supplier_tax_id.
Idempotent — safe to re-run.
"""
import psycopg2
from common.config import settings


def run():
    conn = psycopg2.connect(settings.DATABASE_URL_SYNC)
    conn.autocommit = False
    cur = conn.cursor()

    try:
        # 1. Add partner_id column if not exists
        cur.execute("""
            DO $$ BEGIN
                ALTER TABLE purchase_orders ADD COLUMN partner_id VARCHAR(36);
            EXCEPTION WHEN duplicate_column THEN NULL;
            END $$;
        """)

        # 2. Add FK constraint (NOT VALID)
        cur.execute("""
            DO $$ BEGIN
                ALTER TABLE purchase_orders
                    ADD CONSTRAINT fk_purchase_orders_partner
                    FOREIGN KEY (partner_id) REFERENCES partners(id) NOT VALID;
            EXCEPTION WHEN duplicate_object THEN NULL;
            END $$;
        """)

        conn.commit()

        # 3. Backfill partner_id from supplier_tax_id match
        cur.execute("""
            UPDATE purchase_orders po
            SET partner_id = p.id
            FROM partners p
            WHERE po.supplier_tax_id = p.tax_number
              AND po.supplier_tax_id IS NOT NULL
              AND po.partner_id IS NULL
        """)
        backfilled = cur.rowcount
        print(f"  Backfilled {backfilled} purchase orders with partner_id")

        conn.commit()

        # 4. Validate FK
        try:
            cur.execute("ALTER TABLE purchase_orders VALIDATE CONSTRAINT fk_purchase_orders_partner;")
            conn.commit()
            print("  Validated fk_purchase_orders_partner")
        except Exception as e:
            conn.rollback()
            print(f"  Warning: Could not validate FK: {e}")

        # 5. Add index
        cur.execute("""
            CREATE INDEX IF NOT EXISTS ix_purchase_orders_partner_id
            ON purchase_orders(partner_id);
        """)
        conn.commit()

        print("Migration 004 complete: PO → Partner link established and backfilled.")

    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    run()
