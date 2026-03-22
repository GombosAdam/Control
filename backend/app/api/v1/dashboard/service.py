from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.invoice import Invoice, InvoiceStatus
from app.models.budget_line import BudgetLine, BudgetStatus, PlanType
from app.models.accounting_entry import AccountingEntry
from app.models.department import Department

class DashboardService:
    @staticmethod
    async def get_stats(db: AsyncSession) -> dict:
        total = await db.scalar(select(func.count(Invoice.id)))
        post_approval_statuses = [InvoiceStatus.awaiting_match, InvoiceStatus.matched, InvoiceStatus.posted]
        approved = await db.scalar(select(func.count(Invoice.id)).where(Invoice.status.in_(post_approval_statuses)))
        pending = await db.scalar(select(func.count(Invoice.id)).where(Invoice.status == InvoiceStatus.pending_review))
        error = await db.scalar(select(func.count(Invoice.id)).where(Invoice.status == InvoiceStatus.error))
        total_amount = await db.scalar(select(func.coalesce(func.sum(Invoice.gross_amount), 0)).where(Invoice.status.in_(post_approval_statuses)))

        return {
            "total_invoices": total or 0,
            "approved": approved or 0,
            "pending_review": pending or 0,
            "errors": error or 0,
            "total_amount": float(total_amount or 0),
        }

    @staticmethod
    async def get_recent_invoices(db: AsyncSession, limit: int = 10) -> list:
        result = await db.execute(
            select(Invoice).order_by(Invoice.created_at.desc()).limit(limit)
        )
        invoices = result.scalars().all()
        return [
            {
                "id": inv.id,
                "invoice_number": inv.invoice_number,
                "status": inv.status.value,
                "gross_amount": inv.gross_amount,
                "currency": inv.currency,
                "original_filename": inv.original_filename,
                "created_at": inv.created_at.isoformat(),
            }
            for inv in invoices
        ]

    @staticmethod
    async def get_processing_status(db: AsyncSession) -> dict:
        statuses = {}
        for status in InvoiceStatus:
            count = await db.scalar(select(func.count(Invoice.id)).where(Invoice.status == status))
            statuses[status.value] = count or 0
        return statuses

    @staticmethod
    async def get_cfo_kpis(db: AsyncSession, scenario_id: str | None, plan_type: str | None) -> dict:
        from datetime import datetime
        now = datetime.utcnow()
        current_period = f"{now.year}-{now.month:02d}"
        prev_month = now.month - 1 if now.month > 1 else 12
        prev_year = now.year if now.month > 1 else now.year - 1
        previous_period = f"{prev_year}-{prev_month:02d}"

        async def get_kpi(category: str, period: str) -> dict:
            bl_query = select(func.coalesce(func.sum(BudgetLine.planned_amount), 0)).where(
                BudgetLine.pnl_category == category
            )
            if plan_type:
                bl_query = bl_query.where(BudgetLine.plan_type == plan_type)
            if scenario_id:
                bl_query = bl_query.where(BudgetLine.scenario_id == scenario_id)
            bl_query = bl_query.where(BudgetLine.period == period)
            planned = float(await db.scalar(bl_query) or 0)
            return planned

        revenue_current = await get_kpi("revenue", current_period)
        revenue_previous = await get_kpi("revenue", previous_period)

        # For EBITDA and net income, compute from categories
        async def get_composite(period: str) -> dict:
            vals = {}
            for cat in ["revenue", "cogs", "opex", "depreciation", "interest", "tax"]:
                vals[cat] = await get_kpi(cat, period)
            gross = vals["revenue"] - vals["cogs"]
            ebitda = gross - vals["opex"]
            ebit = ebitda - vals["depreciation"]
            pbt = ebit - vals["interest"]
            net = pbt - vals["tax"]
            return {"revenue": vals["revenue"], "ebitda": ebitda, "net_income": net}

        current = await get_composite(current_period)
        previous = await get_composite(previous_period)

        def trend(curr: float, prev: float) -> float:
            if prev == 0:
                return 0
            return round((curr - prev) / abs(prev) * 100, 1)

        return {
            "revenue": {"current": current["revenue"], "previous": previous["revenue"], "trend_pct": trend(current["revenue"], previous["revenue"])},
            "ebitda": {"current": current["ebitda"], "previous": previous["ebitda"], "trend_pct": trend(current["ebitda"], previous["ebitda"])},
            "net_income": {"current": current["net_income"], "previous": previous["net_income"], "trend_pct": trend(current["net_income"], previous["net_income"])},
            "current_period": current_period,
        }

    @staticmethod
    async def get_trend_data(db: AsyncSession, scenario_id: str | None, plan_type: str | None, periods: int = 12) -> list[dict]:
        # Get last N periods
        period_query = select(BudgetLine.period).distinct().order_by(BudgetLine.period.desc())
        if scenario_id:
            period_query = period_query.where(BudgetLine.scenario_id == scenario_id)
        if plan_type:
            period_query = period_query.where(BudgetLine.plan_type == plan_type)
        result = await db.execute(period_query.limit(periods))
        available_periods = sorted([r[0] for r in result.all()])

        trend = []
        for period in available_periods:
            bl_filter = [BudgetLine.period == period]
            if scenario_id:
                bl_filter.append(BudgetLine.scenario_id == scenario_id)
            if plan_type:
                bl_filter.append(BudgetLine.plan_type == plan_type)

            rev_plan = float(await db.scalar(
                select(func.coalesce(func.sum(BudgetLine.planned_amount), 0)).where(
                    BudgetLine.pnl_category == "revenue", *bl_filter
                )
            ) or 0)

            cost_plan = float(await db.scalar(
                select(func.coalesce(func.sum(BudgetLine.planned_amount), 0)).where(
                    BudgetLine.pnl_category.in_(["cogs", "opex"]), *bl_filter
                )
            ) or 0)

            ebitda_plan = rev_plan - cost_plan

            # Actual from accounting entries
            rev_actual = float(await db.scalar(
                select(func.coalesce(func.sum(AccountingEntry.amount), 0)).where(
                    AccountingEntry.period == period,
                    AccountingEntry.account_code.in_(
                        select(BudgetLine.account_code).where(BudgetLine.pnl_category == "revenue", *bl_filter)
                    )
                )
            ) or 0)

            cost_actual = float(await db.scalar(
                select(func.coalesce(func.sum(AccountingEntry.amount), 0)).where(
                    AccountingEntry.period == period,
                    AccountingEntry.account_code.in_(
                        select(BudgetLine.account_code).where(BudgetLine.pnl_category.in_(["cogs", "opex"]), *bl_filter)
                    )
                )
            ) or 0)

            ebitda_actual = rev_actual - cost_actual

            trend.append({
                "period": period,
                "revenue_plan": rev_plan,
                "revenue_actual": rev_actual,
                "ebitda_plan": ebitda_plan,
                "ebitda_actual": ebitda_actual,
            })

        return trend

    @staticmethod
    async def get_department_comparison(db: AsyncSession, period: str | None,
                                        scenario_id: str | None, plan_type: str | None) -> list[dict]:
        result = await db.execute(select(Department).order_by(Department.name))
        departments = result.scalars().all()

        items = []
        for dept in departments:
            bl_filter = [BudgetLine.department_id == dept.id]
            if scenario_id:
                bl_filter.append(BudgetLine.scenario_id == scenario_id)
            if plan_type:
                bl_filter.append(BudgetLine.plan_type == plan_type)
            if period:
                bl_filter.append(BudgetLine.period == period)

            planned = float(await db.scalar(
                select(func.coalesce(func.sum(BudgetLine.planned_amount), 0)).where(*bl_filter)
            ) or 0)

            ae_filter = [AccountingEntry.department_id == dept.id]
            if period:
                ae_filter.append(AccountingEntry.period == period)

            actual = float(await db.scalar(
                select(func.coalesce(func.sum(AccountingEntry.amount), 0)).where(*ae_filter)
            ) or 0)

            variance = planned - actual
            variance_pct = round((variance / planned * 100) if planned != 0 else 0, 1)

            items.append({
                "department_name": dept.name,
                "planned": planned,
                "actual": actual,
                "variance": variance,
                "variance_pct": variance_pct,
            })
        return items

    @staticmethod
    async def get_budget_alerts(db: AsyncSession, threshold_pct: float = 10,
                                scenario_id: str | None = None, plan_type: str | None = None) -> list[dict]:
        bl_query = select(BudgetLine)
        if scenario_id:
            bl_query = bl_query.where(BudgetLine.scenario_id == scenario_id)
        if plan_type:
            bl_query = bl_query.where(BudgetLine.plan_type == plan_type)

        result = await db.execute(bl_query)
        lines = result.scalars().all()

        alerts = []
        for line in lines:
            actual = float(await db.scalar(
                select(func.coalesce(func.sum(AccountingEntry.amount), 0)).where(
                    AccountingEntry.department_id == line.department_id,
                    AccountingEntry.account_code == line.account_code,
                    AccountingEntry.period == line.period,
                )
            ) or 0)

            if line.planned_amount > 0 and actual > line.planned_amount:
                overage = actual - line.planned_amount
                overage_pct = round(overage / line.planned_amount * 100, 1)
                if overage_pct >= threshold_pct:
                    alerts.append({
                        "account_name": line.account_name,
                        "department_name": line.department.name if line.department else None,
                        "period": line.period,
                        "planned": line.planned_amount,
                        "actual": actual,
                        "overage_pct": overage_pct,
                    })

        alerts.sort(key=lambda a: a["overage_pct"], reverse=True)
        return alerts[:20]
