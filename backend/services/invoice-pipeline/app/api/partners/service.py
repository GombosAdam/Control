import math
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from common.models.partner import Partner, PartnerType
from common.models.invoice import Invoice
from common.exceptions import NotFoundError, DuplicateError

class PartnerService:
    @staticmethod
    async def list_partners(db: AsyncSession, page: int, limit: int, partner_type: str | None, search: str | None) -> dict:
        query = select(Partner)
        count_query = select(func.count(Partner.id))

        if partner_type:
            try:
                pt = PartnerType(partner_type)
                query = query.where(Partner.partner_type == pt)
                count_query = count_query.where(Partner.partner_type == pt)
            except ValueError:
                pass

        if search:
            sf = Partner.name.ilike(f"%{search}%")
            query = query.where(sf)
            count_query = count_query.where(sf)

        total = await db.scalar(count_query) or 0
        result = await db.execute(query.order_by(Partner.name).offset((page - 1) * limit).limit(limit))
        partners = result.scalars().all()

        return {
            "items": [PartnerService._to_dict(p) for p in partners],
            "total": total, "page": page, "limit": limit,
            "pages": math.ceil(total / limit) if total > 0 else 1,
        }

    @staticmethod
    async def get_partner(db: AsyncSession, partner_id: str) -> dict:
        result = await db.execute(select(Partner).where(Partner.id == partner_id))
        partner = result.scalar_one_or_none()
        if not partner:
            raise NotFoundError("Partner", partner_id)
        return PartnerService._to_dict(partner)

    @staticmethod
    async def create_partner(db: AsyncSession, data) -> dict:
        if data.tax_number:
            existing = await db.execute(select(Partner).where(Partner.tax_number == data.tax_number))
            if existing.scalar_one_or_none():
                raise DuplicateError("tax_number", data.tax_number)

        partner = Partner(
            name=data.name, tax_number=data.tax_number, bank_account=data.bank_account,
            partner_type=PartnerType(data.partner_type), address=data.address,
            contact_email=data.contact_email,
        )
        db.add(partner)
        await db.commit()
        await db.refresh(partner)
        return await PartnerService.get_partner(db, partner.id)

    @staticmethod
    async def update_partner(db: AsyncSession, partner_id: str, data) -> dict:
        result = await db.execute(select(Partner).where(Partner.id == partner_id))
        partner = result.scalar_one_or_none()
        if not partner:
            raise NotFoundError("Partner", partner_id)
        update_data = data.model_dump(exclude_unset=True)
        if "partner_type" in update_data:
            update_data["partner_type"] = PartnerType(update_data["partner_type"])
        for key, value in update_data.items():
            setattr(partner, key, value)
        await db.commit()
        return await PartnerService.get_partner(db, partner_id)

    @staticmethod
    async def delete_partner(db: AsyncSession, partner_id: str) -> None:
        result = await db.execute(select(Partner).where(Partner.id == partner_id))
        partner = result.scalar_one_or_none()
        if not partner:
            raise NotFoundError("Partner", partner_id)
        await db.delete(partner)
        await db.commit()

    @staticmethod
    def _to_dict(p: Partner) -> dict:
        return {
            "id": p.id, "name": p.name, "tax_number": p.tax_number,
            "bank_account": p.bank_account, "partner_type": p.partner_type.value,
            "address": p.address, "contact_email": p.contact_email,
            "auto_detected": p.auto_detected, "invoice_count": p.invoice_count,
            "total_amount": float(p.total_amount) if p.total_amount else 0,
            "default_accounting_code": p.default_accounting_code,
            "payment_terms_days": p.payment_terms_days,
            "payment_method": p.payment_method,
            "currency": p.currency,
            "country_code": p.country_code,
            "city": p.city,
            "zip_code": p.zip_code,
            "contact_person": p.contact_person,
            "contact_phone": p.contact_phone,
            "iban": p.iban,
            "swift_code": p.swift_code,
            "is_verified": p.is_verified,
            "notes": p.notes,
            "created_at": p.created_at.isoformat(),
            "updated_at": p.updated_at.isoformat(),
        }

    @staticmethod
    async def get_partner_invoices(db: AsyncSession, partner_id: str) -> list:
        result = await db.execute(
            select(Invoice).where(Invoice.partner_id == partner_id).order_by(Invoice.created_at.desc())
        )
        return [
            {
                "id": inv.id, "invoice_number": inv.invoice_number,
                "status": inv.status.value, "gross_amount": inv.gross_amount,
                "currency": inv.currency, "created_at": inv.created_at.isoformat(),
            }
            for inv in result.scalars().all()
        ]
