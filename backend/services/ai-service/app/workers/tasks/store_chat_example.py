"""
Celery task: Store successful chat question→SQL pairs in Qdrant for RAG.
Also handles supplier template learning from extraction corrections.
"""

import logging

from common.config import settings
from common.vectorstore import VectorStoreManager
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def _get_vectorstore() -> VectorStoreManager:
    return VectorStoreManager(
        qdrant_url=settings.QDRANT_URL,
        ollama_url=settings.OLLAMA_URL,
        embed_model=settings.EMBEDDING_MODEL,
    )


@celery_app.task(name="store_chat_example")
def store_chat_example(question: str, sql: str):
    """Store a successful question→SQL pair for RAG, with dedup."""
    vs = _get_vectorstore()
    try:
        vs.ensure_collections()
        text_to_embed = f"{question}"
        vector = vs.embed_text(text_to_embed)

        # Dedup check: if very similar example exists, skip
        existing = vs.search_by_vector(
            collection="text2sql_examples",
            vector=vector,
            top_k=1,
            min_score=settings.RAG_DEDUP_THRESHOLD,
        )
        if existing:
            logger.debug(
                "Skipping RAG store — similar example exists (score=%.3f): %s",
                existing[0]["score"], question[:80],
            )
            return

        # Store new example
        point_id = str(abs(hash(question)) % (2**63))
        vs.store_with_vector(
            collection="text2sql_examples",
            point_id=point_id,
            vector=vector,
            payload={"question": question, "sql": sql},
        )
        logger.info("Stored RAG chat example: %s", question[:80])

    except Exception:
        logger.exception("Failed to store chat example")
    finally:
        vs.close()


@celery_app.task(name="store_supplier_template")
def store_supplier_template(invoice_id: str):
    """Store supplier extraction template for OCR learning."""
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session
    from common.models.invoice import Invoice
    from common.models.extraction import ExtractionResult
    from common.models.partner import Partner

    engine = create_engine(settings.DATABASE_URL_SYNC, pool_pre_ping=True)
    db = Session(bind=engine)
    vs = _get_vectorstore()

    try:
        vs.ensure_collections()

        invoice = db.get(Invoice, invoice_id)
        if not invoice or not invoice.partner_id:
            return

        extraction = db.execute(
            select(ExtractionResult).where(ExtractionResult.invoice_id == invoice_id)
        ).scalar_one_or_none()
        if not extraction or not extraction.extracted_data:
            return

        partner = db.get(Partner, invoice.partner_id)
        if not partner:
            return

        # Build template text for embedding
        template_text = f"{partner.name}|{partner.tax_number or ''}"

        # Store template
        point_id = f"template_{invoice_id}"
        vs.store(
            collection="supplier_templates",
            point_id=point_id,
            text=template_text,
            payload={
                "partner_id": partner.id,
                "supplier_name": partner.name,
                "tax_number": partner.tax_number,
                "extraction_example": extraction.extracted_data,
                "invoice_id": invoice_id,
            },
        )
        logger.info(
            "Stored supplier template for %s (partner: %s)",
            invoice_id, partner.name,
        )

    except Exception:
        logger.exception("Failed to store supplier template for %s", invoice_id)
    finally:
        db.close()
        vs.close()
