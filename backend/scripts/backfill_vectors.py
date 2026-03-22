"""
Backfill script: Embed existing partners and invoices into Qdrant collections.

Usage:
    cd /app && python -m scripts.backfill_vectors

Or from host:
    docker exec invoice-celery python -m scripts.backfill_vectors
"""

import logging
import sys

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from common.config import settings
from common.models.partner import Partner
from common.models.invoice import Invoice
from common.vectorstore import VectorStoreManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def backfill_partners(db: Session, vs: VectorStoreManager) -> int:
    """Embed all existing partners into partner_embeddings collection."""
    partners = db.execute(select(Partner)).scalars().all()
    count = 0
    for partner in partners:
        if partner.vector_id:
            logger.debug("Partner %s already has vector_id, skipping", partner.name)
            continue

        embed_text = f"{partner.name}|{partner.tax_number or ''}"
        try:
            vs.store(
                collection="partner_embeddings",
                point_id=partner.id,
                text=embed_text,
                payload={
                    "partner_id": partner.id,
                    "name": partner.name,
                    "tax_number": partner.tax_number,
                },
            )
            partner.vector_id = partner.id
            count += 1
            if count % 10 == 0:
                db.commit()
                logger.info("Embedded %d partners...", count)
        except Exception as e:
            logger.error("Failed to embed partner %s: %s", partner.name, e)

    db.commit()
    return count


def backfill_invoice_fingerprints(db: Session, vs: VectorStoreManager) -> int:
    """Embed all existing invoices into invoice_fingerprints collection."""
    invoices = db.execute(
        select(Invoice).where(Invoice.vector_id.is_(None))
    ).scalars().all()
    count = 0
    for invoice in invoices:
        # Build fingerprint from invoice data
        parts = [
            invoice.partner.name if invoice.partner else "",
            invoice.partner.tax_number if invoice.partner and invoice.partner.tax_number else "",
            invoice.invoice_number or "",
            str(invoice.gross_amount or ""),
            invoice.currency or "HUF",
            str(invoice.invoice_date or ""),
        ]
        fingerprint = "|".join(parts)

        try:
            vs.store(
                collection="invoice_fingerprints",
                point_id=invoice.id,
                text=fingerprint,
                payload={
                    "invoice_id": invoice.id,
                    "fingerprint": fingerprint,
                },
            )
            invoice.vector_id = invoice.id
            count += 1
            if count % 10 == 0:
                db.commit()
                logger.info("Embedded %d invoices...", count)
        except Exception as e:
            logger.error("Failed to embed invoice %s: %s", invoice.id, e)

    db.commit()
    return count


def seed_text2sql_examples(vs: VectorStoreManager) -> int:
    """Seed the text2sql_examples collection from hardcoded few-shot examples."""
    from services.ai_service.app.api.chat.semantic_schema import FEW_SHOT_EXAMPLES

    count = 0
    for ex in FEW_SHOT_EXAMPLES:
        try:
            point_id = str(abs(hash(ex["question"])) % (2**63))
            vs.store(
                collection="text2sql_examples",
                point_id=point_id,
                text=ex["question"],
                payload={"question": ex["question"], "sql": ex["sql"]},
            )
            count += 1
        except Exception as e:
            logger.error("Failed to seed example '%s': %s", ex["question"][:50], e)

    return count


def main():
    logger.info("Starting vector backfill...")
    logger.info("Database: %s", settings.DATABASE_URL_SYNC[:50] + "...")
    logger.info("Qdrant: %s", settings.QDRANT_URL)
    logger.info("Ollama: %s", settings.OLLAMA_URL)

    engine = create_engine(settings.DATABASE_URL_SYNC, pool_pre_ping=True)
    db = Session(bind=engine)

    vs = VectorStoreManager(
        qdrant_url=settings.QDRANT_URL,
        ollama_url=settings.OLLAMA_URL,
        embed_model=settings.EMBEDDING_MODEL,
    )

    # Ensure all collections exist
    vs.ensure_collections()
    logger.info("Qdrant collections ensured")

    # Backfill partners
    partner_count = backfill_partners(db, vs)
    logger.info("Embedded %d partners into partner_embeddings", partner_count)

    # Backfill invoice fingerprints
    invoice_count = backfill_invoice_fingerprints(db, vs)
    logger.info("Embedded %d invoices into invoice_fingerprints", invoice_count)

    # Seed text2sql examples
    try:
        t2s_count = seed_text2sql_examples(vs)
        logger.info("Seeded %d text2sql examples", t2s_count)
    except Exception as e:
        logger.warning("Text2SQL seeding skipped (import error): %s", e)

    vs.close()
    db.close()
    logger.info("Backfill complete!")


if __name__ == "__main__":
    main()
