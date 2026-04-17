"""
Celery task for polling NAV transaction statuses.
"""

import logging
from datetime import datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.workers.celery_app import celery_app
from app.config import settings
from app.models.nav_config import NavConfig
from app.models.nav_transaction import NavTransaction, NavTransactionStatus
from app.nav_client.client import NAVOnlineSzamlaClient
from app.nav_client.mock_client import MockNAVOnlineSzamlaClient
from app.nav_client.exceptions import NAVApiError, NAVConnectionError
from app.api.config.service import _decrypt

import asyncio

logger = logging.getLogger(__name__)


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="nav_check_pending_statuses")
def nav_check_pending_statuses_task():
    """Poll NAV for pending/processing transaction statuses."""
    engine = create_engine(settings.DATABASE_URL_SYNC, pool_size=5)

    with Session(engine) as db:
        pending_txns = db.execute(
            select(NavTransaction).where(
                NavTransaction.status.in_([
                    NavTransactionStatus.sent,
                    NavTransactionStatus.processing,
                ])
            ).where(NavTransaction.transaction_id.isnot(None))
        ).scalars().all()

        if not pending_txns:
            return

        logger.info(f"Checking {len(pending_txns)} pending NAV transactions")

        # Group by config to avoid creating multiple clients
        config_cache: dict[str, NAVOnlineSzamlaClient] = {}

        for txn in pending_txns:
            try:
                if txn.nav_config_id not in config_cache:
                    config = db.execute(
                        select(NavConfig).where(NavConfig.id == txn.nav_config_id)
                    ).scalar_one_or_none()
                    if not config:
                        continue
                    import os
                    use_mock = os.environ.get("NAV_USE_MOCK", "").lower() == "true" or config.login.lower().startswith("mock")
                    if use_mock:
                        config_cache[txn.nav_config_id] = MockNAVOnlineSzamlaClient(
                            login=config.login, password="mock", signature_key="mock",
                            replacement_key="mock", tax_number=config.company_tax_number,
                            environment=config.environment.value,
                        )
                    else:
                        config_cache[txn.nav_config_id] = NAVOnlineSzamlaClient(
                            login=config.login,
                            password=_decrypt(config.password_encrypted),
                            signature_key=_decrypt(config.signature_key_encrypted),
                            replacement_key=_decrypt(config.replacement_key_encrypted),
                            tax_number=config.company_tax_number,
                            environment=config.environment.value,
                        )

                client = config_cache[txn.nav_config_id]
                result = _run_async(client.query_transaction_status(txn.transaction_id))

                processing_results = result.get("processingResults", [])
                if processing_results:
                    first = processing_results[0]
                    invoice_status = first.get("invoiceStatus")

                    if invoice_status == "DONE":
                        txn.status = NavTransactionStatus.done
                        logger.info(f"Transaction {txn.transaction_id} completed")
                    elif invoice_status == "ABORTED":
                        txn.status = NavTransactionStatus.aborted
                        msgs = first.get("businessValidationMessages", []) + first.get("technicalValidationMessages", [])
                        if msgs:
                            txn.error_code = msgs[0].get("validationErrorCode")
                            txn.error_message = msgs[0].get("message")
                        logger.warning(f"Transaction {txn.transaction_id} aborted: {txn.error_message}")
                    elif invoice_status == "PROCESSING":
                        txn.status = NavTransactionStatus.processing

                    txn.response_xml = str(result)

            except (NAVApiError, NAVConnectionError) as e:
                logger.warning(f"Error checking status for txn {txn.transaction_id}: {e}")
                continue

        db.commit()
