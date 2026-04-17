from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.nav_config import NavConfig
from app.models.partner import Partner
from app.api.config.service import NavConfigService
from app.exceptions import NotFoundError


class TaxpayerService:
    @staticmethod
    async def validate_tax_number(db: AsyncSession, config_id: str, tax_number: str) -> dict:
        result = await db.execute(select(NavConfig).where(NavConfig.id == config_id))
        config = result.scalar_one_or_none()
        if not config:
            raise NotFoundError("NavConfig", config_id)

        client = NavConfigService.get_nav_client(config)
        taxpayer_info = await client.query_taxpayer(tax_number)
        return {
            "tax_number": tax_number,
            "valid": taxpayer_info.get("taxpayerValidity"),
            "name": taxpayer_info.get("taxpayerName"),
            "short_name": taxpayer_info.get("taxpayerShortName"),
            "city": taxpayer_info.get("taxpayerAddressCity"),
        }

    @staticmethod
    async def validate_partner(db: AsyncSession, config_id: str, partner_id: str) -> dict:
        result = await db.execute(select(NavConfig).where(NavConfig.id == config_id))
        config = result.scalar_one_or_none()
        if not config:
            raise NotFoundError("NavConfig", config_id)

        partner_result = await db.execute(select(Partner).where(Partner.id == partner_id))
        partner = partner_result.scalar_one_or_none()
        if not partner:
            raise NotFoundError("Partner", partner_id)
        if not partner.tax_number:
            return {
                "partner_id": partner_id,
                "partner_name": partner.name,
                "tax_number": None,
                "valid": None,
                "nav_name": None,
                "message": "Partner has no tax number",
            }

        client = NavConfigService.get_nav_client(config)
        taxpayer_info = await client.query_taxpayer(partner.tax_number)
        return {
            "partner_id": partner_id,
            "partner_name": partner.name,
            "tax_number": partner.tax_number,
            "valid": taxpayer_info.get("taxpayerValidity"),
            "nav_name": taxpayer_info.get("taxpayerName"),
            "city": taxpayer_info.get("taxpayerAddressCity"),
        }
