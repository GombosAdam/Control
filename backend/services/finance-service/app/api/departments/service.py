from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from common.models.department import Department
from common.exceptions import NotFoundError, DuplicateError


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
