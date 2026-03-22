"""Invoice processing pipeline - adapted from Unity server.
Uses Ollama VLM (qwen3:14b) on Unity server for OCR+extraction in one step.
Storage: PostgreSQL (not Qdrant).
"""
import logging
import json
import base64
from datetime import datetime
from pathlib import Path

import httpx
from pdf2image import convert_from_path
from sqlalchemy import select
from sqlalchemy.orm import Session

from common.config import settings
from common.models.invoice import Invoice, InvoiceStatus

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """Elemezd a következő számla képét és kinyerd a metaadatokat JSON formátumban.

A válaszod CSAK a JSON objektum legyen, semmi más szöveg!

Kötelező mezők:
- szallito_nev: Szállító/Eladó neve
- szallito_adoszam: Szállító adószáma
- szallito_bankszamlaszam: Bankszámlaszám (ha van)
- szamla_szam: Számla sorszáma/száma
- szamla_kelte: Számla kiállításának dátuma (YYYY-MM-DD)
- teljesites_datuma: Teljesítés dátuma (YYYY-MM-DD)
- fizetesi_hatarido: Fizetési határidő (YYYY-MM-DD)
- fizetesi_mod: Fizetési mód (pl. "átutalás", "készpénz", "bankkártya")
- netto_osszeg: Nettó összeg (szám, tizedesponttal)
- afa_kulcs: ÁFA kulcs százalékban (pl. 27, 18, 5, 0)
- afa_osszeg: ÁFA összeg (szám)
- brutto_osszeg: Bruttó összeg (szám)
- deviza: Pénznem (alapértelmezett: "HUF")

Ha egy mező nem található, használj null értéket.
A dátumokat YYYY-MM-DD formátumban add meg.
Az összegeket számként add meg, ne stringként.

JSON VÁLASZ:"""


def process_invoice_sync(invoice_id: str, db_url: str):
    """Process a single invoice through the full pipeline.
    Runs synchronously (called from worker thread or background task).
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from common.database import Base

    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        invoice = db.execute(select(Invoice).where(Invoice.id == invoice_id)).scalar_one_or_none()
        if not invoice:
            logger.error(f"Invoice {invoice_id} not found")
            return

        # Step 1: Update status to PROCESSING
        invoice.status = InvoiceStatus.ocr_processing
        db.commit()

        pdf_path = Path(invoice.stored_filepath)
        if not pdf_path.exists():
            invoice.status = InvoiceStatus.error
            db.commit()
            logger.error(f"PDF not found: {pdf_path}")
            return

        # Step 2: Convert PDF to image and send to VLM
        logger.info(f"Processing invoice {invoice_id}: {invoice.original_filename}")

        try:
            images = convert_from_path(str(pdf_path), dpi=300)
        except Exception as e:
            invoice.status = InvoiceStatus.error
            invoice.ocr_text = f"PDF conversion error: {e}"
            db.commit()
            logger.error(f"PDF conversion failed for {invoice_id}: {e}")
            return

        # Step 3: Lookup supplier template for better OCR
        template_example = None
        try:
            template_example = _lookup_supplier_template(invoice)
        except Exception as e:
            logger.debug(f"Template lookup skipped: {e}")

        # Step 3b: Send to Ollama VLM for OCR + extraction
        invoice.status = InvoiceStatus.extracting
        db.commit()

        all_results = []
        for i, img in enumerate(images):
            try:
                result = extract_with_vlm(img, i + 1, template_example=template_example)
                if result:
                    all_results.append(result)
            except Exception as e:
                logger.error(f"VLM extraction failed for page {i+1}: {e}")

        if not all_results:
            invoice.status = InvoiceStatus.error
            invoice.ocr_text = "VLM extraction returned no results"
            db.commit()
            return

        # Use first page result (most invoices are single page)
        extracted = all_results[0]
        raw_response = json.dumps(extracted, ensure_ascii=False, indent=2)

        # Step 4: Update invoice with extracted data
        invoice.ocr_text = f"--- Page 1 ---\n```json\n{raw_response}\n```"
        invoice.status = InvoiceStatus.ocr_done

        # Map extracted fields to invoice model
        field_mapping = {
            'szamla_szam': 'invoice_number',
            'netto_osszeg': 'net_amount',
            'afa_kulcs': 'vat_rate',
            'afa_osszeg': 'vat_amount',
            'brutto_osszeg': 'gross_amount',
            'deviza': 'currency',
            'fizetesi_mod': 'payment_method',
        }

        for src_key, dst_key in field_mapping.items():
            val = extracted.get(src_key)
            if val is not None:
                if dst_key in ('net_amount', 'vat_rate', 'vat_amount', 'gross_amount'):
                    try:
                        if isinstance(val, str):
                            val = val.replace(',', '').replace(' ', '')
                            # Remove currency suffix
                            for c in ['HUF', 'EUR', 'USD', 'CZK', 'RUB', 'RSD']:
                                val = val.replace(c, '').strip()
                        val = float(val)
                    except (ValueError, TypeError):
                        val = None
                if val is not None:
                    setattr(invoice, dst_key, val)

        # Parse dates
        for src_key, dst_key in [('szamla_kelte', 'invoice_date'), ('teljesites_datuma', 'fulfillment_date'), ('fizetesi_hatarido', 'due_date')]:
            val = extracted.get(src_key)
            if val:
                try:
                    from datetime import date as date_type
                    # Try common formats
                    for fmt in ['%Y-%m-%d', '%d.%m.%Y', '%Y/%m/%d', '%d/%m/%Y']:
                        try:
                            parsed = datetime.strptime(str(val), fmt).date()
                            setattr(invoice, dst_key, parsed)
                            break
                        except ValueError:
                            continue
                except Exception:
                    pass

        # Validate amounts
        warnings = validate_amounts(invoice)

        if warnings:
            invoice.status = InvoiceStatus.pending_review
        else:
            invoice.status = InvoiceStatus.pending_review  # Always needs review

        invoice.updated_at = datetime.utcnow()

        # Save extraction result (delete previous if reprocessing)
        from common.models.extraction import ExtractionResult
        existing_ext = db.execute(
            select(ExtractionResult).where(ExtractionResult.invoice_id == invoice_id)
        ).scalar_one_or_none()
        if existing_ext:
            db.delete(existing_ext)
            db.flush()

        extraction = ExtractionResult(
            invoice_id=invoice_id,
            raw_llm_response=raw_response,
            extracted_data=extracted,
            confidence_scores={},
            model_used=settings.VLM_MODEL,
        )
        db.add(extraction)
        db.commit()

        # Step 5: AI Enrichment (partner detect + confidence + duplicate)
        try:
            from app.workers.tasks.enrich_invoice import enrich_invoice_sync
            enrich_results = enrich_invoice_sync(invoice_id, extracted, db)
            if enrich_results.get('partner_id'):
                invoice.partner_id = enrich_results['partner_id']
            if enrich_results.get('is_duplicate'):
                invoice.is_duplicate = True
                invoice.duplicate_of_id = enrich_results.get('duplicate_of_id')
                invoice.similarity_score = enrich_results.get('similarity_score')
            if enrich_results.get('vector_id'):
                invoice.vector_id = enrich_results['vector_id']
            if enrich_results.get('ai_confidence') is not None:
                invoice.ai_confidence = enrich_results['ai_confidence']
            if enrich_results.get('confidence_scores'):
                extraction.confidence_scores = enrich_results['confidence_scores']
            db.commit()
        except Exception as e:
            logger.warning(f"AI enrichment failed for {invoice_id}: {e}")

        logger.info(f"Invoice {invoice_id} processed -> pending_review")

        # Publish events
        try:
            import redis as sync_redis
            r = sync_redis.from_url(settings.REDIS_URL)
            import json as _json
            r.publish("events:invoice.approved", _json.dumps({"event": "invoice.approved", "payload": {"invoice_id": invoice_id}}))
            # Publish enrichment event for intelligence layer
            r.publish("events:invoice.enriched", _json.dumps({
                "event": "invoice.enriched",
                "payload": {"invoice_id": invoice_id, "ai_confidence": invoice.ai_confidence}
            }))
            r.close()
        except Exception:
            logger.warning("Failed to publish invoice event")

    except Exception as e:
        logger.exception(f"Error processing invoice {invoice_id}: {e}")
        try:
            invoice.status = InvoiceStatus.error
            invoice.ocr_text = str(e)
            db.commit()
        except:
            pass
    finally:
        db.close()


def _lookup_supplier_template(invoice: Invoice) -> dict | None:
    """Look up supplier template from Qdrant for better OCR."""
    from common.vectorstore import VectorStoreManager

    # If we know the partner, search by their name/tax info
    supplier_hint = invoice.original_filename  # use filename as hint
    if not supplier_hint:
        return None

    vs = VectorStoreManager(
        qdrant_url=settings.QDRANT_URL,
        ollama_url=settings.OLLAMA_URL,
        embed_model="nomic-embed-text",
    )
    try:
        results = vs.search(
            collection="supplier_templates",
            text=supplier_hint,
            top_k=1,
            min_score=0.7,
        )
        if results:
            return results[0]["payload"].get("extraction_example")
    except Exception:
        pass
    finally:
        vs.close()
    return None


def extract_with_vlm(img, page_num: int, template_example: dict | None = None) -> dict:
    """Send image to Ollama VLM for OCR + extraction in one step."""
    import io

    # Convert PIL image to base64
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

    # Build prompt with optional template example
    prompt = EXTRACTION_PROMPT
    if template_example:
        example_json = json.dumps(template_example, ensure_ascii=False, indent=2)
        prompt += f"\n\nPélda egy hasonló szállítótól korábban sikeresen kinyert adat:\n```json\n{example_json}\n```\n\nHasználd referenciaként a mezők formátumához.\n\nJSON VÁLASZ:"

    try:
        response = httpx.post(
            f"{settings.OLLAMA_URL}/api/generate",
            json={
                "model": settings.VLM_MODEL,
                "prompt": prompt,
                "images": [img_base64],
                "temperature": settings.LLM_TEMPERATURE,
                "stream": False,
            },
            timeout=180.0,
        )
        response.raise_for_status()

        result = response.json()
        llm_response = result.get("response", "")

        # Parse JSON from response
        clean = llm_response.strip()
        if clean.startswith("```json"):
            clean = clean[7:]
        if clean.startswith("```"):
            clean = clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]
        clean = clean.strip()

        return json.loads(clean)

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse VLM JSON response (page {page_num}): {e}")
        logger.debug(f"Raw response: {llm_response[:500]}")
        return None
    except Exception as e:
        logger.error(f"VLM request failed (page {page_num}): {e}")
        return None


from app.workers.celery_app import celery_app


@celery_app.task(
    name="process_invoice",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
)
def process_invoice_task(self, invoice_id: str):
    """Celery task wrapper."""
    try:
        process_invoice_sync(invoice_id, settings.DATABASE_URL_SYNC)
    except Exception as exc:
        logger.error(f"Task failed for {invoice_id}: {exc}")
        raise self.retry(exc=exc)


def validate_amounts(invoice: Invoice) -> list:
    """Validate that netto + afa ≈ brutto."""
    warnings = []
    if invoice.net_amount and invoice.vat_amount and invoice.gross_amount:
        expected = invoice.net_amount + invoice.vat_amount
        actual = invoice.gross_amount
        if actual > 0:
            diff_percent = abs((expected - actual) / actual) * 100
            if diff_percent > 5:
                warnings.append(
                    f"Amount mismatch: {invoice.net_amount} + {invoice.vat_amount} "
                    f"!= {invoice.gross_amount} ({diff_percent:.1f}% diff)"
                )
    return warnings
