"""
Seed script: 2023 + 2024 closed years + 2025 draft plan.

Usage:
    cd backend && python seed_2023.py          # seed (if no data yet)
    cd backend && python seed_2023.py --clean   # delete all + regenerate
"""
import uuid
import sys
import os
import random
from datetime import datetime, date, timedelta

sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from passlib.context import CryptContext

try:
    from common.config import settings
    from common.database import Base
    from common.models.user import User, UserRole
    from common.models.department import Department
    from common.models.partner import Partner, PartnerType
    from common.models.scenario import Scenario
    from common.models.planning_period import PlanningPeriod
    from common.models.budget_line import BudgetLine, BudgetStatus
    from common.models.purchase_order import PurchaseOrder, POStatus
    from common.models.purchase_order_line import PurchaseOrderLine
    from common.models.purchase_order_approval import PurchaseOrderApproval
    from common.models.goods_receipt import GoodsReceipt, GoodsReceiptLine
    from common.models.invoice import Invoice, InvoiceLine, MatchStatus
    from common.models.invoice_approval import InvoiceApproval
    from common.models.accounting_entry import AccountingEntry, EntryType
except ImportError:
    from app.config import settings
    from app.database import Base
    from app.models.user import User, UserRole
    from app.models.department import Department
    from app.models.partner import Partner, PartnerType
    from app.models.scenario import Scenario
    from app.models.planning_period import PlanningPeriod
    from app.models.budget_line import BudgetLine, BudgetStatus
    from app.models.purchase_order import PurchaseOrder, POStatus
    from app.models.purchase_order_line import PurchaseOrderLine
    from app.models.purchase_order_approval import PurchaseOrderApproval
    from app.models.goods_receipt import GoodsReceipt, GoodsReceiptLine
    from app.models.invoice import Invoice, InvoiceLine, MatchStatus
    from app.models.invoice_approval import InvoiceApproval
    from app.models.accounting_entry import AccountingEntry, EntryType

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SEASONAL = [0.85, 0.90, 1.00, 1.05, 1.10, 1.15, 1.10, 1.05, 1.00, 0.95, 0.90, 0.80]

USERS_DATA = [
    ("dept.head@invoice.local", "Kovács Péter", "department_head"),
    ("cfo@invoice.local", "Nagy Mária", "cfo"),
    ("accountant@invoice.local", "Szabó Anna", "accountant"),
    ("reviewer@invoice.local", "Tóth Gábor", "reviewer"),
]

DEPARTMENTS_DATA = [
    ("IT", "Informatika"),
    ("MKT", "Marketing"),
    ("OPS", "Operáció"),
    ("HR", "HR"),
    ("SALES", "Értékesítés"),
]

PARTNERS_DATA = [
    ("TechPro Solutions Kft.", "10000001-2-42"),
    ("DataServ Hungary Zrt.", "10000002-2-41"),
    ("CloudBase Kft.", "10000003-2-43"),
    ("OfficePro Bt.", "10000004-2-42"),
    ("MediaMax Kft.", "10000005-2-41"),
    ("HR Konsulting Zrt.", "10000006-2-43"),
    ("LogiTrans Kft.", "10000007-2-42"),
    ("SecureIT Kft.", "10000008-2-41"),
    ("PrintHouse Nyomda Kft.", "10000009-2-43"),
    ("FacilityPro Kft.", "10000010-2-42"),
    ("SalesForce Partner Kft.", "10000011-2-41"),
    ("TrainPro Oktatás Kft.", "10000012-2-43"),
]

# Monthly base amounts per department (HUF)
#                   revenue    cogs      opex     depreciation  interest   tax
BUDGET_MATRIX_2023 = {
    "IT":    [35_000_000, 14_000_000,  8_000_000, 2_000_000,   500_000, 1_500_000],
    "MKT":   [25_000_000,  8_000_000,  6_000_000, 1_000_000,   300_000, 1_200_000],
    "OPS":   [40_000_000, 18_000_000,  7_000_000, 3_000_000,   800_000, 1_800_000],
    "HR":    [15_000_000,  5_000_000,  4_000_000,   500_000,   200_000,   800_000],
    "SALES": [50_000_000, 20_000_000, 10_000_000, 1_500_000,   600_000, 2_000_000],
}

# 2024: ~8% growth vs 2023
BUDGET_MATRIX_2024 = {
    k: [round(v * 1.08) for v in vals]
    for k, vals in BUDGET_MATRIX_2023.items()
}

# 2025: ~6% growth vs 2024
BUDGET_MATRIX_2025 = {
    k: [round(v * 1.06) for v in vals]
    for k, vals in BUDGET_MATRIX_2024.items()
}

PNL_CATEGORIES = ["revenue", "cogs", "opex", "depreciation", "interest", "tax"]
ACCOUNT_CODES = {"revenue": "4100", "cogs": "5100", "opex": "6100",
                 "depreciation": "7100", "interest": "8100", "tax": "9100"}
ACCOUNT_NAMES = {
    "revenue": "Árbevétel", "cogs": "Közvetlen költség",
    "opex": "Működési költség", "depreciation": "Értékcsökkenés",
    "interest": "Pénzügyi ráfordítás", "tax": "Adófizetési kötelezettség",
}
SORT_ORDERS = {"revenue": 10, "cogs": 20, "opex": 30,
               "depreciation": 40, "interest": 50, "tax": 60}

SEED_YEARS = [2023, 2024, 2025]


def uid():
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

def cleanup_orphans(conn):
    """Delete orphan budget lines (no planning_period_id) and cascade."""
    print("\n=== Cleanup orphans ===")

    orphan_count = conn.execute(
        text("SELECT COUNT(*) FROM budget_lines WHERE planning_period_id IS NULL")
    ).fetchone()[0]

    if orphan_count:
        orphan_po_q = ("SELECT id FROM purchase_orders WHERE budget_line_id IN "
                       "(SELECT id FROM budget_lines WHERE planning_period_id IS NULL)")
        conn.execute(text(
            f"DELETE FROM accounting_entries WHERE invoice_id IN "
            f"(SELECT id FROM invoices WHERE purchase_order_id IN ({orphan_po_q}))"
        ))
        conn.execute(text(
            f"DELETE FROM invoice_approvals WHERE invoice_id IN "
            f"(SELECT id FROM invoices WHERE purchase_order_id IN ({orphan_po_q}))"
        ))
        conn.execute(text(
            f"DELETE FROM invoice_lines WHERE invoice_id IN "
            f"(SELECT id FROM invoices WHERE purchase_order_id IN ({orphan_po_q}))"
        ))
        conn.execute(text(
            f"DELETE FROM invoices WHERE purchase_order_id IN ({orphan_po_q})"
        ))
        conn.execute(text(
            f"DELETE FROM goods_receipt_lines WHERE goods_receipt_id IN "
            f"(SELECT id FROM goods_receipts WHERE purchase_order_id IN ({orphan_po_q}))"
        ))
        conn.execute(text(
            f"DELETE FROM goods_receipts WHERE purchase_order_id IN ({orphan_po_q})"
        ))
        conn.execute(text(
            f"DELETE FROM purchase_order_lines WHERE purchase_order_id IN ({orphan_po_q})"
        ))
        conn.execute(text(
            f"DELETE FROM purchase_order_approvals WHERE purchase_order_id IN ({orphan_po_q})"
        ))
        conn.execute(text(
            "DELETE FROM purchase_orders WHERE budget_line_id IN "
            "(SELECT id FROM budget_lines WHERE planning_period_id IS NULL)"
        ))
        conn.execute(text(
            "DELETE FROM budget_line_comments WHERE budget_line_id IN "
            "(SELECT id FROM budget_lines WHERE planning_period_id IS NULL)"
        ))
        result = conn.execute(text("DELETE FROM budget_lines WHERE planning_period_id IS NULL"))
        print(f"  Deleted {result.rowcount} orphan budget lines + cascaded data")
    else:
        print("  No orphan budget lines")

    # Orphan accounting entries
    result = conn.execute(text(
        "DELETE FROM accounting_entries WHERE invoice_id NOT IN (SELECT id FROM invoices)"
    ))
    if result.rowcount:
        print(f"  Deleted {result.rowcount} orphan accounting entries")

    conn.execute(text("ALTER TABLE budget_lines ALTER COLUMN planning_period_id SET NOT NULL"))
    print("  budget_lines.planning_period_id = NOT NULL")
    conn.commit()


def clean_seed_data(conn):
    """Remove all seed data for re-generation."""
    print("\n=== Cleaning ALL seed data ===")

    for year in SEED_YEARS:
        prefix_inv = f"SEED-{year}-%"
        prefix_po = f"PO-{year}-%"

        # Accounting entries → invoice approvals → invoice lines → invoices
        conn.execute(text(
            f"DELETE FROM accounting_entries WHERE invoice_id IN "
            f"(SELECT id FROM invoices WHERE invoice_number LIKE :p)"
        ), {"p": prefix_inv})
        conn.execute(text(
            f"DELETE FROM invoice_approvals WHERE invoice_id IN "
            f"(SELECT id FROM invoices WHERE invoice_number LIKE :p)"
        ), {"p": prefix_inv})
        conn.execute(text(
            f"DELETE FROM invoice_lines WHERE invoice_id IN "
            f"(SELECT id FROM invoices WHERE invoice_number LIKE :p)"
        ), {"p": prefix_inv})
        conn.execute(text("DELETE FROM invoices WHERE invoice_number LIKE :p"), {"p": prefix_inv})

        # GR lines → GRs → PO lines → PO approvals → POs
        conn.execute(text(
            f"DELETE FROM goods_receipt_lines WHERE goods_receipt_id IN "
            f"(SELECT id FROM goods_receipts WHERE purchase_order_id IN "
            f"(SELECT id FROM purchase_orders WHERE po_number LIKE :p))"
        ), {"p": prefix_po})
        conn.execute(text(
            f"DELETE FROM goods_receipts WHERE purchase_order_id IN "
            f"(SELECT id FROM purchase_orders WHERE po_number LIKE :p)"
        ), {"p": prefix_po})
        conn.execute(text(
            f"DELETE FROM purchase_order_lines WHERE purchase_order_id IN "
            f"(SELECT id FROM purchase_orders WHERE po_number LIKE :p)"
        ), {"p": prefix_po})
        conn.execute(text(
            f"DELETE FROM purchase_order_approvals WHERE purchase_order_id IN "
            f"(SELECT id FROM purchase_orders WHERE po_number LIKE :p)"
        ), {"p": prefix_po})
        conn.execute(text("DELETE FROM purchase_orders WHERE po_number LIKE :p"), {"p": prefix_po})

        # Budget lines for this year's PP
        conn.execute(text(
            "DELETE FROM budget_line_comments WHERE budget_line_id IN "
            "(SELECT id FROM budget_lines WHERE planning_period_id IN "
            "(SELECT id FROM planning_periods WHERE year = :y))"
        ), {"y": year})
        conn.execute(text(
            "DELETE FROM budget_lines WHERE planning_period_id IN "
            "(SELECT id FROM planning_periods WHERE year = :y)"
        ), {"y": year})
        conn.execute(text("DELETE FROM planning_periods WHERE year = :y"), {"y": year})

    # Seed users
    for email, _, _ in USERS_DATA:
        conn.execute(text("DELETE FROM users WHERE email = :e"), {"e": email})

    # Seed partners
    for _, tax in PARTNERS_DATA:
        conn.execute(text("DELETE FROM partners WHERE tax_number = :t"), {"t": tax})

    conn.commit()
    print("  Done")


# ---------------------------------------------------------------------------
# Infrastructure (shared across all years)
# ---------------------------------------------------------------------------

def get_or_create_admin(db):
    row = db.execute(text("SELECT id FROM users WHERE role = 'admin' LIMIT 1")).fetchone()
    return row[0] if row else None


def ensure_users(db, admin_id):
    hashed = pwd_context.hash("Demo123")
    user_map = {}
    for email, full_name, role in USERS_DATA:
        existing = db.execute(text("SELECT id FROM users WHERE email = :e"), {"e": email}).fetchone()
        if existing:
            user_map[role] = existing[0]
        else:
            uid_ = uid()
            db.add(User(id=uid_, email=email, full_name=full_name,
                        password_hash=hashed, role=UserRole(role), is_active=True))
            user_map[role] = uid_
    db.flush()
    print(f"  Users: {len(user_map)}")
    return user_map


def ensure_departments(db, admin_id):
    dept_map = {}
    for code, name in DEPARTMENTS_DATA:
        existing = db.execute(text("SELECT id FROM departments WHERE code = :c"), {"c": code}).fetchone()
        if existing:
            dept_map[code] = existing[0]
        else:
            uid_ = uid()
            db.add(Department(id=uid_, name=name, code=code, manager_id=admin_id))
            dept_map[code] = uid_
    db.flush()
    print(f"  Departments: {len(dept_map)}")
    return dept_map


def ensure_partners(db):
    partner_ids = []
    for name, tax in PARTNERS_DATA:
        existing = db.execute(text("SELECT id FROM partners WHERE tax_number = :t"), {"t": tax}).fetchone()
        if existing:
            partner_ids.append(existing[0])
        else:
            uid_ = uid()
            db.add(Partner(id=uid_, name=name, tax_number=tax, partner_type=PartnerType.supplier))
            partner_ids.append(uid_)
    db.flush()
    print(f"  Partners: {len(partner_ids)}")
    return partner_ids


def get_or_create_scenario(db, admin_id):
    row = db.execute(text("SELECT id FROM scenarios WHERE is_default = true LIMIT 1")).fetchone()
    if row:
        return row[0]
    row = db.execute(text("SELECT id FROM scenarios WHERE name = 'Base' LIMIT 1")).fetchone()
    if row:
        return row[0]
    sid = uid()
    db.add(Scenario(id=sid, name="Base", is_default=True, created_by=admin_id))
    db.flush()
    return sid


def ensure_planning_period(db, admin_id, scenario_id, year, name):
    row = db.execute(
        text("SELECT id FROM planning_periods WHERE year = :y AND plan_type = 'budget' LIMIT 1"),
        {"y": year}
    ).fetchone()
    if row:
        return row[0]
    pid = uid()
    db.add(PlanningPeriod(
        id=pid, name=name, year=year,
        start_month=1, end_month=12, plan_type="budget",
        scenario_id=scenario_id, created_by=admin_id,
    ))
    db.flush()
    print(f"  PlanningPeriod: {name} ({pid})")
    return pid


# ---------------------------------------------------------------------------
# Closed year seeder (2023, 2024)
# ---------------------------------------------------------------------------

def seed_closed_year(db, year, budget_matrix, dept_map, planning_period_id,
                     scenario_id, user_map, admin_id):
    """Seed a fully closed year: budget(locked) → POs(closed) → invoices(posted) → accounting."""
    random.seed(year)
    print(f"\n{'='*60}")
    print(f"  SEEDING {year} (closed year)")
    print(f"{'='*60}")

    # --- Budget Lines (360) ---
    lines = []
    for dept_code in ["IT", "MKT", "OPS", "HR", "SALES"]:
        dept_id = dept_map[dept_code]
        base_amounts = budget_matrix[dept_code]
        for month_idx in range(12):
            period = f"{year}-{month_idx + 1:02d}"
            multiplier = SEASONAL[month_idx]
            for cat_idx, cat in enumerate(PNL_CATEGORIES):
                amount = round(base_amounts[cat_idx] * multiplier)
                lines.append(BudgetLine(
                    id=uid(), department_id=dept_id,
                    account_code=ACCOUNT_CODES[cat], account_name=ACCOUNT_NAMES[cat],
                    period=period, planned_amount=amount, currency="HUF",
                    status=BudgetStatus.locked, pnl_category=cat,
                    sort_order=SORT_ORDERS[cat], plan_type="budget",
                    scenario_id=scenario_id, planning_period_id=planning_period_id,
                    created_by=admin_id, approved_by=admin_id,
                ))
    db.add_all(lines)
    db.flush()
    print(f"  Budget lines: {len(lines)}")

    # --- Purchase Orders (120) ---
    bl_index = {}
    for bl in lines:
        bl_index[(bl.department_id, bl.period, bl.pnl_category)] = bl

    pos = []
    po_counter = 0
    dept_head_id = user_map.get("department_head", admin_id)
    cfo_id = user_map.get("cfo", admin_id)

    for dept_code in ["IT", "MKT", "OPS", "HR", "SALES"]:
        dept_id = dept_map[dept_code]
        for month_idx in range(12):
            period = f"{year}-{month_idx + 1:02d}"
            for cat in ["cogs", "opex"]:
                bl = bl_index.get((dept_id, period, cat))
                if not bl:
                    continue
                po_counter += 1
                po_amount = round(bl.planned_amount * random.uniform(0.85, 0.95))
                supplier_name, supplier_tax = PARTNERS_DATA[random.randint(0, 11)]
                po_id = uid()
                pos.append(PurchaseOrder(
                    id=po_id, po_number=f"PO-{year}-{po_counter:03d}",
                    department_id=dept_id, budget_line_id=bl.id,
                    supplier_name=supplier_name, supplier_tax_id=supplier_tax,
                    amount=po_amount, currency="HUF", accounting_code=bl.account_code,
                    description=f"{bl.account_name} – {dept_code} {period}",
                    status=POStatus.closed, created_by=admin_id, approved_by=cfo_id,
                ))
                for step, (sn, role, decider) in enumerate([
                    ("Osztályvezető", "department_head", dept_head_id),
                    ("CFO", "cfo", cfo_id),
                ], start=1):
                    db.add(PurchaseOrderApproval(
                        id=uid(), purchase_order_id=po_id, step=step,
                        step_name=sn, status="approved", assigned_role=role,
                        decided_by=decider,
                        decided_at=datetime(year, month_idx + 1, min(step + 1, 28), 10, 0),
                    ))
    db.add_all(pos)
    db.flush()
    print(f"  Purchase orders: {len(pos)}")

    # --- PO Lines + Goods Receipts ---
    po_lines_map = {}  # po_id -> [PurchaseOrderLine]
    gr_counter = 0
    for po in pos:
        num_lines = random.randint(1, 3)
        remaining = po.amount
        po_line_objs = []
        for li in range(num_lines):
            if li == num_lines - 1:
                line_amount = remaining
            else:
                line_amount = round(po.amount / num_lines)
                remaining -= line_amount
            qty = random.choice([1, 2, 5, 10])
            unit_price = round(line_amount / qty, 2)
            net = round(qty * unit_price, 2)
            pol = PurchaseOrderLine(
                id=uid(), purchase_order_id=po.id,
                description=f"{po.description} – tétel {li + 1}",
                quantity=qty, unit_price=unit_price, net_amount=net,
                sort_order=li,
            )
            db.add(pol)
            po_line_objs.append(pol)
        po_lines_map[po.id] = po_line_objs

        # Goods Receipt for every closed PO
        gr_counter += 1
        month = int(po.po_number.split("-")[2]) if po.po_number.count("-") >= 2 else 1
        # Derive month from po_counter position
        po_idx_in_year = gr_counter
        po_month = ((po_idx_in_year - 1) // 10) + 1  # ~10 POs per month
        po_month = max(1, min(12, po_month))
        gr_day = random.randint(10, 28)
        gr = GoodsReceipt(
            id=uid(), gr_number=f"GR-{year}-{gr_counter:03d}",
            purchase_order_id=po.id,
            received_date=date(year, po_month, gr_day),
            received_by=dept_head_id,
        )
        db.add(gr)
        db.flush()

        for pol in po_line_objs:
            db.add(GoodsReceiptLine(
                id=uid(), goods_receipt_id=gr.id,
                purchase_order_line_id=pol.id,
                quantity_received=pol.quantity,
            ))

    db.flush()
    print(f"  PO lines: {sum(len(v) for v in po_lines_map.values())}")
    print(f"  Goods receipts: {gr_counter}")

    # --- Invoices (120) ---
    invoices = []
    reviewer_id = user_map.get("reviewer", admin_id)
    accountant_id = user_map.get("accountant", admin_id)

    for idx, po in enumerate(pos):
        inv_counter = idx + 1
        month = (idx % 12) + 1
        day = random.randint(5, 28)
        inv_date = date(year, month, day)

        net_amount = round(po.amount * random.uniform(0.97, 1.03))
        vat_amount = round(net_amount * 0.27)
        gross_amount = net_amount + vat_amount

        partner_row = db.execute(
            text("SELECT id FROM partners WHERE tax_number = :t LIMIT 1"),
            {"t": po.supplier_tax_id}
        ).fetchone()
        partner_id = partner_row[0] if partner_row else None

        inv_id = uid()
        invoices.append(Invoice(
            id=inv_id, invoice_number=f"SEED-{year}-{inv_counter:03d}",
            partner_id=partner_id, status="posted", match_status="posted",
            invoice_date=inv_date, due_date=inv_date + timedelta(days=30),
            net_amount=net_amount, vat_rate=27.0, vat_amount=vat_amount,
            gross_amount=gross_amount, currency="HUF",
            original_filename=f"seed_{year}_{inv_counter:03d}.pdf",
            stored_filepath=f"seed/{year}/{inv_counter:03d}.pdf",
            purchase_order_id=po.id, accounting_code=po.accounting_code,
            uploaded_by_id=accountant_id,
            approved_at=datetime(year, month, min(day + 5, 28), 14, 0),
        ))

        # Invoice Lines (1-3)
        num_lines = random.randint(1, 3)
        remaining = net_amount
        for li in range(num_lines):
            line_net = remaining if li == num_lines - 1 else round(net_amount / num_lines)
            if li < num_lines - 1:
                remaining -= line_net
            line_vat = round(line_net * 0.27)
            db.add(InvoiceLine(
                id=uid(), invoice_id=inv_id, description=f"Tétel {li + 1}",
                quantity=1.0, unit_price=line_net, net_amount=line_net,
                vat_rate=27.0, vat_amount=line_vat, gross_amount=line_net + line_vat,
                sort_order=li,
            ))

        # Invoice Approvals (3 steps)
        for step, (sn, role, decider) in enumerate([
            ("Ellenőrzés", "reviewer", reviewer_id),
            ("Osztályvezető", "department_head", dept_head_id),
            ("CFO jóváhagyás", "cfo", cfo_id),
        ], start=1):
            db.add(InvoiceApproval(
                id=uid(), invoice_id=inv_id, step=step, step_name=sn,
                status="approved", assigned_role=role, decided_by=decider,
                decided_at=datetime(year, month, min(day + step + 2, 28), 10, 0),
            ))

    db.add_all(invoices)
    db.flush()
    print(f"  Invoices: {len(invoices)}")

    # --- Accounting Entries (3 per invoice = 360) ---
    entries = []
    for inv in invoices:
        period = inv.invoice_date.strftime("%Y-%m")
        posted_at = datetime.combine(inv.invoice_date + timedelta(days=2), datetime.min.time())

        po_row = db.execute(
            text("SELECT department_id FROM purchase_orders WHERE id = :pid"),
            {"pid": inv.purchase_order_id}
        ).fetchone()
        dept_id = po_row[0] if po_row else None

        entries.append(AccountingEntry(
            id=uid(), invoice_id=inv.id, purchase_order_id=inv.purchase_order_id,
            account_code=inv.accounting_code, department_id=dept_id,
            amount=inv.net_amount, currency="HUF", period=period,
            entry_type=EntryType.debit, posted_at=posted_at, posted_by=accountant_id,
        ))
        entries.append(AccountingEntry(
            id=uid(), invoice_id=inv.id, purchase_order_id=inv.purchase_order_id,
            account_code="466", department_id=dept_id,
            amount=inv.vat_amount, currency="HUF", period=period,
            entry_type=EntryType.debit, posted_at=posted_at, posted_by=accountant_id,
        ))
        entries.append(AccountingEntry(
            id=uid(), invoice_id=inv.id, purchase_order_id=inv.purchase_order_id,
            account_code="454", department_id=dept_id,
            amount=inv.gross_amount, currency="HUF", period=period,
            entry_type=EntryType.credit, posted_at=posted_at, posted_by=accountant_id,
        ))

    db.add_all(entries)
    db.flush()
    print(f"  Accounting entries: {len(entries)}")

    return lines, pos, invoices, entries


# ---------------------------------------------------------------------------
# Draft year seeder (2025)
# ---------------------------------------------------------------------------

def seed_draft_year(db, year, budget_matrix, dept_map, planning_period_id,
                    scenario_id, admin_id):
    """Seed a draft planning year: only budget lines in draft status, no POs/invoices."""
    random.seed(year)
    print(f"\n{'='*60}")
    print(f"  SEEDING {year} (draft plan)")
    print(f"{'='*60}")

    lines = []
    for dept_code in ["IT", "MKT", "OPS", "HR", "SALES"]:
        dept_id = dept_map[dept_code]
        base_amounts = budget_matrix[dept_code]
        for month_idx in range(12):
            period = f"{year}-{month_idx + 1:02d}"
            multiplier = SEASONAL[month_idx]
            for cat_idx, cat in enumerate(PNL_CATEGORIES):
                amount = round(base_amounts[cat_idx] * multiplier)
                lines.append(BudgetLine(
                    id=uid(), department_id=dept_id,
                    account_code=ACCOUNT_CODES[cat], account_name=ACCOUNT_NAMES[cat],
                    period=period, planned_amount=amount, currency="HUF",
                    status=BudgetStatus.draft, pnl_category=cat,
                    sort_order=SORT_ORDERS[cat], plan_type="budget",
                    scenario_id=scenario_id, planning_period_id=planning_period_id,
                    created_by=admin_id,
                ))
    db.add_all(lines)
    db.flush()
    print(f"  Budget lines (draft): {len(lines)}")
    return lines


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_year(label, budget_lines, pos, invoices, entries):
    print(f"\n  === Validation: {label} ===")
    errors = 0

    for inv in invoices:
        debits = sum(e.amount for e in entries if e.invoice_id == inv.id and e.entry_type == EntryType.debit)
        credits = sum(e.amount for e in entries if e.invoice_id == inv.id and e.entry_type == EntryType.credit)
        if abs(debits - credits) > 1:
            print(f"  FAIL balance: {inv.invoice_number} debit={debits} credit={credits}")
            errors += 1

    po_by_bl = {}
    for po in pos:
        po_by_bl.setdefault(po.budget_line_id, []).append(po)
    for bl in budget_lines:
        bl_pos = po_by_bl.get(bl.id, [])
        total_po = sum(p.amount for p in bl_pos)
        if total_po > bl.planned_amount:
            print(f"  FAIL coverage: {bl.period} {bl.pnl_category}")
            errors += 1

    # P&L summary
    totals = {cat: 0 for cat in PNL_CATEGORIES}
    for bl in budget_lines:
        totals[bl.pnl_category] += bl.planned_amount

    revenue = totals["revenue"]
    cogs = totals["cogs"]
    gross_profit = revenue - cogs
    opex = totals["opex"]
    ebitda = gross_profit - opex
    dep = totals["depreciation"]
    ebit = ebitda - dep
    interest = totals["interest"]
    ebt = ebit - interest
    tax = totals["tax"]
    net_income = ebt - tax

    def fmt(v):
        return f"{v / 1_000_000:,.1f}M HUF"

    print(f"  Revenue:      {fmt(revenue)}")
    print(f"  COGS:        -{fmt(cogs)}")
    print(f"  Gross Profit: {fmt(gross_profit)}")
    print(f"  OpEx:        -{fmt(opex)}")
    print(f"  EBITDA:       {fmt(ebitda)}")
    print(f"  Net Income:   {fmt(net_income)}")

    if errors == 0:
        print(f"  All checks PASSED")
    else:
        print(f"  {errors} FAILURES")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def seed():
    clean_mode = "--clean" in sys.argv
    engine = create_engine(settings.DATABASE_URL_SYNC, echo=False)
    Base.metadata.create_all(engine)

    with engine.connect() as conn:
        if clean_mode:
            clean_seed_data(conn)
        cleanup_orphans(conn)

    with Session(engine) as db:
        # Check if already seeded
        existing = db.execute(
            text("SELECT COUNT(*) FROM budget_lines WHERE period LIKE '2023-%'")
        ).fetchone()
        if existing and existing[0] > 0 and not clean_mode:
            print("Seed data already exists. Use --clean to regenerate.")
            return

        admin_id = get_or_create_admin(db)
        if not admin_id:
            print("ERROR: No admin user found.")
            return

        print("\n=== Infrastructure ===")
        user_map = ensure_users(db, admin_id)
        dept_map = ensure_departments(db, admin_id)
        ensure_partners(db)
        scenario_id = get_or_create_scenario(db, admin_id)

        # --- 2023 (closed) ---
        pp_2023 = ensure_planning_period(db, admin_id, scenario_id, 2023, "2023 Éves Terv")
        bl23, po23, inv23, ae23 = seed_closed_year(
            db, 2023, BUDGET_MATRIX_2023, dept_map, pp_2023, scenario_id, user_map, admin_id)

        # --- 2024 (closed, +8% growth) ---
        pp_2024 = ensure_planning_period(db, admin_id, scenario_id, 2024, "2024 Éves Terv")
        bl24, po24, inv24, ae24 = seed_closed_year(
            db, 2024, BUDGET_MATRIX_2024, dept_map, pp_2024, scenario_id, user_map, admin_id)

        # --- 2025 (draft plan, +6% growth) ---
        pp_2025 = ensure_planning_period(db, admin_id, scenario_id, 2025, "2025 Éves Terv")
        bl25 = seed_draft_year(
            db, 2025, BUDGET_MATRIX_2025, dept_map, pp_2025, scenario_id, admin_id)

        db.commit()
        print("\n\nSeed committed!")

        # Validation
        print("\n" + "=" * 60)
        print("  VALIDATION")
        print("=" * 60)
        validate_year("2023", bl23, po23, inv23, ae23)
        validate_year("2024", bl24, po24, inv24, ae24)

        print(f"\n  === 2025 (draft, no actuals) ===")
        totals = {cat: 0 for cat in PNL_CATEGORIES}
        for bl in bl25:
            totals[bl.pnl_category] += bl.planned_amount
        fmt = lambda v: f"{v / 1_000_000:,.1f}M HUF"
        print(f"  Revenue:      {fmt(totals['revenue'])}")
        print(f"  COGS:        -{fmt(totals['cogs'])}")
        print(f"  OpEx:        -{fmt(totals['opex'])}")
        print(f"  Budget lines: {len(bl25)} (all draft)")

        # Final counts
        print("\n" + "=" * 60)
        print("  TOTALS")
        print("=" * 60)
        for table in ["planning_periods", "budget_lines", "purchase_orders",
                       "invoices", "accounting_entries"]:
            r = db.execute(text(f"SELECT COUNT(*) FROM {table}")).fetchone()
            print(f"  {table}: {r[0]}")

    print("\nDone!")


if __name__ == "__main__":
    seed()
