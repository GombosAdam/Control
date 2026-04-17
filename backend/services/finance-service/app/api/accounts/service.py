from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from common.models.account_master import AccountMaster, AccountType
from common.exceptions import NotFoundError, DuplicateError


class AccountService:
    @staticmethod
    async def list_all(
        db: AsyncSession,
        account_type: str | None = None,
        active: bool | None = None,
        pnl_category: str | None = None,
    ) -> list[dict]:
        q = select(AccountMaster).order_by(AccountMaster.sort_order, AccountMaster.code)
        if account_type:
            q = q.where(AccountMaster.account_type == AccountType(account_type))
        if active is not None:
            q = q.where(AccountMaster.is_active == active)
        if pnl_category:
            q = q.where(AccountMaster.pnl_category == pnl_category)
        result = await db.execute(q)
        return [AccountService._to_dict(a) for a in result.scalars().all()]

    @staticmethod
    async def get_tree(db: AsyncSession) -> list[dict]:
        result = await db.execute(
            select(AccountMaster)
            .where(AccountMaster.is_active == True)
            .order_by(AccountMaster.sort_order, AccountMaster.code)
        )
        accounts = result.scalars().all()

        by_parent: dict[str | None, list] = {}
        account_map: dict[str, AccountMaster] = {}
        for a in accounts:
            account_map[a.code] = a
            by_parent.setdefault(a.parent_code, []).append(a)

        def build_node(acc: AccountMaster) -> dict:
            node = AccountService._to_dict(acc)
            children = by_parent.get(acc.code, [])
            if children:
                node["children"] = [build_node(c) for c in children]
            return node

        roots = by_parent.get(None, [])
        return [build_node(r) for r in roots]

    @staticmethod
    async def get(db: AsyncSession, code: str) -> dict:
        account = await db.get(AccountMaster, code)
        if not account:
            raise NotFoundError("Account not found")
        result = AccountService._to_dict(account)
        # Include children
        children_q = await db.execute(
            select(AccountMaster)
            .where(AccountMaster.parent_code == code)
            .order_by(AccountMaster.sort_order, AccountMaster.code)
        )
        result["children"] = [
            AccountService._to_dict(c) for c in children_q.scalars().all()
        ]
        return result

    @staticmethod
    async def create(db: AsyncSession, data: dict) -> dict:
        existing = await db.get(AccountMaster, data["code"])
        if existing:
            raise DuplicateError(f"Account code '{data['code']}' already exists")
        account = AccountMaster(**data)
        db.add(account)
        await db.commit()
        await db.refresh(account)
        return AccountService._to_dict(account)

    @staticmethod
    async def update(db: AsyncSession, code: str, data: dict) -> dict:
        account = await db.get(AccountMaster, code)
        if not account:
            raise NotFoundError("Account not found")
        for key, value in data.items():
            if value is not None:
                setattr(account, key, value)
        await db.commit()
        await db.refresh(account)
        return AccountService._to_dict(account)

    @staticmethod
    def _to_dict(acc: AccountMaster) -> dict:
        return {
            "code": acc.code,
            "name": acc.name,
            "name_en": acc.name_en,
            "account_type": acc.account_type.value if acc.account_type else None,
            "pnl_category": acc.pnl_category,
            "parent_code": acc.parent_code,
            "sort_order": acc.sort_order,
            "is_active": acc.is_active,
            "is_header": acc.is_header,
            "normal_side": acc.normal_side,
            "created_at": acc.created_at.isoformat() if acc.created_at else None,
            "updated_at": acc.updated_at.isoformat() if acc.updated_at else None,
        }
