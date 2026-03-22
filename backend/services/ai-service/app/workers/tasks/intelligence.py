"""
Intelligence Layer — Celery tasks for decision support.
Triggered by invoice.enriched event.

Tasks:
  3a. suggest_budget_category — P&L category suggestion
  3b. suggest_po_match — PO auto-suggestion
  3c. detect_anomalies — anomaly detection
"""

import logging
import uuid
from datetime import datetime, date

import httpx
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from common.config import settings
from common.models.invoice import Invoice
from common.models.ai_enrichment import AIEnrichment
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

_sync_engine = create_engine(settings.DATABASE_URL_SYNC, pool_pre_ping=True)


def _get_db() -> Session:
    return Session(bind=_sync_engine)


# ---------------------------------------------------------------------------
# 3a. Budget Category Suggestion
# ---------------------------------------------------------------------------

@celery_app.task(name="suggest_budget_category")
def suggest_budget_category(invoice_id: str):
    """Suggest accounting/budget category for an invoice."""
    db = _get_db()
    try:
        invoice = db.get(Invoice, invoice_id)
        if not invoice:
            logger.error("Invoice %s not found", invoice_id)
            return

        suggested_code = None

        # Strategy 1: Historical partner data
        if invoice.partner_id:
            row = db.execute(text("""
                SELECT ae.account_code, COUNT(*) as cnt
                FROM accounting_entries ae
                JOIN invoices i ON ae.invoice_id = i.id
                WHERE i.partner_id = :pid
                GROUP BY ae.account_code
                ORDER BY cnt DESC
                LIMIT 1
            """), {"pid": invoice.partner_id}).first()

            if row:
                suggested_code = row[0]
                logger.info(
                    "Budget suggestion for %s: %s (from history)",
                    invoice_id, suggested_code,
                )

        # Strategy 2: Partner default
        if not suggested_code and invoice.partner_id:
            from common.models.partner import Partner
            partner = db.get(Partner, invoice.partner_id)
            if partner and partner.default_accounting_code:
                suggested_code = partner.default_accounting_code
                logger.info(
                    "Budget suggestion for %s: %s (partner default)",
                    invoice_id, suggested_code,
                )

        # Strategy 3: LLM fallback
        if not suggested_code and invoice.ocr_text:
            suggested_code = _llm_categorize(invoice.ocr_text)

        if suggested_code:
            invoice.suggested_accounting_code = suggested_code
            db.add(AIEnrichment(
                invoice_id=invoice_id,
                enrichment_type="budget_suggestion",
                result_data={"suggested_code": suggested_code},
                confidence=0.9 if not invoice.ocr_text else 0.6,
            ))
            db.commit()

    except Exception:
        logger.exception("Budget suggestion failed for %s", invoice_id)
        db.rollback()
    finally:
        db.close()


def _llm_categorize(ocr_text: str) -> str | None:
    """Use LLM to categorize invoice into P&L category."""
    prompt = (
        "Te egy magyar könyvelési asszisztens vagy. Az alábbi számla szövege alapján "
        "határozd meg a legvalószínűbb főkönyvi kategóriát. "
        "Válaszolj CSAK a kategória kódjával, semmi mással.\n"
        "Lehetséges kategóriák: 5110 (anyagköltség), 5200 (igénybe vett szolgáltatás), "
        "5300 (egyéb szolgáltatás), 5400 (bérköltség), 5500 (értékcsökkenés), "
        "8100 (pénzügyi ráfordítás), 8600 (rendkívüli ráfordítás)\n\n"
        f"Számla szöveg (első 500 karakter):\n{ocr_text[:500]}\n\n"
        "Kategória kód:"
    )
    try:
        response = httpx.post(
            f"{settings.OLLAMA_URL}/api/generate",
            json={
                "model": settings.LLM_MODEL,
                "prompt": prompt,
                "temperature": 0.0,
                "stream": False,
                "options": {"num_predict": 20},
            },
            timeout=60.0,
        )
        response.raise_for_status()
        result = response.json().get("response", "").strip()
        # Extract just the code
        import re
        match = re.search(r"\d{4}", result)
        return match.group(0) if match else None
    except Exception as e:
        logger.warning("LLM categorization failed: %s", e)
        return None


# ---------------------------------------------------------------------------
# 3b. PO Auto-Suggestion
# ---------------------------------------------------------------------------

@celery_app.task(name="suggest_po_match")
def suggest_po_match(invoice_id: str):
    """Suggest matching Purchase Orders for an invoice."""
    db = _get_db()
    try:
        invoice = db.get(Invoice, invoice_id)
        if not invoice:
            return

        suggestions = []

        # Strategy 1: Exact tax_id + amount match (existing logic, extended tolerance)
        if invoice.partner_id and invoice.gross_amount:
            rows = db.execute(text("""
                SELECT po.id, po.po_number, po.amount, po.supplier_name, po.status,
                       ABS(po.amount - :amount) / NULLIF(:amount, 0) as diff_pct
                FROM purchase_orders po
                WHERE po.status IN ('approved', 'received')
                  AND po.supplier_tax_id = (
                      SELECT p.tax_number FROM partners p WHERE p.id = :pid
                  )
                  AND ABS(po.amount - :amount) / NULLIF(:amount, 0) <= 0.10
                ORDER BY diff_pct ASC
                LIMIT 3
            """), {
                "pid": invoice.partner_id,
                "amount": invoice.gross_amount,
            }).fetchall()

            for row in rows:
                suggestions.append({
                    "po_id": row[0],
                    "po_number": row[1],
                    "amount": row[2],
                    "supplier_name": row[3],
                    "match_type": "tax_id_amount",
                    "confidence": round(1.0 - (row[5] or 0), 3),
                })

        # Strategy 2: Historical pattern — same partner's previous POs
        if invoice.partner_id and not suggestions:
            rows = db.execute(text("""
                SELECT po.id, po.po_number, po.amount, po.supplier_name, po.status
                FROM purchase_orders po
                JOIN invoices i ON i.purchase_order_id = po.id
                WHERE i.partner_id = :pid
                  AND po.status IN ('approved', 'received')
                ORDER BY po.created_at DESC
                LIMIT 3
            """), {"pid": invoice.partner_id}).fetchall()

            for row in rows:
                suggestions.append({
                    "po_id": row[0],
                    "po_number": row[1],
                    "amount": row[2],
                    "supplier_name": row[3],
                    "match_type": "historical",
                    "confidence": 0.5,
                })

        if suggestions:
            db.add(AIEnrichment(
                invoice_id=invoice_id,
                enrichment_type="po_suggestion",
                result_data={"suggestions": suggestions[:3]},
                confidence=suggestions[0]["confidence"] if suggestions else 0.0,
            ))
            db.commit()
            logger.info("PO suggestions for %s: %d found", invoice_id, len(suggestions))

    except Exception:
        logger.exception("PO suggestion failed for %s", invoice_id)
        db.rollback()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 3c. Anomaly Detection
# ---------------------------------------------------------------------------

@celery_app.task(name="detect_anomalies")
def detect_anomalies(invoice_id: str):
    """Detect anomalies in invoice data."""
    db = _get_db()
    try:
        invoice = db.get(Invoice, invoice_id)
        if not invoice:
            return

        anomalies = []

        # Check 1: Amount > 3x partner average
        if invoice.partner_id and invoice.gross_amount:
            row = db.execute(text("""
                SELECT AVG(gross_amount) as avg_amount
                FROM invoices
                WHERE partner_id = :pid
                  AND id != :iid
                  AND gross_amount IS NOT NULL
            """), {"pid": invoice.partner_id, "iid": invoice_id}).first()

            if row and row[0] and row[0] > 0:
                if invoice.gross_amount > row[0] * 3:
                    anomalies.append({
                        "type": "high_amount",
                        "message": f"Kiugró összeg: {invoice.gross_amount:,.0f} (partner átlag: {row[0]:,.0f})",
                        "severity": "warning",
                    })

        # Check 2: Future invoice date
        if invoice.invoice_date and invoice.invoice_date > date.today():
            anomalies.append({
                "type": "future_date",
                "message": f"Jövőbeli számla dátum: {invoice.invoice_date}",
                "severity": "warning",
            })

        # Check 3: Due date before invoice date
        if invoice.due_date and invoice.invoice_date and invoice.due_date < invoice.invoice_date:
            anomalies.append({
                "type": "invalid_due_date",
                "message": "Fizetési határidő korábbi, mint a számla dátuma",
                "severity": "error",
            })

        # Check 4: Missing critical fields
        missing = []
        if not invoice.invoice_number:
            missing.append("számlaszám")
        if not invoice.net_amount:
            missing.append("nettó összeg")
        if not invoice.gross_amount:
            missing.append("bruttó összeg")
        if not invoice.invoice_date:
            missing.append("számla dátuma")
        if missing:
            anomalies.append({
                "type": "missing_fields",
                "message": f"Hiányzó mezők: {', '.join(missing)}",
                "severity": "warning",
            })

        # Check 5: Duplicate invoice number from same supplier
        if invoice.invoice_number and invoice.partner_id:
            dup_count = db.execute(text("""
                SELECT COUNT(*) FROM invoices
                WHERE invoice_number = :inum
                  AND partner_id = :pid
                  AND id != :iid
            """), {
                "inum": invoice.invoice_number,
                "pid": invoice.partner_id,
                "iid": invoice_id,
            }).scalar()

            if dup_count and dup_count > 0:
                anomalies.append({
                    "type": "duplicate_number",
                    "message": f"Azonos számlaszám ({invoice.invoice_number}) már létezik ettől a szállítótól",
                    "severity": "error",
                })

        # Store results
        if anomalies:
            invoice.anomaly_flags = anomalies
        else:
            invoice.anomaly_flags = []

        db.add(AIEnrichment(
            invoice_id=invoice_id,
            enrichment_type="anomaly_detection",
            result_data={"anomalies": anomalies},
            confidence=1.0,
        ))
        db.commit()
        logger.info("Anomaly detection for %s: %d flags", invoice_id, len(anomalies))

    except Exception:
        logger.exception("Anomaly detection failed for %s", invoice_id)
        db.rollback()
    finally:
        db.close()
