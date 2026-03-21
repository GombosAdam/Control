"""
Celery task: calculate 30 CFO metrics and upsert into cfo_metrics table.
Runs hourly or on-demand.
"""

import uuid
import logging
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.config import settings
from app.workers.celery_app import celery_app

_sync_engine = create_engine(settings.DATABASE_URL_SYNC, pool_pre_ping=True)


def SessionLocal() -> Session:
    return Session(bind=_sync_engine)

logger = logging.getLogger(__name__)

PROCESSED_STATUSES = "('approved','in_approval','awaiting_match','matched','posted','pending_review')"


def _prev_period(period: str) -> str:
    """Get previous month period string."""
    y, m = int(period[:4]), int(period[5:7])
    d = date(y, m, 1) - relativedelta(months=1)
    return d.strftime("%Y-%m")


def _get_metric_queries(period: str) -> list[tuple[str, str]]:
    """Return list of (metric_key, sql) tuples for the given period."""
    prev = _prev_period(period)

    return [
        # === Invoice Volume & Amounts (1-6) ===
        ("invoice_total_count",
         f"SELECT COUNT(*) FROM invoices WHERE TO_CHAR(created_at, 'YYYY-MM') = '{period}'"),

        ("invoice_processed_count",
         f"SELECT COUNT(*) FROM invoices WHERE TO_CHAR(created_at, 'YYYY-MM') = '{period}' AND status IN {PROCESSED_STATUSES}"),

        ("invoice_unprocessed_count",
         f"SELECT COUNT(*) FROM invoices WHERE TO_CHAR(created_at, 'YYYY-MM') = '{period}' AND status IN ('uploaded','ocr_processing','ocr_done','extracting','error')"),

        ("invoice_rejected_count",
         f"SELECT COUNT(*) FROM invoices WHERE TO_CHAR(created_at, 'YYYY-MM') = '{period}' AND status = 'rejected'"),

        ("invoice_total_gross_amount",
         f"SELECT COALESCE(SUM(gross_amount), 0) FROM invoices WHERE TO_CHAR(created_at, 'YYYY-MM') = '{period}' AND gross_amount IS NOT NULL"),

        ("invoice_processed_gross_amount",
         f"SELECT COALESCE(SUM(gross_amount), 0) FROM invoices WHERE TO_CHAR(created_at, 'YYYY-MM') = '{period}' AND status IN {PROCESSED_STATUSES}"),

        # === Budget Performance (7-10) ===
        ("budget_planned_total",
         f"SELECT COALESCE(SUM(planned_amount), 0) FROM budget_lines WHERE period = '{period}' AND plan_type = 'budget'"),

        ("budget_actual_total",
         f"SELECT COALESCE(SUM(amount), 0) FROM accounting_entries WHERE period = '{period}'"),

        ("budget_variance",
         f"""SELECT COALESCE((SELECT SUM(planned_amount) FROM budget_lines WHERE period = '{period}' AND plan_type = 'budget'), 0)
             - COALESCE((SELECT SUM(amount) FROM accounting_entries WHERE period = '{period}'), 0)"""),

        ("budget_overage_line_count",
         f"""SELECT COUNT(*) FROM (
             SELECT bl.id FROM budget_lines bl
             WHERE bl.period = '{period}' AND bl.plan_type = 'budget'
             AND COALESCE((SELECT SUM(ae.amount) FROM accounting_entries ae
                 WHERE ae.department_id = bl.department_id AND ae.period = bl.period), 0) > bl.planned_amount
         ) sub"""),

        # === Cash Flow Indicators (11-14) ===
        ("overdue_invoice_count",
         f"SELECT COUNT(*) FROM invoices WHERE due_date < CURRENT_DATE AND status NOT IN ('posted','rejected','error')"),

        ("overdue_invoice_amount",
         f"SELECT COALESCE(SUM(gross_amount), 0) FROM invoices WHERE due_date < CURRENT_DATE AND status NOT IN ('posted','rejected','error') AND gross_amount IS NOT NULL"),

        ("upcoming_due_7d_amount",
         f"SELECT COALESCE(SUM(gross_amount), 0) FROM invoices WHERE due_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '7 days' AND status NOT IN ('posted','rejected','error') AND gross_amount IS NOT NULL"),

        ("upcoming_due_30d_amount",
         f"SELECT COALESCE(SUM(gross_amount), 0) FROM invoices WHERE due_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '30 days' AND status NOT IN ('posted','rejected','error') AND gross_amount IS NOT NULL"),

        # === Partner/Supplier Analysis (15-18) ===
        ("top_supplier_amount",
         f"""SELECT COALESCE(MAX(t.total), 0) FROM (
             SELECT SUM(gross_amount) AS total FROM invoices
             WHERE TO_CHAR(created_at, 'YYYY-MM') = '{period}' AND status IN {PROCESSED_STATUSES} AND gross_amount IS NOT NULL
             GROUP BY partner_id
         ) t"""),

        ("active_supplier_count",
         f"SELECT COUNT(DISTINCT partner_id) FROM invoices WHERE TO_CHAR(created_at, 'YYYY-MM') = '{period}' AND partner_id IS NOT NULL AND status IN {PROCESSED_STATUSES}"),

        ("supplier_concentration_top5_pct",
         f"""SELECT CASE WHEN total_all = 0 THEN 0 ELSE ROUND(CAST(top5_sum / total_all * 100 AS NUMERIC), 1) END FROM (
             SELECT
                 COALESCE((SELECT SUM(t.total) FROM (
                     SELECT SUM(gross_amount) AS total FROM invoices
                     WHERE TO_CHAR(created_at, 'YYYY-MM') = '{period}' AND status IN {PROCESSED_STATUSES} AND gross_amount IS NOT NULL
                     GROUP BY partner_id ORDER BY total DESC LIMIT 5
                 ) t), 0) AS top5_sum,
                 COALESCE((SELECT SUM(gross_amount) FROM invoices
                     WHERE TO_CHAR(created_at, 'YYYY-MM') = '{period}' AND status IN {PROCESSED_STATUSES} AND gross_amount IS NOT NULL), 0) AS total_all
         ) sub"""),

        ("avg_invoice_amount",
         f"SELECT COALESCE(AVG(gross_amount), 0) FROM invoices WHERE TO_CHAR(created_at, 'YYYY-MM') = '{period}' AND status IN {PROCESSED_STATUSES} AND gross_amount IS NOT NULL"),

        # === Operational Efficiency (19-22) ===
        ("avg_processing_time_hours",
         f"""SELECT COALESCE(AVG(EXTRACT(EPOCH FROM (approved_at - created_at)) / 3600), 0)
             FROM invoices WHERE approved_at IS NOT NULL AND TO_CHAR(created_at, 'YYYY-MM') = '{period}'"""),

        ("avg_approval_time_hours",
         f"""SELECT COALESCE(AVG(EXTRACT(EPOCH FROM (ia.decided_at - ia.created_at)) / 3600), 0)
             FROM invoice_approvals ia JOIN invoices i ON i.id = ia.invoice_id
             WHERE ia.decided_at IS NOT NULL AND TO_CHAR(i.created_at, 'YYYY-MM') = '{period}'"""),

        ("duplicate_invoice_count",
         f"SELECT COUNT(*) FROM invoices WHERE is_duplicate = TRUE AND TO_CHAR(created_at, 'YYYY-MM') = '{period}'"),

        ("error_rate_pct",
         f"""SELECT CASE WHEN COUNT(*) = 0 THEN 0
             ELSE ROUND(CAST(SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END)::FLOAT / COUNT(*) * 100 AS NUMERIC), 1) END
             FROM invoices WHERE TO_CHAR(created_at, 'YYYY-MM') = '{period}'"""),

        # === P&L Summary (23-25) ===
        ("pnl_revenue",
         f"SELECT COALESCE(SUM(planned_amount), 0) FROM budget_lines WHERE period = '{period}' AND pnl_category = 'revenue' AND plan_type = 'budget'"),

        ("pnl_ebitda",
         f"""SELECT
             COALESCE(SUM(CASE WHEN pnl_category = 'revenue' THEN planned_amount ELSE 0 END), 0)
             - COALESCE(SUM(CASE WHEN pnl_category = 'cogs' THEN planned_amount ELSE 0 END), 0)
             - COALESCE(SUM(CASE WHEN pnl_category = 'opex' THEN planned_amount ELSE 0 END), 0)
             FROM budget_lines WHERE period = '{period}' AND plan_type = 'budget'"""),

        ("pnl_net_income",
         f"""SELECT
             COALESCE(SUM(CASE WHEN pnl_category = 'revenue' THEN planned_amount ELSE 0 END), 0)
             - COALESCE(SUM(CASE WHEN pnl_category IN ('cogs','opex','depreciation','interest','tax') THEN planned_amount ELSE 0 END), 0)
             FROM budget_lines WHERE period = '{period}' AND plan_type = 'budget'"""),

        # === Department Spending (26-27) ===
        ("dept_highest_spend_amount",
         f"""SELECT COALESCE(MAX(dept_total), 0) FROM (
             SELECT SUM(ae.amount) AS dept_total FROM accounting_entries ae
             WHERE ae.period = '{period}' GROUP BY ae.department_id
         ) sub"""),

        ("dept_count_over_budget",
         f"""SELECT COUNT(*) FROM (
             SELECT d.id,
                 COALESCE(SUM(bl.planned_amount), 0) AS planned,
                 COALESCE((SELECT SUM(ae.amount) FROM accounting_entries ae WHERE ae.department_id = d.id AND ae.period = '{period}'), 0) AS actual
             FROM departments d
             LEFT JOIN budget_lines bl ON bl.department_id = d.id AND bl.period = '{period}' AND bl.plan_type = 'budget'
             GROUP BY d.id
             HAVING COALESCE((SELECT SUM(ae.amount) FROM accounting_entries ae WHERE ae.department_id = d.id AND ae.period = '{period}'), 0) > COALESCE(SUM(bl.planned_amount), 0) AND COALESCE(SUM(bl.planned_amount), 0) > 0
         ) sub"""),

        # === Purchase Order Metrics (28-29) ===
        ("po_open_count",
         f"SELECT COUNT(*) FROM purchase_orders WHERE status IN ('draft','approved','received')"),

        ("po_open_amount",
         f"SELECT COALESCE(SUM(amount), 0) FROM purchase_orders WHERE status IN ('draft','approved','received')"),

        # === Trend Indicators (30) ===
        ("invoice_amount_mom_change_pct",
         f"""SELECT CASE WHEN prev_amount = 0 THEN 0 ELSE ROUND(CAST((curr_amount - prev_amount) / NULLIF(ABS(prev_amount), 0) * 100 AS NUMERIC), 1) END FROM (
             SELECT
                 COALESCE((SELECT SUM(gross_amount) FROM invoices WHERE TO_CHAR(created_at, 'YYYY-MM') = '{period}' AND status IN {PROCESSED_STATUSES} AND gross_amount IS NOT NULL), 0) AS curr_amount,
                 COALESCE((SELECT SUM(gross_amount) FROM invoices WHERE TO_CHAR(created_at, 'YYYY-MM') = '{prev}' AND status IN {PROCESSED_STATUSES} AND gross_amount IS NOT NULL), 0) AS prev_amount
         ) sub"""),
    ]


def _upsert_metric(db: Session, metric_key: str, period: str, value: float) -> None:
    """Upsert a metric value into cfo_metrics table."""
    now = datetime.utcnow()
    db.execute(text("""
        INSERT INTO cfo_metrics (id, metric_key, period, value, currency, calculated_at)
        VALUES (:id, :key, :period, :value, 'HUF', :now)
        ON CONFLICT (metric_key, period)
        DO UPDATE SET value = :value, calculated_at = :now
    """), {"id": str(uuid.uuid4()), "key": metric_key, "period": period, "value": value, "now": now})


@celery_app.task(name="calculate_cfo_metrics")
def calculate_cfo_metrics(period: str | None = None):
    """Calculate all 30 CFO metrics for the given period (default: current month)."""
    if period is None:
        period = date.today().strftime("%Y-%m")

    logger.info("Calculating CFO metrics for period %s", period)
    db = SessionLocal()

    try:
        queries = _get_metric_queries(period)
        success_count = 0

        for metric_key, sql in queries:
            try:
                result = db.execute(text(sql))
                row = result.fetchone()
                value = float(row[0]) if row and row[0] is not None else 0.0
                _upsert_metric(db, metric_key, period, value)
                success_count += 1
            except Exception as e:
                logger.error("Failed to calculate %s: %s", metric_key, str(e)[:200])
                db.rollback()

        db.commit()
        logger.info("CFO metrics calculated: %d/%d for period %s", success_count, len(queries), period)
        return {"period": period, "success": success_count, "total": len(queries)}

    except Exception as e:
        db.rollback()
        logger.exception("CFO metrics calculation failed")
        raise
    finally:
        db.close()
