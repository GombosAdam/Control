"""
Seed script for the Controlling module demo data.
Run: cd backend && python seed_controlling.py
"""
import uuid
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from app.config import settings
from app.database import Base
from app.models.department import Department
from app.models.budget_line import BudgetLine, BudgetStatus
from app.models.purchase_order import PurchaseOrder, POStatus
from app.models.accounting_entry import AccountingEntry, EntryType
from app.models.invoice import Invoice, MatchStatus


def seed():
    engine = create_engine(settings.DATABASE_URL_SYNC, echo=False)

    # Ensure new tables exist
    Base.metadata.create_all(engine)

    # Add new columns to invoices if missing
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE invoices ADD COLUMN IF NOT EXISTS purchase_order_id VARCHAR(36)"))
            conn.execute(text("ALTER TABLE invoices ADD COLUMN IF NOT EXISTS match_status VARCHAR(20) DEFAULT 'unmatched'"))
            conn.execute(text("ALTER TABLE invoices ADD COLUMN IF NOT EXISTS accounting_code VARCHAR(20)"))
            conn.commit()
        except Exception as e:
            print(f"ALTER TABLE note: {e}")
            conn.rollback()

    with Session(engine) as db:
        # Check if already seeded
        existing = db.query(Department).first()
        if existing:
            print("Controlling data already seeded. Skipping.")
            return

        # Get admin user
        admin = db.execute(text("SELECT id FROM users WHERE role = 'admin' LIMIT 1")).fetchone()
        admin_id = admin[0] if admin else str(uuid.uuid4())

        # 1. Departments
        departments = [
            Department(id=str(uuid.uuid4()), name="Pénzügy", code="FIN", manager_id=admin_id),
            Department(id=str(uuid.uuid4()), name="IT", code="IT", manager_id=admin_id),
            Department(id=str(uuid.uuid4()), name="HR", code="HR", manager_id=admin_id),
            Department(id=str(uuid.uuid4()), name="Marketing", code="MKT", manager_id=admin_id),
            Department(id=str(uuid.uuid4()), name="Logisztika", code="LOG", manager_id=admin_id),
        ]
        db.add_all(departments)
        db.flush()
        print(f"Created {len(departments)} departments")

        # 2. Budget lines — 4 per department, Q1 2024
        budget_lines = []
        accounts = [
            ("5110", "Alapanyag költség"),
            ("5210", "Szolgáltatás költség"),
            ("5310", "Személyi jellegű ráfordítás"),
            ("5410", "Egyéb működési költség"),
        ]
        periods = ["2024-01", "2024-02", "2024-03", "2024-04"]
        amounts = [5000000, 3000000, 8000000, 2000000]

        for dept in departments:
            for i, (code, name) in enumerate(accounts):
                bl = BudgetLine(
                    id=str(uuid.uuid4()),
                    department_id=dept.id,
                    account_code=code,
                    account_name=name,
                    period=periods[i],
                    planned_amount=amounts[i],
                    currency="HUF",
                    status=BudgetStatus.approved,
                    created_by=admin_id,
                    approved_by=admin_id,
                )
                budget_lines.append(bl)
        db.add_all(budget_lines)
        db.flush()
        print(f"Created {len(budget_lines)} budget lines")

        # 3. Purchase Orders — 10 POs linked to budget lines
        suppliers = [
            ("Alfa Kft.", "12345678-2-42"),
            ("Beta Solutions Zrt.", "87654321-2-41"),
            ("Gamma Tech Bt.", "11223344-2-43"),
            ("Delta Szolg. Kft.", "44332211-2-44"),
            ("Epsilon Logisztika Kft.", "55667788-2-45"),
        ]

        purchase_orders = []
        po_counter = 1
        for dept_idx in range(5):
            for bl_idx in range(2):  # 2 PO per department
                bl = budget_lines[dept_idx * 4 + bl_idx]
                supplier = suppliers[dept_idx]
                po = PurchaseOrder(
                    id=str(uuid.uuid4()),
                    po_number=f"PO-2024-{po_counter:03d}",
                    department_id=departments[dept_idx].id,
                    budget_line_id=bl.id,
                    supplier_name=supplier[0],
                    supplier_tax_id=supplier[1],
                    amount=bl.planned_amount * 0.4,  # 40% of budget
                    currency="HUF",
                    accounting_code=bl.account_code,
                    description=f"Megrendelés - {bl.account_name}",
                    status=POStatus.approved,
                    created_by=admin_id,
                    approved_by=admin_id,
                )
                purchase_orders.append(po)
                po_counter += 1
        db.add_all(purchase_orders)
        db.flush()
        print(f"Created {len(purchase_orders)} purchase orders")

        # 4. Match existing approved invoices to POs
        approved_invoices = db.execute(
            text("SELECT id, gross_amount, currency FROM invoices WHERE status = 'approved' LIMIT 2")
        ).fetchall()

        for idx, inv_row in enumerate(approved_invoices):
            if idx < len(purchase_orders):
                po = purchase_orders[idx]
                db.execute(text(
                    "UPDATE invoices SET purchase_order_id = :po_id, match_status = 'posted', accounting_code = :acc_code WHERE id = :inv_id"
                ), {"po_id": po.id, "inv_id": inv_row[0], "acc_code": po.accounting_code})

                # Create accounting entry
                entry = AccountingEntry(
                    id=str(uuid.uuid4()),
                    invoice_id=inv_row[0],
                    purchase_order_id=po.id,
                    account_code=po.accounting_code,
                    department_id=po.department_id,
                    amount=float(inv_row[1]) if inv_row[1] else po.amount,
                    currency=inv_row[2] or "HUF",
                    period="2024-01",
                    entry_type=EntryType.debit,
                    posted_at=datetime.utcnow(),
                    posted_by=admin_id,
                )
                db.add(entry)
        print(f"Matched {len(approved_invoices)} invoices to POs")

        # 5. Additional accounting entries for demo
        extra_entries = []
        for dept_idx in range(3):  # First 3 departments get extra entries
            bl = budget_lines[dept_idx * 4]  # First budget line of each dept
            entry = AccountingEntry(
                id=str(uuid.uuid4()),
                invoice_id=approved_invoices[0][0] if approved_invoices else str(uuid.uuid4()),
                purchase_order_id=purchase_orders[dept_idx * 2].id,
                account_code=bl.account_code,
                department_id=departments[dept_idx].id,
                amount=bl.planned_amount * 0.25,
                currency="HUF",
                period=bl.period,
                entry_type=EntryType.debit,
                posted_at=datetime.utcnow(),
                posted_by=admin_id,
            )
            extra_entries.append(entry)
        db.add_all(extra_entries)
        print(f"Created {len(extra_entries)} extra accounting entries")

        db.commit()
        print("\nSeed complete! Controlling demo data is ready.")


if __name__ == "__main__":
    seed()
