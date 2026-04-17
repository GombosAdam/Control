"""
Migration 001: AccountMaster table + seed data + FK constraints.
Idempotent — safe to re-run.
"""
import psycopg2
from common.config import settings


SEED_ACCOUNTS = [
    # (code, name, name_en, account_type, pnl_category, parent_code, sort_order, is_header, normal_side)
    ("4", "Bevételek", "Revenue", "revenue", None, None, 100, True, "credit"),
    ("4100", "Termék értékesítés", "Product Revenue", "revenue", "revenue", "4", 110, False, "credit"),
    ("4200", "Szolgáltatás bevétel", "Service Revenue", "revenue", "revenue", "4", 120, False, "credit"),
    ("4300", "Egyéb bevétel", "Other Revenue", "revenue", "revenue", "4", 130, False, "credit"),
    ("5", "Közvetlen költségek", "Direct Costs", "expense", None, None, 200, True, "debit"),
    ("5100", "Anyagköltség", "Material Cost", "expense", "cogs", "5", 210, False, "debit"),
    ("5110", "Alapanyag költség", "Raw Material Cost", "expense", "cogs", "5", 211, False, "debit"),
    ("5120", "Alvállalkozói díj", "Subcontractor Fee", "expense", "cogs", "5", 212, False, "debit"),
    ("5130", "Közvetlen bérköltség", "Direct Labor Cost", "expense", "cogs", "5", 213, False, "debit"),
    ("6", "Működési költségek", "Operating Expenses", "expense", None, None, 300, True, "debit"),
    ("6100", "Irodai költség", "Office Expense", "expense", "opex", "6", 310, False, "debit"),
    ("6200", "Marketing költség", "Marketing Expense", "expense", "opex", "6", 320, False, "debit"),
    ("6300", "IT költség", "IT Expense", "expense", "opex", "6", 330, False, "debit"),
    ("6400", "Utazási költség", "Travel Expense", "expense", "opex", "6", 340, False, "debit"),
    ("6500", "Képzési költség", "Training Expense", "expense", "opex", "6", 350, False, "debit"),
    ("6600", "Egyéb működési", "Other Operating", "expense", "opex", "6", 360, False, "debit"),
    ("7", "Értékcsökkenés", "Depreciation", "expense", None, None, 400, True, "debit"),
    ("7100", "Tárgyi eszköz ÉCS", "Tangible Asset Depreciation", "expense", "depreciation", "7", 410, False, "debit"),
    ("7200", "Immat. javak ÉCS", "Intangible Asset Amortization", "expense", "depreciation", "7", 420, False, "debit"),
    ("8", "Pénzügyi ráfordítás", "Financial Expenses", "expense", None, None, 500, True, "debit"),
    ("8100", "Kamatráfordítás", "Interest Expense", "expense", "interest", "8", 510, False, "debit"),
    ("8200", "Árfolyamveszteség", "Foreign Exchange Loss", "expense", "interest", "8", 520, False, "debit"),
    ("9", "Adók", "Taxes", "tax", None, None, 600, True, "debit"),
    ("9100", "Társasági adó", "Corporate Tax", "tax", "tax", "9", 610, False, "debit"),
    ("9200", "Iparűzési adó", "Local Business Tax", "tax", "tax", "9", 620, False, "debit"),
    ("454", "Szállítók", "Accounts Payable", "liability", None, None, 50, False, "credit"),
    ("466", "Levonható ÁFA", "Input VAT", "asset", None, None, 55, False, "debit"),
]


def run():
    conn = psycopg2.connect(settings.DATABASE_URL_SYNC)
    conn.autocommit = False
    cur = conn.cursor()

    try:
        # 1. Create account_type enum if not exists
        cur.execute("""
            DO $$ BEGIN
                CREATE TYPE accounttype AS ENUM ('asset', 'liability', 'revenue', 'expense', 'tax');
            EXCEPTION WHEN duplicate_object THEN NULL;
            END $$;
        """)

        # 2. Create account_master table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS account_master (
                code        VARCHAR(20) PRIMARY KEY,
                name        VARCHAR(255) NOT NULL,
                name_en     VARCHAR(255),
                account_type accounttype NOT NULL,
                pnl_category VARCHAR(20),
                parent_code VARCHAR(20) REFERENCES account_master(code),
                sort_order  INTEGER NOT NULL DEFAULT 0,
                is_active   BOOLEAN NOT NULL DEFAULT TRUE,
                is_header   BOOLEAN NOT NULL DEFAULT FALSE,
                normal_side VARCHAR(6),
                created_at  TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at  TIMESTAMP NOT NULL DEFAULT NOW()
            );
        """)

        # 3. Seed data
        for row in SEED_ACCOUNTS:
            cur.execute("""
                INSERT INTO account_master (code, name, name_en, account_type, pnl_category, parent_code, sort_order, is_header, normal_side)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (code) DO NOTHING;
            """, row)

        # 4. Add FK constraints (NOT VALID for zero-downtime)
        fk_definitions = [
            ("budget_lines", "account_code", "fk_budget_lines_account_master"),
            ("accounting_entries", "account_code", "fk_accounting_entries_account_master"),
            ("purchase_orders", "accounting_code", "fk_purchase_orders_account_master"),
            ("invoices", "accounting_code", "fk_invoices_accounting_code_account_master"),
            ("invoices", "suggested_accounting_code", "fk_invoices_suggested_code_account_master"),
            ("department_budget_master", "account_code", "fk_dept_budget_master_account_master"),
            ("accounting_templates", "debit_account", "fk_acct_templates_debit_account_master"),
            ("accounting_templates", "credit_account", "fk_acct_templates_credit_account_master"),
        ]

        for table, column, constraint_name in fk_definitions:
            cur.execute(f"""
                DO $$ BEGIN
                    ALTER TABLE {table}
                        ADD CONSTRAINT {constraint_name}
                        FOREIGN KEY ({column}) REFERENCES account_master(code) NOT VALID;
                EXCEPTION WHEN duplicate_object THEN NULL;
                END $$;
            """)

        conn.commit()

        # 5. Validate FKs separately (can be slow but non-blocking)
        for table, column, constraint_name in fk_definitions:
            try:
                cur.execute(f"ALTER TABLE {table} VALIDATE CONSTRAINT {constraint_name};")
                conn.commit()
                print(f"  Validated {constraint_name}")
            except Exception as e:
                conn.rollback()
                print(f"  Warning: Could not validate {constraint_name}: {e}")

        print("Migration 001 complete: account_master created with seed data and FK constraints.")

    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    run()
