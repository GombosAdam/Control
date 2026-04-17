import math
from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.nav_config import NavConfig, NavEnvironment
from app.nav_client.client import NAVOnlineSzamlaClient
from app.nav_client.mock_client import MockNAVOnlineSzamlaClient
from app.nav_client.exceptions import NAVApiError, NAVConnectionError

from app.exceptions import NotFoundError, DuplicateError, ValidationError

USE_MOCK_ENV_KEY = "NAV_USE_MOCK"


def _get_fernet() -> Fernet:
    from app.config import settings
    key = settings.NAV_ENCRYPTION_KEY
    if not key:
        raise ValidationError("NAV_ENCRYPTION_KEY not configured")
    return Fernet(key.encode() if isinstance(key, str) else key)


def _encrypt(value: str) -> str:
    return _get_fernet().encrypt(value.encode()).decode()


def _decrypt(value: str) -> str:
    return _get_fernet().decrypt(value.encode()).decode()


class NavConfigService:
    @staticmethod
    async def list_configs(db: AsyncSession, page: int, limit: int) -> dict:
        count_query = select(func.count(NavConfig.id))
        total = await db.scalar(count_query) or 0

        result = await db.execute(
            select(NavConfig).order_by(NavConfig.created_at.desc())
            .offset((page - 1) * limit).limit(limit)
        )
        configs = result.scalars().all()

        return {
            "items": [
                {
                    "id": c.id,
                    "company_tax_number": c.company_tax_number,
                    "company_name": c.company_name,
                    "login": c.login,
                    "environment": c.environment.value,
                    "is_active": c.is_active,
                    "last_sync_at": c.last_sync_at.isoformat() if c.last_sync_at else None,
                    "created_at": c.created_at.isoformat(),
                    "updated_at": c.updated_at.isoformat(),
                }
                for c in configs
            ],
            "total": total, "page": page, "limit": limit,
            "pages": math.ceil(total / limit) if total > 0 else 1,
        }

    @staticmethod
    async def create_config(db: AsyncSession, data) -> dict:
        existing = await db.execute(
            select(NavConfig).where(NavConfig.company_tax_number == data.company_tax_number)
        )
        if existing.scalar_one_or_none():
            raise DuplicateError("company_tax_number", data.company_tax_number)

        config = NavConfig(
            company_tax_number=data.company_tax_number,
            company_name=data.company_name,
            login=data.login,
            password_encrypted=_encrypt(data.password),
            signature_key_encrypted=_encrypt(data.signature_key),
            replacement_key_encrypted=_encrypt(data.replacement_key),
            environment=NavEnvironment(data.environment),
        )
        db.add(config)
        await db.commit()
        await db.refresh(config)
        return await NavConfigService.get_config(db, config.id)

    @staticmethod
    async def get_config(db: AsyncSession, config_id: str) -> dict:
        result = await db.execute(select(NavConfig).where(NavConfig.id == config_id))
        config = result.scalar_one_or_none()
        if not config:
            raise NotFoundError("NavConfig", config_id)
        return {
            "id": config.id,
            "company_tax_number": config.company_tax_number,
            "company_name": config.company_name,
            "login": config.login,
            "environment": config.environment.value,
            "is_active": config.is_active,
            "last_sync_at": config.last_sync_at.isoformat() if config.last_sync_at else None,
            "created_at": config.created_at.isoformat(),
            "updated_at": config.updated_at.isoformat(),
        }

    @staticmethod
    async def update_config(db: AsyncSession, config_id: str, data) -> dict:
        result = await db.execute(select(NavConfig).where(NavConfig.id == config_id))
        config = result.scalar_one_or_none()
        if not config:
            raise NotFoundError("NavConfig", config_id)

        update_data = data.model_dump(exclude_unset=True)
        if "password" in update_data:
            config.password_encrypted = _encrypt(update_data.pop("password"))
        if "signature_key" in update_data:
            config.signature_key_encrypted = _encrypt(update_data.pop("signature_key"))
        if "replacement_key" in update_data:
            config.replacement_key_encrypted = _encrypt(update_data.pop("replacement_key"))
        if "environment" in update_data:
            update_data["environment"] = NavEnvironment(update_data["environment"])

        for key, value in update_data.items():
            setattr(config, key, value)
        await db.commit()
        return await NavConfigService.get_config(db, config_id)

    @staticmethod
    async def delete_config(db: AsyncSession, config_id: str) -> None:
        result = await db.execute(select(NavConfig).where(NavConfig.id == config_id))
        config = result.scalar_one_or_none()
        if not config:
            raise NotFoundError("NavConfig", config_id)
        await db.delete(config)
        await db.commit()

    @staticmethod
    async def test_connection(db: AsyncSession, config_id: str) -> dict:
        result = await db.execute(select(NavConfig).where(NavConfig.id == config_id))
        config = result.scalar_one_or_none()
        if not config:
            raise NotFoundError("NavConfig", config_id)

        try:
            client = NavConfigService.get_nav_client(config)
            taxpayer = await client.query_taxpayer(config.company_tax_number)
            return {
                "success": True,
                "taxpayer_name": taxpayer.get("taxpayerName"),
                "taxpayer_valid": taxpayer.get("taxpayerValidity"),
            }
        except (NAVApiError, NAVConnectionError) as e:
            return {
                "success": False,
                "error": str(e),
            }

    @staticmethod
    def _should_use_mock(config: NavConfig) -> bool:
        """Use mock client if NAV_USE_MOCK=true or environment is test with mock credentials."""
        import os
        if os.environ.get(USE_MOCK_ENV_KEY, "").lower() == "true":
            return True
        # Auto-detect: if login starts with "mock" or "test", use mock
        if config.login.lower().startswith("mock"):
            return True
        return False

    @staticmethod
    def get_nav_client(config: NavConfig):
        """Create a NAV client from a NavConfig model instance."""
        if NavConfigService._should_use_mock(config):
            return MockNAVOnlineSzamlaClient(
                login=config.login,
                password="mock",
                signature_key="mock",
                replacement_key="mock",
                tax_number=config.company_tax_number,
                environment=config.environment.value,
            )
        return NAVOnlineSzamlaClient(
            login=config.login,
            password=_decrypt(config.password_encrypted),
            signature_key=_decrypt(config.signature_key_encrypted),
            replacement_key=_decrypt(config.replacement_key_encrypted),
            tax_number=config.company_tax_number,
            environment=config.environment.value,
        )
