from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.nav_config import NavConfig
from app.models.nav_transaction import NavTransaction, NavOperation, NavTransactionStatus
from app.models.invoice import Invoice
from app.exceptions import NotFoundError, ValidationError


class SubmitService:
    @staticmethod
    async def submit_invoice(db: AsyncSession, invoice_id: str, config_id: str) -> dict:
        config_result = await db.execute(select(NavConfig).where(NavConfig.id == config_id))
        config = config_result.scalar_one_or_none()
        if not config:
            raise NotFoundError("NavConfig", config_id)

        invoice_result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
        invoice = invoice_result.scalar_one_or_none()
        if not invoice:
            raise NotFoundError("Invoice", invoice_id)

        if invoice.status.value not in ("approved", "posted"):
            raise ValidationError(f"Invoice must be approved to submit, current status: {invoice.status.value}")

        transaction = NavTransaction(
            nav_config_id=config_id,
            invoice_id=invoice_id,
            operation=NavOperation.CREATE,
            status=NavTransactionStatus.pending,
            invoice_number=invoice.invoice_number,
        )
        db.add(transaction)
        await db.commit()
        await db.refresh(transaction)

        # Dispatch Celery task
        from app.workers.celery_app import celery_app
        celery_app.send_task(
            "nav_submit_outbound",
            args=[transaction.id],
            queue="nav",
        )

        return {
            "transaction_id": transaction.id,
            "status": transaction.status.value,
            "message": "Submission queued",
        }

    @staticmethod
    async def submit_batch(db: AsyncSession, invoice_ids: list[str], config_id: str) -> dict:
        results = []
        for invoice_id in invoice_ids:
            try:
                result = await SubmitService.submit_invoice(db, invoice_id, config_id)
                results.append(result)
            except Exception as e:
                results.append({
                    "invoice_id": invoice_id,
                    "status": "error",
                    "message": str(e),
                })
        return {
            "submitted": len([r for r in results if r.get("status") != "error"]),
            "errors": len([r for r in results if r.get("status") == "error"]),
            "results": results,
        }
