import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from common.models.scenario import Scenario
from common.models.budget_line import BudgetLine, BudgetStatus
from common.models.audit import AuditLog
from common.exceptions import NotFoundError, ValidationError


class ScenarioService:
    @staticmethod
    async def list_scenarios(db: AsyncSession) -> list[dict]:
        result = await db.execute(select(Scenario).order_by(Scenario.created_at))
        scenarios = result.scalars().all()
        return [ScenarioService._to_dict(s) for s in scenarios]

    @staticmethod
    async def create_scenario(db: AsyncSession, name: str, description: str | None, user_id: str) -> dict:
        scenario = Scenario(name=name, description=description, created_by=user_id)
        db.add(scenario)
        await db.commit()
        await db.refresh(scenario)
        return ScenarioService._to_dict(scenario)

    @staticmethod
    async def copy_scenario(db: AsyncSession, source_scenario_id: str, name: str,
                            description: str | None, adjustment_pct: float,
                            period: str | None, department_id: str | None,
                            user_id: str) -> dict:
        source = await db.get(Scenario, source_scenario_id)
        if not source:
            raise NotFoundError("Scenario", source_scenario_id)

        new_scenario = Scenario(name=name, description=description, created_by=user_id)
        db.add(new_scenario)
        await db.flush()

        query = select(BudgetLine).where(BudgetLine.scenario_id == source_scenario_id)
        if period:
            query = query.where(BudgetLine.period == period)
        if department_id:
            query = query.where(BudgetLine.department_id == department_id)

        result = await db.execute(query)
        source_lines = result.scalars().all()

        created = 0
        for sl in source_lines:
            new_line = BudgetLine(
                department_id=sl.department_id,
                account_code=sl.account_code,
                account_name=sl.account_name,
                period=sl.period,
                planned_amount=round(sl.planned_amount * (1 + adjustment_pct / 100), 2),
                currency=sl.currency,
                pnl_category=sl.pnl_category,
                sort_order=sl.sort_order,
                plan_type=sl.plan_type,
                scenario_id=new_scenario.id,
                created_by=user_id,
            )
            db.add(new_line)
            created += 1

        await db.commit()
        await db.refresh(new_scenario)
        return {**ScenarioService._to_dict(new_scenario), "lines_created": created}

    @staticmethod
    async def delete_scenario(db: AsyncSession, scenario_id: str) -> dict:
        scenario = await db.get(Scenario, scenario_id)
        if not scenario:
            raise NotFoundError("Scenario", scenario_id)
        if scenario.is_default:
            raise ValidationError("Cannot delete the default scenario")

        # Delete associated budget lines
        result = await db.execute(select(BudgetLine).where(BudgetLine.scenario_id == scenario_id))
        lines = result.scalars().all()
        for line in lines:
            await db.delete(line)

        await db.delete(scenario)
        await db.commit()
        return {"deleted": scenario_id, "lines_removed": len(lines)}

    @staticmethod
    def _to_dict(scenario: Scenario) -> dict:
        return {
            "id": scenario.id,
            "name": scenario.name,
            "description": scenario.description,
            "is_default": scenario.is_default,
            "created_by": scenario.created_by,
            "creator_name": scenario.creator.name if scenario.creator and hasattr(scenario.creator, 'name') else (scenario.creator.email if scenario.creator else None),
            "created_at": scenario.created_at.isoformat(),
        }
