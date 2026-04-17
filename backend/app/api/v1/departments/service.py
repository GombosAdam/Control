from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete as sa_delete
from app.models.department import Department
from app.models.department_budget_master import DepartmentBudgetMaster
from app.exceptions import NotFoundError, DuplicateError


class DepartmentService:
    @staticmethod
    async def list_all(db: AsyncSession) -> list[dict]:
        result = await db.execute(select(Department).order_by(Department.name))
        departments = result.scalars().all()
        return [DepartmentService._to_dict(d) for d in departments]

    @staticmethod
    async def get(db: AsyncSession, dept_id: str) -> dict:
        dept = await db.get(Department, dept_id)
        if not dept:
            raise NotFoundError("Department not found")
        return DepartmentService._to_dict(dept)

    @staticmethod
    async def create(db: AsyncSession, data: dict) -> dict:
        existing = await db.execute(select(Department).where(Department.code == data["code"]))
        if existing.scalar_one_or_none():
            raise DuplicateError(f"Department code '{data['code']}' already exists")
        dept = Department(**data)
        db.add(dept)
        await db.commit()
        await db.refresh(dept)
        return DepartmentService._to_dict(dept)

    @staticmethod
    async def update(db: AsyncSession, dept_id: str, data: dict) -> dict:
        dept = await db.get(Department, dept_id)
        if not dept:
            raise NotFoundError("Department not found")
        for key, value in data.items():
            if value is not None:
                setattr(dept, key, value)
        await db.commit()
        await db.refresh(dept)
        return DepartmentService._to_dict(dept)

    @staticmethod
    async def delete(db: AsyncSession, dept_id: str) -> dict:
        dept = await db.get(Department, dept_id)
        if not dept:
            raise NotFoundError("Department not found")
        await db.delete(dept)
        await db.commit()
        return {"message": "Department deleted"}

    # ── Department Budget Master ──

    @staticmethod
    async def get_budget_master(db: AsyncSession, dept_id: str) -> list[dict]:
        result = await db.execute(
            select(DepartmentBudgetMaster)
            .where(DepartmentBudgetMaster.department_id == dept_id)
            .order_by(DepartmentBudgetMaster.account_code)
        )
        items = result.scalars().all()
        return [{
            "id": m.id,
            "department_id": m.department_id,
            "account_code": m.account_code,
            "account_name": m.account_name,
            "is_active": m.is_active,
        } for m in items]

    @staticmethod
    async def set_budget_master(db: AsyncSession, dept_id: str, entries: list[dict]) -> list[dict]:
        """Replace the budget master entries for a department."""
        dept = await db.get(Department, dept_id)
        if not dept:
            raise NotFoundError("Department not found")

        # Delete existing entries
        await db.execute(
            sa_delete(DepartmentBudgetMaster).where(
                DepartmentBudgetMaster.department_id == dept_id
            )
        )

        # Insert new entries
        for entry in entries:
            m = DepartmentBudgetMaster(
                department_id=dept_id,
                account_code=entry["account_code"],
                account_name=entry.get("account_name", entry["account_code"]),
                is_active=entry.get("is_active", True),
            )
            db.add(m)

        await db.commit()
        return await DepartmentService.get_budget_master(db, dept_id)

    @staticmethod
    def _to_dict(dept: Department) -> dict:
        return {
            "id": dept.id,
            "name": dept.name,
            "code": dept.code,
            "parent_id": dept.parent_id,
            "manager_id": dept.manager_id,
            "manager_name": dept.manager.full_name if dept.manager else None,
            "created_at": dept.created_at.isoformat(),
            "updated_at": dept.updated_at.isoformat(),
        }
