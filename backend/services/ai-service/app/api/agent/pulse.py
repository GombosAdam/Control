import logging
from datetime import datetime

import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.config import settings
from common.models.cfo_metric import CfoMetric

logger = logging.getLogger(__name__)

_redis: aioredis.Redis | None = None


async def _get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


def _format_huf(value: float) -> str:
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:,.1f}M Ft".replace(",", " ")
    if abs(value) >= 1_000:
        return f"{value / 1_000:,.0f}e Ft".replace(",", " ")
    return f"{value:,.0f} Ft".replace(",", " ")


async def get_pulse(db: AsyncSession) -> str:
    """Generate a ~300 token pulse summary from cfo_metrics, cached in Redis."""
    try:
        r = await _get_redis()
        cached = await r.get("agent:pulse")
        if cached:
            return cached
    except Exception:
        logger.debug("Redis cache miss for pulse (non-critical)")

    period = datetime.now().strftime("%Y-%m")
    result = await db.execute(
        select(CfoMetric).where(CfoMetric.period == period)
    )
    metrics_rows = result.scalars().all()

    # Build a key→value dict
    m: dict[str, float] = {}
    for row in metrics_rows:
        m[row.metric_key] = row.value

    invoice_total = int(m.get("invoice_total_count", 0))
    invoice_amount = m.get("invoice_total_gross_amount", 0)
    overdue_count = int(m.get("overdue_invoice_count", 0))
    overdue_amount = m.get("overdue_invoice_amount", 0)
    budget_planned = m.get("budget_planned_total", 0)
    budget_actual = m.get("budget_actual_total", 0)
    budget_variance = m.get("budget_variance", 0)
    utilization = round(
        (budget_actual / budget_planned * 100) if budget_planned else 0, 1
    )
    over_budget_count = int(m.get("dept_count_over_budget", 0))
    processed_count = int(m.get("invoice_processed_count", 0))
    unprocessed_count = int(m.get("invoice_unprocessed_count", 0))
    dup_count = int(m.get("duplicate_invoice_count", 0))
    error_rate = round(m.get("error_rate_pct", 0), 1)
    po_count = int(m.get("po_open_count", 0))
    po_amount = m.get("po_open_amount", 0)

    forecast_net_30d = m.get("forecast_net_cash_30d", 0)
    avg_pay_days = m.get("avg_payment_days", 0)
    dep_risk_count = int(m.get("supplier_dependency_risk_count", 0))

    pulse_lines = [
        f"Számlák: {invoice_total} db ({_format_huf(invoice_amount)}) | "
        f"Feldolgozott: {processed_count}, feldolgozatlan: {unprocessed_count}",
        f"Lejárt: {overdue_count} ({_format_huf(overdue_amount)})",
        f"Budget felhasználás: {utilization}% | Eltérés: {_format_huf(budget_variance)}",
        f"Túllépő osztályok: {over_budget_count} db",
        f"Anomáliák: duplikátok {dup_count}, hibaarány {error_rate}%",
        f"Nyitott megrendelések: {po_count} db ({_format_huf(po_amount)})",
        f"Előrejelzés 30 nap: nettó ~{_format_huf(forecast_net_30d)}",
    ]
    if dep_risk_count > 0:
        pulse_lines.append(
            f"Szállítói kockázat: {dep_risk_count} magas függőségű, {avg_pay_days:.0f} nap"
        )
    pulse_lines.append(f"Frissítve: {period}")
    pulse = "\n".join(pulse_lines)

    try:
        r = await _get_redis()
        await r.set("agent:pulse", pulse, ex=settings.PULSE_CACHE_TTL)
    except Exception:
        logger.debug("Failed to cache pulse in Redis (non-critical)")

    return pulse
