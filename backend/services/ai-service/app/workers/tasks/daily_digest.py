"""
Celery task: send_daily_digest — daily at configured hour.
Collects CFO metrics, anomalies, bottleneck data and POSTs a structured JSON
to the configured webhook URL (Slack/Teams/email relay compatible).
"""

import logging
from datetime import datetime
from ipaddress import ip_address
from urllib.parse import urlparse

import httpx
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from common.config import settings
from app.workers.celery_app import celery_app

_sync_engine = create_engine(settings.DATABASE_URL_SYNC, pool_pre_ping=True)

logger = logging.getLogger(__name__)


def _is_safe_url(url: str) -> bool:
    """Basic SSRF protection: reject internal/private IPs."""
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        if not hostname or not parsed.scheme.startswith("http"):
            return False
        try:
            addr = ip_address(hostname)
            if addr.is_private or addr.is_loopback or addr.is_reserved:
                return False
        except ValueError:
            # Not a raw IP — hostname is OK (DNS could still resolve to private,
            # but that requires network-level protection)
            pass
        return True
    except Exception:
        return False


def _fmt(value: float) -> str:
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:,.1f}M Ft".replace(",", " ")
    if abs(value) >= 1_000:
        return f"{int(value):,} Ft".replace(",", " ")
    return f"{int(value)} Ft"


@celery_app.task(name="send_daily_digest")
def send_daily_digest():
    """Collect metrics and send daily digest to webhook."""
    if not settings.DAILY_DIGEST_ENABLED:
        logger.info("Daily digest is disabled, skipping.")
        return {"status": "disabled"}

    webhook_url = settings.DAILY_DIGEST_WEBHOOK_URL
    if not webhook_url:
        logger.warning("DAILY_DIGEST_WEBHOOK_URL is empty, skipping.")
        return {"status": "no_url"}

    if not _is_safe_url(webhook_url):
        logger.error("Webhook URL rejected by SSRF check: %s", webhook_url[:100])
        return {"status": "unsafe_url"}

    period = datetime.now().strftime("%Y-%m")
    db = Session(bind=_sync_engine)

    try:
        # Fetch all metrics for current period
        result = db.execute(text(
            "SELECT metric_key, value FROM cfo_metrics WHERE period = :period"
        ), {"period": period})
        m = {row[0]: row[1] for row in result.fetchall()}

        # Fetch pending approvals count
        result = db.execute(text(
            "SELECT COUNT(*) FROM invoice_approvals WHERE status = 'pending'"
        ))
        pending_approvals = result.scalar() or 0

        # Fetch top 3 slow approvers
        result = db.execute(text("""
            SELECT u.full_name, ia.step_name,
                   ROUND(AVG(EXTRACT(EPOCH FROM (ia.decided_at - ia.created_at)) / 3600)::NUMERIC, 1) AS avg_hours
            FROM invoice_approvals ia
            JOIN users u ON u.id = ia.decided_by
            WHERE ia.decided_at IS NOT NULL
            GROUP BY u.full_name, ia.step_name
            ORDER BY avg_hours DESC
            LIMIT 3
        """))
        slow_approvers = [
            {"name": row[0], "step": row[1], "avg_hours": float(row[2])}
            for row in result.fetchall()
        ]

        # Determine status
        overdue = int(m.get("overdue_invoice_count", 0))
        budget_planned = m.get("budget_planned_total", 0)
        budget_actual = m.get("budget_actual_total", 0)
        utilization = (budget_actual / budget_planned * 100) if budget_planned > 0 else 0
        unprocessed = int(m.get("invoice_unprocessed_count", 0))

        if overdue > 0 or utilization > 95:
            status = "critical"
        elif unprocessed > 5 or utilization > 80:
            status = "warning"
        else:
            status = "ok"

        digest = {
            "status": status,
            "period": period,
            "generated_at": datetime.now().isoformat(),
            "sections": {
                "financial_position": {
                    "budget_planned": m.get("budget_planned_total", 0),
                    "budget_actual": m.get("budget_actual_total", 0),
                    "budget_variance": m.get("budget_variance", 0),
                    "utilization_pct": round(utilization, 1),
                    "pnl_revenue": m.get("pnl_revenue", 0),
                    "pnl_ebitda": m.get("pnl_ebitda", 0),
                    "pnl_net_income": m.get("pnl_net_income", 0),
                },
                "invoices": {
                    "total_count": int(m.get("invoice_total_count", 0)),
                    "total_amount": m.get("invoice_total_gross_amount", 0),
                    "processed": int(m.get("invoice_processed_count", 0)),
                    "unprocessed": unprocessed,
                    "overdue_count": overdue,
                    "overdue_amount": m.get("overdue_invoice_amount", 0),
                    "duplicate_count": int(m.get("duplicate_invoice_count", 0)),
                    "error_rate_pct": m.get("error_rate_pct", 0),
                },
                "forecast": {
                    "cash_in_30d": m.get("forecast_cash_in_30d", 0),
                    "cash_out_30d": m.get("forecast_cash_out_30d", 0),
                    "net_cash_30d": m.get("forecast_net_cash_30d", 0),
                    "net_cash_60d": m.get("forecast_net_cash_60d", 0),
                    "net_cash_90d": m.get("forecast_net_cash_90d", 0),
                },
                "supplier_risk": {
                    "avg_payment_days": m.get("avg_payment_days", 0),
                    "dependency_risk_count": int(m.get("supplier_dependency_risk_count", 0)),
                    "price_trend_pct": m.get("supplier_price_trend_pct", 0),
                },
                "bottleneck": {
                    "pending_approvals": pending_approvals,
                    "slow_approvers": slow_approvers,
                },
                "yoy": {
                    "revenue_change_pct": m.get("revenue_yoy_change_pct", 0),
                    "expense_change_pct": m.get("expense_yoy_change_pct", 0),
                    "ebitda_change_pct": m.get("ebitda_yoy_change_pct", 0),
                    "invoice_count_change_pct": m.get("invoice_count_yoy_change_pct", 0),
                },
            },
        }

        # POST to webhook
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(webhook_url, json=digest)
            resp.raise_for_status()

        logger.info("Daily digest sent successfully (status=%s)", status)
        return {"status": "sent", "digest_status": status}

    except Exception as e:
        logger.exception("Failed to send daily digest")
        return {"status": "error", "error": str(e)[:200]}
    finally:
        db.close()
