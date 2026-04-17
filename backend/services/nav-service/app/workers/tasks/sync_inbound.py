"""
Celery tasks for inbound invoice sync from NAV.
"""

import logging
from datetime import datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.workers.celery_app import celery_app
from app.config import settings
from app.models.nav_config import NavConfig
from app.models.nav_sync_log import NavSyncLog, NavSyncStatus
from app.models.invoice import Invoice, InvoiceLine, InvoiceStatus
from app.models.partner import Partner, PartnerType
from app.nav_client.client import NAVOnlineSzamlaClient
from app.nav_client.mock_client import MockNAVOnlineSzamlaClient
from app.nav_client.exceptions import NAVApiError, NAVConnectionError
from app.api.config.service import _decrypt

import asyncio

logger = logging.getLogger(__name__)


def _get_sync_engine():
    return create_engine(settings.DATABASE_URL_SYNC, pool_size=5)


def _run_async(coro):
    """Run an async coroutine in a sync context."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="nav_sync_inbound", bind=True, max_retries=2)
def nav_sync_inbound_task(self, sync_log_id: str, config_id: str,
                           date_from: str, date_to: str):
    """Sync inbound invoices from NAV for a given date range."""
    engine = _get_sync_engine()

    with Session(engine) as db:
        sync_log = db.execute(
            select(NavSyncLog).where(NavSyncLog.id == sync_log_id)
        ).scalar_one_or_none()
        if not sync_log:
            logger.error(f"SyncLog not found: {sync_log_id}")
            return

        config = db.execute(
            select(NavConfig).where(NavConfig.id == config_id)
        ).scalar_one_or_none()
        if not config:
            sync_log.status = NavSyncStatus.error
            sync_log.error_message = f"Config not found: {config_id}"
            sync_log.completed_at = datetime.utcnow()
            db.commit()
            return

        try:
            import os
            use_mock = os.environ.get("NAV_USE_MOCK", "").lower() == "true" or config.login.lower().startswith("mock")
            if use_mock:
                client = MockNAVOnlineSzamlaClient(
                    login=config.login, password="mock", signature_key="mock",
                    replacement_key="mock", tax_number=config.company_tax_number,
                    environment=config.environment.value,
                )
            else:
                client = NAVOnlineSzamlaClient(
                    login=config.login,
                    password=_decrypt(config.password_encrypted),
                    signature_key=_decrypt(config.signature_key_encrypted),
                    replacement_key=_decrypt(config.replacement_key_encrypted),
                    tax_number=config.company_tax_number,
                    environment=config.environment.value,
                )

            invoices_found = 0
            invoices_created = 0
            invoices_skipped = 0
            page = 1

            while True:
                digest_result = _run_async(
                    client.query_invoice_digest(date_from, date_to, page=page)
                )
                digests = digest_result.get("invoiceDigests", [])
                available_page = digest_result.get("availablePage", 1)

                for digest in digests:
                    invoices_found += 1
                    inv_number = digest.get("invoiceNumber")

                    # Skip if already exists
                    existing = db.execute(
                        select(Invoice).where(Invoice.invoice_number == inv_number)
                    ).scalar_one_or_none()
                    if existing:
                        invoices_skipped += 1
                        continue

                    # Get full invoice data
                    try:
                        invoice_data = _run_async(
                            client.query_invoice_data(
                                inv_number,
                                supplier_tax_number=digest.get("supplierTaxNumber"),
                            )
                        )
                    except NAVApiError as e:
                        logger.warning(f"Failed to get invoice data for {inv_number}: {e}")
                        invoices_skipped += 1
                        continue

                    parsed = invoice_data.get("parsedInvoice")
                    if not parsed:
                        invoices_skipped += 1
                        continue

                    # Find or create partner
                    supplier = parsed.get("supplier", {})
                    supplier_tax = supplier.get("taxNumber")
                    partner = None
                    if supplier_tax:
                        partner = db.execute(
                            select(Partner).where(Partner.tax_number == supplier_tax)
                        ).scalar_one_or_none()
                        if not partner:
                            partner = Partner(
                                name=supplier.get("name") or f"Partner {supplier_tax}",
                                tax_number=supplier_tax,
                                partner_type=PartnerType.supplier,
                                auto_detected=True,
                            )
                            db.add(partner)
                            db.flush()

                    # Create invoice
                    header = parsed.get("header", {})
                    summary = parsed.get("summary", {})

                    invoice = Invoice(
                        invoice_number=inv_number,
                        partner_id=partner.id if partner else None,
                        status=InvoiceStatus.pending_review,
                        invoice_date=_parse_date(header.get("invoiceIssueDate")),
                        fulfillment_date=_parse_date(header.get("invoiceDeliveryDate")),
                        due_date=_parse_date(header.get("paymentDate")),
                        payment_method=header.get("paymentMethod"),
                        net_amount=_parse_float(summary.get("invoiceNetAmount")),
                        vat_amount=_parse_float(summary.get("invoiceVatAmount")),
                        gross_amount=_parse_float(summary.get("invoiceGrossAmount")),
                        currency=header.get("currency") or "HUF",
                        original_filename=f"NAV_{inv_number}",
                        stored_filepath=f"nav_import/{inv_number}",
                    )
                    db.add(invoice)
                    db.flush()

                    # Create invoice lines
                    for idx, line_data in enumerate(parsed.get("lines", [])):
                        line = InvoiceLine(
                            invoice_id=invoice.id,
                            description=line_data.get("lineDescription"),
                            quantity=_parse_float(line_data.get("quantity")),
                            unit_price=_parse_float(line_data.get("unitPrice")),
                            net_amount=_parse_float(line_data.get("lineNetAmount")),
                            vat_rate=_parse_float(line_data.get("lineVatRate")),
                            vat_amount=_parse_float(line_data.get("lineVatAmount")),
                            gross_amount=_parse_float(line_data.get("lineGrossAmount")),
                            sort_order=idx,
                        )
                        db.add(line)

                    # Update partner stats
                    if partner and invoice.gross_amount:
                        partner.invoice_count += 1
                        partner.total_amount += invoice.gross_amount

                    invoices_created += 1

                if page >= available_page:
                    break
                page += 1

            # Update sync log
            sync_log.invoices_found = invoices_found
            sync_log.invoices_created = invoices_created
            sync_log.invoices_skipped = invoices_skipped
            sync_log.status = NavSyncStatus.completed
            sync_log.completed_at = datetime.utcnow()

            # Update config last_sync_at
            config.last_sync_at = datetime.utcnow()
            db.commit()

            logger.info(f"NAV sync completed: found={invoices_found}, created={invoices_created}, skipped={invoices_skipped}")

        except Exception as e:
            logger.error(f"NAV sync error: {e}")
            sync_log.status = NavSyncStatus.error
            sync_log.error_message = str(e)[:1000]
            sync_log.completed_at = datetime.utcnow()
            db.commit()
            raise self.retry(exc=e)


@celery_app.task(name="nav_sync_inbound_auto")
def nav_sync_inbound_auto_task():
    """Auto-sync: runs every 4 hours for all active configs, last 7 days."""
    from datetime import timedelta
    engine = _get_sync_engine()

    with Session(engine) as db:
        configs = db.execute(
            select(NavConfig).where(NavConfig.is_active == True)
        ).scalars().all()

        today = datetime.utcnow().date()
        date_from = (today - timedelta(days=7)).isoformat()
        date_to = today.isoformat()

        for config in configs:
            sync_log = NavSyncLog(
                nav_config_id=config.id,
                direction="inbound",
                date_from=today - timedelta(days=7),
                date_to=today,
                status=NavSyncStatus.running,
            )
            db.add(sync_log)
            db.commit()
            db.refresh(sync_log)

            nav_sync_inbound_task.delay(sync_log.id, config.id, date_from, date_to)


def _parse_date(date_str: str | None):
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None


def _parse_float(val: str | None) -> float | None:
    if not val:
        return None
    try:
        return float(val)
    except ValueError:
        return None
