"""
Celery task for submitting outbound invoices to NAV.
"""

import base64
import logging
from datetime import datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.workers.celery_app import celery_app
from app.config import settings
from app.models.nav_config import NavConfig
from app.models.nav_transaction import NavTransaction, NavTransactionStatus
from app.models.invoice import Invoice
from app.nav_client.client import NAVOnlineSzamlaClient
from app.nav_client.mock_client import MockNAVOnlineSzamlaClient
from app.nav_client.exceptions import NAVApiError, NAVConnectionError
from app.api.config.service import _decrypt
from lxml import etree

import asyncio

logger = logging.getLogger(__name__)

DATA_NS = "http://schemas.nav.gov.hu/OSA/3.0/data"


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _build_invoice_xml(invoice: Invoice) -> str:
    """Build NAV-compatible invoice XML from an Invoice model."""
    root = etree.Element(f"{{{DATA_NS}}}InvoiceData", nsmap={None: DATA_NS})
    etree.SubElement(root, f"{{{DATA_NS}}}invoiceNumber").text = invoice.invoice_number or ""
    etree.SubElement(root, f"{{{DATA_NS}}}invoiceIssueDate").text = (
        invoice.invoice_date.isoformat() if invoice.invoice_date else ""
    )
    etree.SubElement(root, f"{{{DATA_NS}}}completenessIndicator").text = "false"

    # Supplier info (from config — will be filled by NAV)
    # Customer info
    if invoice.partner:
        customer = etree.SubElement(root, f"{{{DATA_NS}}}customerInfo")
        if invoice.partner.tax_number:
            tax_el = etree.SubElement(customer, f"{{{DATA_NS}}}customerTaxNumber")
            etree.SubElement(tax_el, f"{{{DATA_NS}}}taxpayerId").text = invoice.partner.tax_number[:8]
        etree.SubElement(customer, f"{{{DATA_NS}}}customerName").text = invoice.partner.name

    # Invoice detail
    detail = etree.SubElement(root, f"{{{DATA_NS}}}invoiceDetail")
    etree.SubElement(detail, f"{{{DATA_NS}}}currencyCode").text = invoice.currency or "HUF"
    if invoice.invoice_date:
        etree.SubElement(detail, f"{{{DATA_NS}}}invoiceDeliveryDate").text = invoice.invoice_date.isoformat()
    if invoice.due_date:
        etree.SubElement(detail, f"{{{DATA_NS}}}paymentDate").text = invoice.due_date.isoformat()
    if invoice.payment_method:
        etree.SubElement(detail, f"{{{DATA_NS}}}paymentMethod").text = invoice.payment_method
    etree.SubElement(detail, f"{{{DATA_NS}}}invoiceAppearance").text = "ELECTRONIC"

    # Lines
    lines_el = etree.SubElement(root, f"{{{DATA_NS}}}invoiceLines")
    for line in (invoice.lines or []):
        line_el = etree.SubElement(lines_el, f"{{{DATA_NS}}}line")
        etree.SubElement(line_el, f"{{{DATA_NS}}}lineNumber").text = str(line.sort_order + 1)
        if line.description:
            etree.SubElement(line_el, f"{{{DATA_NS}}}lineDescription").text = line.description
        if line.quantity is not None:
            etree.SubElement(line_el, f"{{{DATA_NS}}}quantity").text = str(line.quantity)
        if line.unit_price is not None:
            etree.SubElement(line_el, f"{{{DATA_NS}}}unitPrice").text = str(line.unit_price)

        amounts = etree.SubElement(line_el, f"{{{DATA_NS}}}lineAmountsNormal")
        net_data = etree.SubElement(amounts, f"{{{DATA_NS}}}lineNetAmountData")
        etree.SubElement(net_data, f"{{{DATA_NS}}}lineNetAmount").text = str(line.net_amount or 0)
        vat_rate_el = etree.SubElement(amounts, f"{{{DATA_NS}}}lineVatRate")
        etree.SubElement(vat_rate_el, f"{{{DATA_NS}}}vatPercentage").text = str(line.vat_rate or 0)
        vat_data = etree.SubElement(amounts, f"{{{DATA_NS}}}lineVatData")
        etree.SubElement(vat_data, f"{{{DATA_NS}}}lineVatAmount").text = str(line.vat_amount or 0)
        gross_data = etree.SubElement(amounts, f"{{{DATA_NS}}}lineGrossAmountData")
        etree.SubElement(gross_data, f"{{{DATA_NS}}}lineGrossAmountNormal").text = str(line.gross_amount or 0)

    # Summary
    summary = etree.SubElement(root, f"{{{DATA_NS}}}invoiceSummary")
    summary_normal = etree.SubElement(summary, f"{{{DATA_NS}}}summaryNormal")
    etree.SubElement(summary_normal, f"{{{DATA_NS}}}invoiceNetAmount").text = str(invoice.net_amount or 0)
    etree.SubElement(summary_normal, f"{{{DATA_NS}}}invoiceVatAmount").text = str(invoice.vat_amount or 0)
    gross_el = etree.SubElement(summary, f"{{{DATA_NS}}}summaryGrossData")
    etree.SubElement(gross_el, f"{{{DATA_NS}}}invoiceGrossAmount").text = str(invoice.gross_amount or 0)

    return etree.tostring(root, xml_declaration=True, encoding="UTF-8").decode("utf-8")


@celery_app.task(name="nav_submit_outbound", bind=True, max_retries=2)
def nav_submit_outbound_task(self, transaction_id: str):
    """Submit an invoice to NAV."""
    engine = create_engine(settings.DATABASE_URL_SYNC, pool_size=5)

    with Session(engine) as db:
        txn = db.execute(
            select(NavTransaction).where(NavTransaction.id == transaction_id)
        ).scalar_one_or_none()
        if not txn:
            logger.error(f"Transaction not found: {transaction_id}")
            return

        config = db.execute(
            select(NavConfig).where(NavConfig.id == txn.nav_config_id)
        ).scalar_one_or_none()
        if not config:
            txn.status = NavTransactionStatus.error
            txn.error_message = "Config not found"
            db.commit()
            return

        invoice = db.execute(
            select(Invoice).where(Invoice.id == txn.invoice_id)
        ).scalar_one_or_none()
        if not invoice:
            txn.status = NavTransactionStatus.error
            txn.error_message = "Invoice not found"
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

            # Build invoice XML
            invoice_xml = _build_invoice_xml(invoice)
            invoice_b64 = base64.b64encode(invoice_xml.encode("utf-8")).decode("utf-8")

            txn.request_xml = invoice_xml
            txn.status = NavTransactionStatus.sent

            # Submit to NAV
            nav_txn_id = _run_async(client.manage_invoice([{
                "operation": txn.operation.value,
                "invoice_data_base64": invoice_b64,
            }]))

            txn.transaction_id = nav_txn_id
            txn.status = NavTransactionStatus.processing
            db.commit()

            logger.info(f"Invoice {invoice.invoice_number} submitted to NAV, txn={nav_txn_id}")

        except (NAVApiError, NAVConnectionError) as e:
            logger.error(f"NAV submit error for txn {transaction_id}: {e}")
            txn.status = NavTransactionStatus.error
            txn.error_code = getattr(e, "error_code", None)
            txn.error_message = str(e)[:1000]
            txn.retry_count += 1
            db.commit()
            raise self.retry(exc=e)
        except Exception as e:
            logger.error(f"Unexpected error for txn {transaction_id}: {e}")
            txn.status = NavTransactionStatus.error
            txn.error_message = str(e)[:1000]
            db.commit()
            raise
