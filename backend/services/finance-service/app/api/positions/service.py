from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from common.models.position import Position
from common.models.user import User
from common.exceptions import NotFoundError, DuplicateError


class PositionService:
    @staticmethod
    async def list_all(db: AsyncSession) -> list[dict]:
        result = await db.execute(select(Position).order_by(Position.name))
        positions = result.scalars().all()
        items = []
        for p in positions:
            d = PositionService._to_dict(p)
            # Find holder
            holder_result = await db.execute(
                select(User).where(User.position_id == p.id, User.is_active == True).limit(1)
            )
            holder = holder_result.scalar_one_or_none()
            d["holder_id"] = holder.id if holder else None
            d["holder_name"] = holder.full_name if holder else None
            items.append(d)
        return items

    @staticmethod
    async def get(db: AsyncSession, position_id: str) -> dict:
        pos = await db.get(Position, position_id)
        if not pos:
            raise NotFoundError("Position not found")
        return PositionService._to_dict(pos)

    @staticmethod
    async def create(db: AsyncSession, data: dict) -> dict:
        pos = Position(**data)
        db.add(pos)
        await db.commit()
        await db.refresh(pos)
        return PositionService._to_dict(pos)

    @staticmethod
    async def update(db: AsyncSession, position_id: str, data: dict) -> dict:
        pos = await db.get(Position, position_id)
        if not pos:
            raise NotFoundError("Position not found")
        for key, value in data.items():
            if value is not None:
                setattr(pos, key, value)
        await db.commit()
        await db.refresh(pos)
        return PositionService._to_dict(pos)

    @staticmethod
    async def delete(db: AsyncSession, position_id: str) -> dict:
        pos = await db.get(Position, position_id)
        if not pos:
            raise NotFoundError("Position not found")
        await db.delete(pos)
        await db.commit()
        return {"message": "Position deleted"}

    @staticmethod
    def _to_dict(pos: Position) -> dict:
        return {
            "id": pos.id,
            "name": pos.name,
            "department_id": pos.department_id,
            "department_name": pos.department.name if pos.department else None,
            "reports_to_id": pos.reports_to_id,
            "reports_to_name": pos.reports_to.name if pos.reports_to else None,
            "created_at": pos.created_at.isoformat(),
            "updated_at": pos.updated_at.isoformat(),
        }
