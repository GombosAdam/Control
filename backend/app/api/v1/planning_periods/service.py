from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.planning_period import PlanningPeriod
from app.models.budget_line import BudgetLine, BudgetStatus
from app.models.audit import AuditLog
from app.exceptions import NotFoundError, ValidationError


class PlanningPeriodService:
    @staticmethod
    async def list_periods(db: AsyncSession, scenario_id: str | None = None,
                           plan_type: str | None = None) -> list[dict]:
        query = select(PlanningPeriod)
        if scenario_id:
            query = query.where(PlanningPeriod.scenario_id == scenario_id)
        if plan_type:
            query = query.where(PlanningPeriod.plan_type == plan_type)
        query = query.order_by(PlanningPeriod.year.desc(), PlanningPeriod.created_at.desc())
        result = await db.execute(query)
        periods = result.scalars().all()
        return [PlanningPeriodService._to_dict(p) for p in periods]

    @staticmethod
    async def get_period(db: AsyncSession, period_id: str) -> dict:
        period = await db.get(PlanningPeriod, period_id)
        if not period:
            raise NotFoundError("Planning period not found")
        return PlanningPeriodService._to_dict(period)

    @staticmethod
    async def create_period(db: AsyncSession, data: dict, user_id: str) -> dict:
        source_period_id = data.pop("source_period_id", None)
        adjustment_pct = data.pop("adjustment_pct", 0.0)
        department_id = data.pop("department_id", None)

        period = PlanningPeriod(**data, created_by=user_id)
        db.add(period)
        await db.flush()

        created = 0

        if source_period_id:
            # Copy lines from source planning period
            source = await db.get(PlanningPeriod, source_period_id)
            if not source:
                raise ValidationError("Source planning period not found")

            query = select(BudgetLine).where(
                BudgetLine.planning_period_id == source_period_id
            )
            if department_id:
                query = query.where(BudgetLine.department_id == department_id)
            result = await db.execute(query)
            source_lines = result.scalars().all()

            for sl in source_lines:
                src_month = int(sl.period.split("-")[1])
                if src_month < period.start_month or src_month > period.end_month:
                    continue
                new_period_str = f"{period.year}-{src_month:02d}"
                new_line = BudgetLine(
                    department_id=sl.department_id,
                    account_code=sl.account_code,
                    account_name=sl.account_name,
                    period=new_period_str,
                    planned_amount=round(sl.planned_amount * (1 + adjustment_pct / 100), 2),
                    currency=sl.currency,
                    pnl_category=sl.pnl_category,
                    sort_order=sl.sort_order,
                    plan_type=period.plan_type,
                    scenario_id=period.scenario_id or sl.scenario_id,
                    planning_period_id=period.id,
                    created_by=user_id,
                )
                db.add(new_line)
                created += 1
        else:
            # Create placeholder lines for each month x 6 categories
            categories = [
                ("revenue", "REV-001", "Bevétel", 0),
                ("cogs", "COGS-001", "Közvetlen költség", 10),
                ("opex", "OPEX-001", "Működési költség", 20),
                ("depreciation", "DEP-001", "Értékcsökkenés", 30),
                ("interest", "INT-001", "Kamatköltség", 40),
                ("tax", "TAX-001", "Adó", 50),
            ]

            dept = department_id
            if not dept:
                from app.models.department import Department
                dept_result = await db.scalar(select(Department.id).limit(1))
                dept = dept_result or "unknown"

            for m in range(period.start_month, period.end_month + 1):
                period_str = f"{period.year}-{m:02d}"
                for cat, code, name, sort in categories:
                    new_line = BudgetLine(
                        department_id=dept,
                        account_code=code,
                        account_name=name,
                        period=period_str,
                        planned_amount=0,
                        pnl_category=cat,
                        sort_order=sort,
                        plan_type=period.plan_type,
                        scenario_id=period.scenario_id,
                        planning_period_id=period.id,
                        created_by=user_id,
                    )
                    db.add(new_line)
                    created += 1

        await db.flush()

        log = AuditLog(
            user_id=user_id,
            action="planning_period.create",
            entity_type="planning_period",
            entity_id=period.id,
            details={
                "name": period.name,
                "year": period.year,
                "start_month": period.start_month,
                "end_month": period.end_month,
                "lines_created": created,
                "source_period_id": source_period_id,
            },
        )
        db.add(log)
        await db.commit()
        await db.refresh(period)

        result_dict = PlanningPeriodService._to_dict(period)
        result_dict["lines_created"] = created
        return result_dict

    @staticmethod
    async def delete_period(db: AsyncSession, period_id: str, user_id: str) -> dict:
        period = await db.get(PlanningPeriod, period_id)
        if not period:
            raise NotFoundError("Planning period not found")

        non_draft = await db.scalar(
            select(func.count(BudgetLine.id)).where(
                BudgetLine.planning_period_id == period_id,
                BudgetLine.status.in_([BudgetStatus.approved, BudgetStatus.locked]),
            )
        ) or 0
        if non_draft > 0:
            raise ValidationError(
                f"Cannot delete: {non_draft} approved/locked budget lines exist in this period"
            )

        draft_lines = await db.execute(
            select(BudgetLine).where(
                BudgetLine.planning_period_id == period_id,
                BudgetLine.status == BudgetStatus.draft,
            )
        )
        deleted = 0
        for line in draft_lines.scalars().all():
            await db.delete(line)
            deleted += 1

        log = AuditLog(
            user_id=user_id,
            action="planning_period.delete",
            entity_type="planning_period",
            entity_id=period_id,
            details={"name": period.name, "lines_deleted": deleted},
        )
        db.add(log)

        await db.delete(period)
        await db.commit()
        return {"deleted": True, "lines_deleted": deleted}

    @staticmethod
    def _to_dict(period: PlanningPeriod) -> dict:
        return {
            "id": period.id,
            "name": period.name,
            "year": period.year,
            "start_month": period.start_month,
            "end_month": period.end_month,
            "plan_type": period.plan_type,
            "scenario_id": period.scenario_id,
            "scenario_name": period.scenario.name if period.scenario else None,
            "created_by": period.created_by,
            "creator_name": period.creator.name if period.creator and hasattr(period.creator, 'name') else (period.creator.email if period.creator else None),
            "created_at": period.created_at.isoformat(),
        }
