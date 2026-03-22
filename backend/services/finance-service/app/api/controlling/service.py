from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from common.models.department import Department
from common.models.budget_line import BudgetLine, BudgetStatus
from common.models.purchase_order import PurchaseOrder, POStatus
from common.models.accounting_entry import AccountingEntry, EntryType


# P&L waterfall structure definition
# Each section: (category_key, label_hu, label_en, sign, is_subtotal)
# sign: 1 = positive (revenue), -1 = cost/expense (subtracted)
PNL_STRUCTURE = [
    {"key": "revenue",       "label": "Bevétel (Revenue)",                     "sign": 1,  "is_subtotal": False, "category": "revenue"},
    {"key": "cogs",          "label": "Közvetlen költségek (COGS)",            "sign": -1, "is_subtotal": False, "category": "cogs"},
    {"key": "gross_profit",  "label": "Bruttó profit (Gross Profit)",          "sign": 1,  "is_subtotal": True,  "formula": "revenue - cogs"},
    {"key": "opex",          "label": "Működési költségek (OpEx)",             "sign": -1, "is_subtotal": False, "category": "opex"},
    {"key": "ebitda",        "label": "EBITDA",                                "sign": 1,  "is_subtotal": True,  "formula": "gross_profit - opex"},
    {"key": "depreciation",  "label": "Értékcsökkenés (D&A)",                 "sign": -1, "is_subtotal": False, "category": "depreciation"},
    {"key": "ebit",          "label": "Működési eredmény (EBIT)",             "sign": 1,  "is_subtotal": True,  "formula": "ebitda - depreciation"},
    {"key": "interest",      "label": "Kamatköltség (Interest)",              "sign": -1, "is_subtotal": False, "category": "interest"},
    {"key": "pbt",           "label": "Adózás előtti eredmény (PBT)",         "sign": 1,  "is_subtotal": True,  "formula": "ebit - interest"},
    {"key": "tax",           "label": "Adó (Tax)",                            "sign": -1, "is_subtotal": False, "category": "tax"},
    {"key": "net_income",    "label": "Nettó eredmény (Net Income)",          "sign": 1,  "is_subtotal": True,  "formula": "pbt - tax"},
]


class ControllingService:
    @staticmethod
    async def plan_vs_actual(db: AsyncSession, department_id: str | None, period: str | None) -> list[dict]:
        query = select(BudgetLine).where(
            BudgetLine.status.in_([BudgetStatus.approved, BudgetStatus.locked])
        )
        if department_id:
            query = query.where(BudgetLine.department_id == department_id)
        if period:
            query = query.where(BudgetLine.period == period)

        result = await db.execute(query.order_by(BudgetLine.period, BudgetLine.account_code))
        lines = result.scalars().all()

        items = []
        for line in lines:
            actual = await db.scalar(
                select(func.coalesce(func.sum(AccountingEntry.amount), 0)).where(
                    AccountingEntry.department_id == line.department_id,
                    AccountingEntry.account_code == line.account_code,
                    AccountingEntry.period == line.period,
                    AccountingEntry.entry_type == EntryType.debit,
                )
            ) or 0

            committed = await db.scalar(
                select(func.coalesce(func.sum(PurchaseOrder.amount), 0)).where(
                    PurchaseOrder.budget_line_id == line.id,
                    PurchaseOrder.status.in_([POStatus.draft, POStatus.approved, POStatus.received, POStatus.closed]),
                )
            ) or 0

            planned = line.planned_amount
            actual_f = float(actual)
            variance = planned - actual_f
            variance_pct = (variance / planned * 100) if planned != 0 else 0

            items.append({
                "department_id": line.department_id,
                "department_name": line.department.name if line.department else None,
                "account_code": line.account_code,
                "account_name": line.account_name,
                "period": line.period,
                "planned": planned,
                "actual": actual_f,
                "committed": float(committed),
                "variance": variance,
                "variance_pct": round(variance_pct, 1),
                "currency": line.currency,
            })

        return items

    @staticmethod
    async def budget_status(db: AsyncSession, department_id: str | None) -> list[dict]:
        query = select(Department)
        if department_id:
            query = query.where(Department.id == department_id)

        result = await db.execute(query.order_by(Department.name))
        departments = result.scalars().all()

        items = []
        for dept in departments:
            planned = await db.scalar(
                select(func.coalesce(func.sum(BudgetLine.planned_amount), 0)).where(
                    BudgetLine.department_id == dept.id,
                    BudgetLine.status.in_([BudgetStatus.approved, BudgetStatus.locked]),
                )
            ) or 0

            committed = await db.scalar(
                select(func.coalesce(func.sum(PurchaseOrder.amount), 0)).where(
                    PurchaseOrder.department_id == dept.id,
                    PurchaseOrder.status.in_([POStatus.draft, POStatus.approved, POStatus.received, POStatus.closed]),
                )
            ) or 0

            spent = await db.scalar(
                select(func.coalesce(func.sum(AccountingEntry.amount), 0)).where(
                    AccountingEntry.department_id == dept.id,
                    AccountingEntry.entry_type == EntryType.debit,
                )
            ) or 0

            planned_f = float(planned)
            committed_f = float(committed)
            spent_f = float(spent)
            available = planned_f - committed_f - spent_f

            items.append({
                "department_id": dept.id,
                "department_name": dept.name,
                "department_code": dept.code,
                "planned": planned_f,
                "committed": committed_f,
                "spent": spent_f,
                "available": available,
                "utilization_pct": round((spent_f / planned_f * 100) if planned_f > 0 else 0, 1),
            })

        return items

    @staticmethod
    async def commitment_report(db: AsyncSession, department_id: str | None) -> list[dict]:
        query = select(PurchaseOrder).where(
            PurchaseOrder.status.in_([POStatus.approved, POStatus.received])
        )
        if department_id:
            query = query.where(PurchaseOrder.department_id == department_id)

        result = await db.execute(query.order_by(PurchaseOrder.created_at.desc()))
        orders = result.scalars().all()

        return [{
            "id": po.id,
            "po_number": po.po_number,
            "department_name": po.department.name if po.department else None,
            "supplier_name": po.supplier_name,
            "amount": po.amount,
            "currency": po.currency,
            "accounting_code": po.accounting_code,
            "status": po.status.value,
            "created_at": po.created_at.isoformat(),
        } for po in orders]

    @staticmethod
    async def ebitda_report(db: AsyncSession, department_id: str | None, period: str | None) -> list[dict]:
        query = select(Department)
        if department_id:
            query = query.where(Department.id == department_id)

        result = await db.execute(query.order_by(Department.name))
        departments = result.scalars().all()

        items = []
        for dept in departments:
            entry_query = select(func.coalesce(func.sum(AccountingEntry.amount), 0)).where(
                AccountingEntry.department_id == dept.id,
                AccountingEntry.entry_type == EntryType.debit,
            )
            if period:
                entry_query = entry_query.where(AccountingEntry.period == period)

            total_cost = float(await db.scalar(entry_query) or 0)

            budget_query = select(func.coalesce(func.sum(BudgetLine.planned_amount), 0)).where(
                BudgetLine.department_id == dept.id,
                BudgetLine.status.in_([BudgetStatus.approved, BudgetStatus.locked]),
            )
            if period:
                budget_query = budget_query.where(BudgetLine.period == period)

            planned_budget = float(await db.scalar(budget_query) or 0)
            ebitda = planned_budget - total_cost
            margin = round((ebitda / planned_budget * 100) if planned_budget > 0 else 0, 1)

            items.append({
                "department_id": dept.id,
                "department_name": dept.name,
                "planned_budget": planned_budget,
                "actual_cost": total_cost,
                "ebitda": ebitda,
                "margin_pct": margin,
            })

        return items

    @staticmethod
    async def pnl_waterfall(db: AsyncSession, department_id: str | None, period: str | None,
                            status: str | None = None,
                            period_from: str | None = None, period_to: str | None = None,
                            plan_type: str | None = None, scenario_id: str | None = None) -> dict:
        """
        Full P&L waterfall: Revenue -> Gross Profit -> EBITDA -> EBIT -> PBT -> Net Income
        Returns line items grouped by pnl_category with plan/actual/variance,
        plus computed subtotal rows.
        Supports single period, or period_from/period_to range for quarterly/yearly aggregation.
        """
        bl_query = select(BudgetLine)
        if status:
            bl_query = bl_query.where(BudgetLine.status == BudgetStatus(status))
        if department_id:
            bl_query = bl_query.where(BudgetLine.department_id == department_id)
        if plan_type:
            bl_query = bl_query.where(BudgetLine.plan_type == plan_type)
        if scenario_id:
            bl_query = bl_query.where(BudgetLine.scenario_id == scenario_id)
        if period:
            bl_query = bl_query.where(BudgetLine.period == period)
        elif period_from and period_to:
            bl_query = bl_query.where(BudgetLine.period >= period_from, BudgetLine.period <= period_to)

        bl_result = await db.execute(bl_query.order_by(BudgetLine.sort_order, BudgetLine.account_code))
        budget_lines = bl_result.scalars().all()

        # Group plan by pnl_category
        plan_by_cat: dict[str, float] = {}
        detail_lines: dict[str, list[dict]] = {}

        for bl in budget_lines:
            cat = bl.pnl_category or "opex"
            plan_by_cat[cat] = plan_by_cat.get(cat, 0) + bl.planned_amount

            if cat not in detail_lines:
                detail_lines[cat] = []

            # Get actual for this specific budget line (only debit entries count as cost)
            ae_query = select(func.coalesce(func.sum(AccountingEntry.amount), 0)).where(
                AccountingEntry.department_id == bl.department_id,
                AccountingEntry.account_code == bl.account_code,
                AccountingEntry.entry_type == EntryType.debit,
            )
            if period:
                ae_query = ae_query.where(AccountingEntry.period == period)
            elif period_from and period_to:
                ae_query = ae_query.where(AccountingEntry.period >= period_from, AccountingEntry.period <= period_to)

            actual = float(await db.scalar(ae_query) or 0)

            detail_lines[cat].append({
                "id": bl.id,
                "account_code": bl.account_code,
                "account_name": bl.account_name,
                "department_name": bl.department.name if bl.department else None,
                "planned": bl.planned_amount,
                "actual": actual,
                "variance": bl.planned_amount - actual,
                "variance_pct": round(((bl.planned_amount - actual) / bl.planned_amount * 100) if bl.planned_amount != 0 else 0, 1),
                "status": bl.status.value,
                "created_by": bl.created_by,
                "creator_name": bl.creator.name if bl.creator and hasattr(bl.creator, 'name') else (bl.creator.email if bl.creator else None),
                "approved_by": bl.approved_by,
                "approver_name": bl.approver.name if bl.approver and hasattr(bl.approver, 'name') else (bl.approver.email if bl.approver else None),
                "plan_type": bl.plan_type.value if hasattr(bl.plan_type, 'value') else bl.plan_type,
                "scenario_id": bl.scenario_id,
                "updated_at": bl.updated_at.isoformat(),
            })

        # Add comment counts to children
        all_child_ids = []
        for cat_lines in detail_lines.values():
            for dl in cat_lines:
                all_child_ids.append(dl["id"])
        if all_child_ids:
            from common.models.budget_line_comment import BudgetLineComment
            comment_counts_result = await db.execute(
                select(
                    BudgetLineComment.budget_line_id,
                    func.count(BudgetLineComment.id)
                ).where(
                    BudgetLineComment.budget_line_id.in_(all_child_ids)
                ).group_by(BudgetLineComment.budget_line_id)
            )
            comment_counts = {row[0]: row[1] for row in comment_counts_result.all()}
            for cat_lines in detail_lines.values():
                for dl in cat_lines:
                    dl["comment_count"] = comment_counts.get(dl["id"], 0)

        # Get actual totals by category from accounting entries
        actual_by_cat: dict[str, float] = {}
        for cat in ["revenue", "cogs", "opex", "depreciation", "interest", "tax"]:
            # Match accounting entries to budget lines by account_code + department
            matching_codes_q = select(BudgetLine.account_code).where(
                BudgetLine.pnl_category == cat,
            )
            if status:
                matching_codes_q = matching_codes_q.where(BudgetLine.status == BudgetStatus(status))
            if department_id:
                matching_codes_q = matching_codes_q.where(BudgetLine.department_id == department_id)
            if plan_type:
                matching_codes_q = matching_codes_q.where(BudgetLine.plan_type == plan_type)
            if scenario_id:
                matching_codes_q = matching_codes_q.where(BudgetLine.scenario_id == scenario_id)

            matching_codes = await db.execute(matching_codes_q)
            codes = [r[0] for r in matching_codes.all()]

            if codes:
                actual_q = select(func.coalesce(func.sum(AccountingEntry.amount), 0)).where(
                    AccountingEntry.account_code.in_(codes),
                    AccountingEntry.entry_type == EntryType.debit,
                )
                if department_id:
                    actual_q = actual_q.where(AccountingEntry.department_id == department_id)
                if period:
                    actual_q = actual_q.where(AccountingEntry.period == period)
                elif period_from and period_to:
                    actual_q = actual_q.where(AccountingEntry.period >= period_from, AccountingEntry.period <= period_to)
                actual_by_cat[cat] = float(await db.scalar(actual_q) or 0)
            else:
                actual_by_cat[cat] = 0

        # Build waterfall rows
        computed: dict[str, dict] = {}
        rows = []

        for section in PNL_STRUCTURE:
            key = section["key"]

            if section["is_subtotal"]:
                # Calculate from formula
                formula = section["formula"]
                parts = formula.split(" - ")
                if len(parts) == 2:
                    a, b = parts
                    planned = computed.get(a, {}).get("planned", 0) - computed.get(b, {}).get("planned", 0)
                    actual = computed.get(a, {}).get("actual", 0) - computed.get(b, {}).get("actual", 0)
                else:
                    planned = 0
                    actual = 0

                variance = planned - actual
                variance_pct = round((variance / planned * 100) if planned != 0 else 0, 1)
                margin_of_revenue = 0
                rev_planned = computed.get("revenue", {}).get("planned", 0)
                if rev_planned > 0:
                    margin_of_revenue = round(planned / rev_planned * 100, 1)

                row = {
                    "key": key,
                    "label": section["label"],
                    "is_subtotal": True,
                    "is_editable": False,
                    "planned": planned,
                    "actual": actual,
                    "variance": variance,
                    "variance_pct": variance_pct,
                    "margin_pct": margin_of_revenue,
                    "children": [],
                }
                computed[key] = {"planned": planned, "actual": actual}
            else:
                cat = section["category"]
                planned = plan_by_cat.get(cat, 0)
                actual = actual_by_cat.get(cat, 0)
                variance = planned - actual
                variance_pct = round((variance / planned * 100) if planned != 0 else 0, 1)

                row = {
                    "key": key,
                    "label": section["label"],
                    "is_subtotal": False,
                    "is_editable": True,
                    "planned": planned,
                    "actual": actual,
                    "variance": variance,
                    "variance_pct": variance_pct,
                    "margin_pct": 0,
                    "children": detail_lines.get(cat, []),
                }
                computed[key] = {"planned": planned, "actual": actual}

            rows.append(row)

        return {
            "rows": rows,
            "structure": [{"key": s["key"], "label": s["label"], "is_subtotal": s["is_subtotal"]} for s in PNL_STRUCTURE],
        }
