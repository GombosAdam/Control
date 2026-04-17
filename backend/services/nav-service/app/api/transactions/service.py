import math
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.nav_transaction import NavTransaction, NavTransactionStatus
from app.models.nav_config import NavConfig
from app.api.config.service import NavConfigService
from app.exceptions import NotFoundError, ValidationError


class TransactionService:
    @staticmethod
    async def list_transactions(db: AsyncSession, page: int, limit: int,
                                 status: str | None = None) -> dict:
        query = select(NavTransaction)
        count_query = select(func.count(NavTransaction.id))

        if status:
            try:
                st = NavTransactionStatus(status)
                query = query.where(NavTransaction.status == st)
                count_query = count_query.where(NavTransaction.status == st)
            except ValueError:
                pass

        total = await db.scalar(count_query) or 0
        result = await db.execute(
            query.order_by(NavTransaction.created_at.desc())
            .offset((page - 1) * limit).limit(limit)
        )
        transactions = result.scalars().all()

        return {
            "items": [TransactionService._to_dict(t) for t in transactions],
            "total": total, "page": page, "limit": limit,
            "pages": math.ceil(total / limit) if total > 0 else 1,
        }

    @staticmethod
    async def get_transaction(db: AsyncSession, transaction_id: str) -> dict:
        result = await db.execute(
            select(NavTransaction).where(NavTransaction.id == transaction_id)
        )
        txn = result.scalar_one_or_none()
        if not txn:
            raise NotFoundError("NavTransaction", transaction_id)
        return TransactionService._to_dict(txn, include_xml=True)

    @staticmethod
    async def refresh_status(db: AsyncSession, transaction_id: str) -> dict:
        result = await db.execute(
            select(NavTransaction).where(NavTransaction.id == transaction_id)
        )
        txn = result.scalar_one_or_none()
        if not txn:
            raise NotFoundError("NavTransaction", transaction_id)

        if not txn.transaction_id:
            raise ValidationError("Transaction has no NAV transaction ID yet")

        config_result = await db.execute(
            select(NavConfig).where(NavConfig.id == txn.nav_config_id)
        )
        config = config_result.scalar_one_or_none()
        if not config:
            raise NotFoundError("NavConfig", txn.nav_config_id)

        client = NavConfigService.get_nav_client(config)
        status_result = await client.query_transaction_status(txn.transaction_id)

        processing_results = status_result.get("processingResults", [])
        if processing_results:
            first = processing_results[0]
            invoice_status = first.get("invoiceStatus")
            if invoice_status == "DONE":
                txn.status = NavTransactionStatus.done
            elif invoice_status == "ABORTED":
                txn.status = NavTransactionStatus.aborted
                msgs = first.get("businessValidationMessages", []) + first.get("technicalValidationMessages", [])
                if msgs:
                    txn.error_code = msgs[0].get("validationErrorCode")
                    txn.error_message = msgs[0].get("message")
            elif invoice_status == "PROCESSING":
                txn.status = NavTransactionStatus.processing

            txn.response_xml = str(status_result)
            await db.commit()

        return TransactionService._to_dict(txn, include_xml=True)

    @staticmethod
    def _to_dict(txn: NavTransaction, include_xml: bool = False) -> dict:
        d = {
            "id": txn.id,
            "nav_config_id": txn.nav_config_id,
            "invoice_id": txn.invoice_id,
            "transaction_id": txn.transaction_id,
            "operation": txn.operation.value,
            "status": txn.status.value,
            "error_code": txn.error_code,
            "error_message": txn.error_message,
            "invoice_number": txn.invoice_number,
            "retry_count": txn.retry_count,
            "created_at": txn.created_at.isoformat(),
            "updated_at": txn.updated_at.isoformat(),
        }
        if include_xml:
            d["request_xml"] = txn.request_xml
            d["response_xml"] = txn.response_xml
        return d
