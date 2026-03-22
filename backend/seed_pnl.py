"""
Seed script to add P&L structure to existing budget lines + add missing categories.
Run: cd backend && .venv/bin/python seed_pnl.py
"""
import uuid
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import create_engine, text
from app.config import settings


def seed():
    engine = create_engine(settings.DATABASE_URL_SYNC, echo=False)

    with engine.connect() as conn:
        # Add new columns if missing
        try:
            conn.execute(text("ALTER TABLE budget_lines ADD COLUMN IF NOT EXISTS pnl_category VARCHAR(20) DEFAULT 'opex'"))
            conn.execute(text("ALTER TABLE budget_lines ADD COLUMN IF NOT EXISTS sort_order INTEGER DEFAULT 0"))
            conn.commit()
            print("Added pnl_category and sort_order columns")
        except Exception as e:
            print(f"ALTER TABLE note: {e}")
            conn.rollback()

        # Map existing account codes to P&L categories
        conn.execute(text("UPDATE budget_lines SET pnl_category = 'opex', sort_order = 30 WHERE pnl_category IS NULL OR pnl_category = 'opex'"))
        conn.execute(text("UPDATE budget_lines SET pnl_category = 'cogs', sort_order = 20 WHERE account_code = '5110'"))
        conn.execute(text("UPDATE budget_lines SET pnl_category = 'opex', sort_order = 30 WHERE account_code = '5210'"))
        conn.execute(text("UPDATE budget_lines SET pnl_category = 'opex', sort_order = 31 WHERE account_code = '5310'"))
        conn.execute(text("UPDATE budget_lines SET pnl_category = 'opex', sort_order = 32 WHERE account_code = '5410'"))
        conn.commit()
        print("Updated existing budget lines with pnl_category")

        # Get admin user and departments
        admin = conn.execute(text("SELECT id FROM users WHERE role = 'admin' LIMIT 1")).fetchone()
        admin_id = admin[0] if admin else str(uuid.uuid4())

        depts = conn.execute(text("SELECT id, code FROM departments")).fetchall()
        if not depts:
            print("No departments found. Run seed_controlling.py first.")
            return

        # Check if revenue lines already exist
        existing = conn.execute(text("SELECT COUNT(*) FROM budget_lines WHERE pnl_category = 'revenue'")).fetchone()
        if existing and existing[0] > 0:
            print(f"Revenue lines already exist ({existing[0]}). Skipping P&L seed.")
            return

        # P&L line definitions per department
        # (account_code, account_name, pnl_category, sort_order, amount_multiplier)
        pnl_lines = [
            # Revenue
            ("4100", "Termék értékesítés",         "revenue",       10, 1.0),
            ("4200", "Szolgáltatás bevétel",        "revenue",       11, 0.4),
            ("4300", "Egyéb bevétel",               "revenue",       12, 0.1),
            # COGS
            ("5100", "Anyagköltség",                "cogs",          20, 0.25),
            ("5120", "Alvállalkozói díj",           "cogs",          21, 0.10),
            ("5130", "Közvetlen bérköltség",        "cogs",          22, 0.15),
            # OpEx
            ("6100", "Értékesítési költség",         "opex",          30, 0.05),
            ("6200", "Marketing költség",            "opex",          31, 0.04),
            ("6300", "Adminisztrációs költség",      "opex",          32, 0.03),
            ("6400", "IT költség",                   "opex",          33, 0.03),
            ("6500", "HR költség",                   "opex",          34, 0.02),
            ("6600", "Irodabérleti díj",             "opex",          35, 0.03),
            # D&A
            ("7100", "Tárgyi eszköz értékcsökkenés", "depreciation",  40, 0.02),
            ("7200", "Immateriális javak amort.",     "depreciation",  41, 0.01),
            # Interest
            ("8100", "Bankhitel kamat",              "interest",      50, 0.01),
            ("8200", "Pénzügyi költségek",           "interest",      51, 0.005),
            # Tax
            ("9100", "Társasági adó",                "tax",           60, 0.04),
            ("9200", "Iparűzési adó",                "tax",           61, 0.01),
        ]

        # Base revenue per department (different scale for realism)
        dept_revenues = {
            "FIN": 120_000_000,
            "IT":  250_000_000,
            "HR":   80_000_000,
            "MKT": 180_000_000,
            "LOG": 150_000_000,
        }

        periods = ["2024-01", "2024-02", "2024-03"]
        count = 0

        for dept_id, dept_code in depts:
            base_revenue = dept_revenues.get(dept_code, 100_000_000)

            for period in periods:
                for acc_code, acc_name, pnl_cat, sort, multiplier in pnl_lines:
                    amount = base_revenue * multiplier
                    # Slight variation per period
                    if period == "2024-02":
                        amount *= 1.05
                    elif period == "2024-03":
                        amount *= 1.12

                    line_id = str(uuid.uuid4())
                    conn.execute(text("""
                        INSERT INTO budget_lines (id, department_id, account_code, account_name, period,
                            planned_amount, currency, status, pnl_category, sort_order, created_by,
                            created_at, updated_at)
                        VALUES (:id, :dept_id, :acc_code, :acc_name, :period,
                            :amount, 'HUF', 'approved', :pnl_cat, :sort, :user_id,
                            NOW(), NOW())
                    """), {
                        "id": line_id, "dept_id": dept_id, "acc_code": acc_code, "acc_name": acc_name,
                        "period": period, "amount": round(amount), "pnl_cat": pnl_cat, "sort": sort,
                        "user_id": admin_id,
                    })
                    count += 1

        conn.commit()
        print(f"Created {count} P&L budget lines across {len(depts)} departments and {len(periods)} periods")
        print("\nP&L structure seeded successfully!")


if __name__ == "__main__":
    seed()
