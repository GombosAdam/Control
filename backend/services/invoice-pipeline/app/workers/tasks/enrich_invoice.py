"""
AI Enrichment pipeline — runs inline after OCR extraction.
Three steps:
  2a. Partner auto-detect (exact DB match → fuzzy Qdrant match → create new)
  2b. Confidence scoring (rule-based, deterministic)
  2c. Duplicate detection (vector similarity)
"""

import logging
import uuid
from datetime import datetime

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from common.config import settings
from common.models.invoice import Invoice
from common.models.partner import Partner
from common.models.ai_enrichment import AIEnrichment
from common.vectorstore import VectorStoreManager

logger = logging.getLogger(__name__)


def _get_vectorstore() -> VectorStoreManager:
    return VectorStoreManager(
        qdrant_url=settings.QDRANT_URL,
        ollama_url=settings.OLLAMA_URL,
        embed_model=settings.EMBEDDING_MODEL,
    )


def enrich_invoice_sync(
    invoice_id: str,
    extracted: dict,
    db: Session,
) -> dict:
    """Run all enrichment steps. Returns dict of results to apply to invoice."""
    results = {}

    try:
        vs = _get_vectorstore()
        vs.ensure_collections()
    except Exception as e:
        logger.warning("VectorStore init failed, skipping enrichment: %s", e)
        results["confidence_scores"] = _compute_confidence(extracted, partner_known=False)
        results["ai_confidence"] = _weighted_average(results["confidence_scores"])
        return results

    # Step 2a: Partner auto-detect
    try:
        partner_result = _detect_partner(extracted, db, vs)
        results.update(partner_result)
    except Exception as e:
        logger.warning("Partner detection failed for %s: %s", invoice_id, e)

    # Step 2b: Confidence scoring
    partner_known = results.get("partner_id") is not None
    confidence_scores = _compute_confidence(extracted, partner_known)
    results["confidence_scores"] = confidence_scores
    results["ai_confidence"] = _weighted_average(confidence_scores)

    # Step 2c: Duplicate detection
    try:
        dup_result = _detect_duplicate(invoice_id, extracted, db, vs)
        results.update(dup_result)
    except Exception as e:
        logger.warning("Duplicate detection failed for %s: %s", invoice_id, e)

    # Store enrichment records
    try:
        _store_enrichment_records(invoice_id, results, db)
    except Exception as e:
        logger.warning("Failed to store enrichment records: %s", e)

    try:
        vs.close()
    except Exception:
        pass

    return results


# ---------------------------------------------------------------------------
# 2a. Partner Auto-Detect
# ---------------------------------------------------------------------------

def _detect_partner(extracted: dict, db: Session, vs: VectorStoreManager) -> dict:
    """Detect and link partner from extracted invoice data."""
    tax_number = extracted.get("szallito_adoszam")
    supplier_name = extracted.get("szallito_nev", "")
    bank_account = extracted.get("szallito_bankszamlaszam")

    # 1. Exact match by tax number
    if tax_number:
        partner = db.execute(
            select(Partner).where(Partner.tax_number == str(tax_number))
        ).scalar_one_or_none()
        if partner:
            logger.info("Partner exact match by tax_number: %s → %s", tax_number, partner.name)
            return {"partner_id": partner.id}

    # 2. Fuzzy match via Qdrant
    if supplier_name:
        search_text = f"{supplier_name}|{tax_number or ''}"
        matches = vs.search(
            collection="partner_embeddings",
            text=search_text,
            top_k=1,
            min_score=settings.PARTNER_MATCH_THRESHOLD,
        )
        if matches:
            best = matches[0]
            partner_id = best["payload"].get("partner_id")
            if partner_id:
                logger.info(
                    "Partner fuzzy match: '%s' → %s (score=%.3f)",
                    supplier_name, partner_id, best["score"],
                )
                return {"partner_id": partner_id}

    # 3. Create new partner
    if supplier_name:
        new_partner = Partner(
            id=str(uuid.uuid4()),
            name=supplier_name,
            tax_number=str(tax_number) if tax_number else None,
            bank_account=str(bank_account) if bank_account else None,
            auto_detected=True,
        )
        db.add(new_partner)
        db.flush()

        # Embed and store in Qdrant
        embed_text = f"{supplier_name}|{tax_number or ''}"
        point_id = new_partner.id
        try:
            vs.store(
                collection="partner_embeddings",
                point_id=point_id,
                text=embed_text,
                payload={
                    "partner_id": new_partner.id,
                    "name": supplier_name,
                    "tax_number": str(tax_number) if tax_number else None,
                },
            )
            new_partner.vector_id = point_id
        except Exception as e:
            logger.warning("Failed to embed new partner: %s", e)

        logger.info("Created new auto-detected partner: %s (%s)", supplier_name, new_partner.id)
        return {"partner_id": new_partner.id}

    return {}


# ---------------------------------------------------------------------------
# 2b. Confidence Scoring
# ---------------------------------------------------------------------------

def _compute_confidence(extracted: dict, partner_known: bool) -> dict:
    """Rule-based confidence scoring per field."""
    scores = {}

    field_checks = {
        "szamla_szam": extracted.get("szamla_szam"),
        "szamla_kelte": extracted.get("szamla_kelte"),
        "teljesites_datuma": extracted.get("teljesites_datuma"),
        "fizetesi_hatarido": extracted.get("fizetesi_hatarido"),
        "netto_osszeg": extracted.get("netto_osszeg"),
        "afa_osszeg": extracted.get("afa_osszeg"),
        "brutto_osszeg": extracted.get("brutto_osszeg"),
        "szallito_nev": extracted.get("szallito_nev"),
        "szallito_adoszam": extracted.get("szallito_adoszam"),
    }

    for field_name, value in field_checks.items():
        score = 0.0

        # Not null → +0.3
        if value is not None and str(value).strip():
            score += 0.3

            # Format validation → +0.3
            if _validate_format(field_name, value):
                score += 0.3

        # Known partner → +0.2
        if partner_known:
            score += 0.2

        scores[field_name] = round(min(score, 1.0), 2)

    # Amount consistency check → bonus for amount fields
    netto = _to_float(extracted.get("netto_osszeg"))
    afa = _to_float(extracted.get("afa_osszeg"))
    brutto = _to_float(extracted.get("brutto_osszeg"))

    if netto is not None and afa is not None and brutto is not None and brutto > 0:
        expected = netto + afa
        diff_pct = abs((expected - brutto) / brutto)
        if diff_pct <= 0.01:  # ±1% tolerance
            for f in ("netto_osszeg", "afa_osszeg", "brutto_osszeg"):
                scores[f] = round(min(scores.get(f, 0) + 0.2, 1.0), 2)

    return scores


def _validate_format(field_name: str, value) -> bool:
    """Check if value format is valid for the given field."""
    import re

    val_str = str(value).strip()

    if field_name in ("szamla_kelte", "teljesites_datuma", "fizetesi_hatarido"):
        # Date: should match YYYY-MM-DD or common formats
        return bool(re.match(r"^\d{4}-\d{2}-\d{2}$", val_str))

    if field_name in ("netto_osszeg", "afa_osszeg", "brutto_osszeg"):
        try:
            float(str(value).replace(",", "").replace(" ", ""))
            return True
        except (ValueError, TypeError):
            return False

    if field_name == "szallito_adoszam":
        # Hungarian tax number format: 8 digits - 1 digit - 2 digits
        cleaned = val_str.replace("-", "").replace(" ", "")
        return bool(re.match(r"^\d{8,11}$", cleaned))

    # Default: non-empty is valid
    return bool(val_str)


def _to_float(val) -> float | None:
    if val is None:
        return None
    try:
        if isinstance(val, str):
            val = val.replace(",", "").replace(" ", "")
        return float(val)
    except (ValueError, TypeError):
        return None


def _weighted_average(scores: dict) -> float:
    """Compute weighted average confidence."""
    if not scores:
        return 0.0
    # Higher weight for critical fields
    weights = {
        "szamla_szam": 1.5,
        "brutto_osszeg": 1.5,
        "szallito_nev": 1.2,
        "szallito_adoszam": 1.2,
        "szamla_kelte": 1.0,
        "netto_osszeg": 1.0,
        "afa_osszeg": 0.8,
        "teljesites_datuma": 0.6,
        "fizetesi_hatarido": 0.6,
    }
    total_weight = 0.0
    total_score = 0.0
    for field, score in scores.items():
        w = weights.get(field, 1.0)
        total_weight += w
        total_score += score * w
    return round(total_score / total_weight, 3) if total_weight > 0 else 0.0


# ---------------------------------------------------------------------------
# 2c. Duplicate Detection
# ---------------------------------------------------------------------------

def _detect_duplicate(
    invoice_id: str,
    extracted: dict,
    db: Session,
    vs: VectorStoreManager,
) -> dict:
    """Detect duplicate invoices via vector similarity."""
    # Build fingerprint
    parts = [
        str(extracted.get("szallito_nev", "")),
        str(extracted.get("szallito_adoszam", "")),
        str(extracted.get("szamla_szam", "")),
        str(extracted.get("brutto_osszeg", "")),
        str(extracted.get("deviza", "HUF")),
        str(extracted.get("szamla_kelte", "")),
    ]
    fingerprint = "|".join(parts)

    # Embed
    vector = vs.embed_text(fingerprint)

    # Store this invoice's fingerprint
    point_id = invoice_id
    vs.store_with_vector(
        collection="invoice_fingerprints",
        point_id=point_id,
        vector=vector,
        payload={
            "invoice_id": invoice_id,
            "fingerprint": fingerprint,
        },
    )

    # Search for similar (top-3, excluding self)
    matches = vs.search_by_vector(
        collection="invoice_fingerprints",
        vector=vector,
        top_k=4,
        min_score=settings.DUPLICATE_THRESHOLD,
    )

    # Filter out self
    matches = [m for m in matches if m["payload"].get("invoice_id") != invoice_id]

    result = {"vector_id": point_id}

    if matches:
        best = matches[0]
        result["is_duplicate"] = True
        result["duplicate_of_id"] = best["payload"].get("invoice_id")
        result["similarity_score"] = best["score"]
        logger.info(
            "Duplicate detected for %s → %s (score=%.3f)",
            invoice_id, result["duplicate_of_id"], best["score"],
        )

    return result


# ---------------------------------------------------------------------------
# Enrichment records
# ---------------------------------------------------------------------------

def _store_enrichment_records(invoice_id: str, results: dict, db: Session) -> None:
    """Store AIEnrichment records for tracking."""
    if results.get("partner_id"):
        db.add(AIEnrichment(
            invoice_id=invoice_id,
            enrichment_type="partner_detection",
            result_data={"partner_id": results["partner_id"]},
            confidence=1.0 if results.get("partner_id") else 0.0,
        ))

    if results.get("confidence_scores"):
        db.add(AIEnrichment(
            invoice_id=invoice_id,
            enrichment_type="confidence_scoring",
            result_data=results["confidence_scores"],
            confidence=results.get("ai_confidence"),
        ))

    if results.get("is_duplicate"):
        db.add(AIEnrichment(
            invoice_id=invoice_id,
            enrichment_type="duplicate_check",
            result_data={
                "duplicate_of_id": results.get("duplicate_of_id"),
                "similarity_score": results.get("similarity_score"),
            },
            confidence=results.get("similarity_score"),
        ))

    db.flush()
