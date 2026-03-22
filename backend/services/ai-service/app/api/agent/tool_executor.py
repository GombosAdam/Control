import logging
import re
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.agent.http_client import service_client
from app.api.chat.service import validate_sql, _execute_sql

logger = logging.getLogger(__name__)

_SAFE_IDENT_RE = re.compile(r"[^a-zA-ZáéíóöőúüűÁÉÍÓÖŐÚÜŰ0-9 _\-.]")
_SAFE_PERIOD_RE = re.compile(r"^\d{4}-\d{2}$")
_VALID_PNL_CATEGORIES = {"revenue", "cogs", "opex", "depreciation", "interest", "tax"}


def _sanitize_name(value: str) -> str:
    """Strip SQL-dangerous characters from a name/identifier input."""
    return _SAFE_IDENT_RE.sub("", value).strip()[:100]


def _sanitize_period(value: str) -> str | None:
    """Validate period format YYYY-MM. Returns None if invalid."""
    value = value.strip()[:7]
    if _SAFE_PERIOD_RE.match(value):
        return value
    return None


def _huf(value: float | int) -> str:
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:,.1f}M Ft".replace(",", " ")
    if abs(value) >= 1_000:
        return f"{int(value):,} Ft".replace(",", " ")
    return f"{int(value)} Ft"


async def execute_tool(tool_name: str, arguments: dict, token: str, db: AsyncSession) -> str:
    """Execute a tool call and return a text result for the LLM."""
    try:
        match tool_name:
            case "get_budget_summary":
                return await _budget_summary(arguments, token)
            case "get_invoice_stats":
                return await _invoice_stats(arguments, token)
            case "get_partner_detail":
                return await _partner_detail(arguments, token)
            case "get_anomalies":
                return await _anomalies(arguments, token)
            case "get_cash_position":
                return await _cash_position(arguments, token)
            case "search_history":
                return await _search_history(arguments)
            case "execute_sql":
                return await _execute_sql_tool(arguments, db)
            case "get_forecast":
                return await _forecast(db)
            case "simulate_scenario":
                return await _simulate_scenario(arguments, db)
            case "get_yoy_comparison":
                return await _yoy_comparison(arguments, db)
            case "get_approval_bottleneck":
                return await _approval_bottleneck(arguments, db)
            case "get_supplier_risk":
                return await _supplier_risk(arguments, db)
            case _:
                return f"Ismeretlen tool: {tool_name}"
    except Exception as e:
        logger.exception("Tool execution error: %s", tool_name)
        return f"Hiba a(z) {tool_name} tool futtatásakor: {str(e)[:300]}"


async def _budget_summary(args: dict, token: str) -> str:
    params: dict = {}
    dept_name = args.get("department")

    if dept_name:
        depts = await service_client.finance("/api/v1/departments/", token=token)
        match = next(
            (d for d in depts if dept_name.lower() in d["name"].lower()),
            None,
        )
        if match:
            params["department_id"] = match["id"]
        else:
            return f"Nem találtam '{dept_name}' nevű osztályt."

    data = await service_client.finance(
        "/api/v1/controlling/budget-status", params=params, token=token
    )

    if not data:
        return "Nincs elérhető budget adat."

    lines = ["Budget státusz:"]
    for dept in data:
        lines.append(
            f"- {dept.get('department_name', '?')}: "
            f"terv {_huf(dept.get('planned', 0))}, "
            f"elkötött {_huf(dept.get('committed', 0))}, "
            f"tényleges {_huf(dept.get('spent', 0))}, "
            f"szabad {_huf(dept.get('available', 0))}, "
            f"kihasználtság {dept.get('utilization_pct', 0)}%"
        )
    return "\n".join(lines)


async def _invoice_stats(args: dict, token: str) -> str:
    stats = await service_client.finance(
        "/api/v1/dashboard/stats", token=token
    )
    processing = await service_client.finance(
        "/api/v1/dashboard/processing-status", token=token
    )

    lines = ["Számla statisztikák:"]

    if isinstance(stats, dict):
        for key, val in stats.items():
            lines.append(f"- {key}: {val}")

    if isinstance(processing, (list, dict)):
        lines.append("Feldolgozási státusz:")
        if isinstance(processing, list):
            for item in processing:
                lines.append(
                    f"- {item.get('status', '?')}: {item.get('count', 0)} db"
                )
        elif isinstance(processing, dict):
            for key, val in processing.items():
                lines.append(f"- {key}: {val}")

    status_filter = args.get("status")
    partner_filter = args.get("partner")
    if status_filter:
        lines.append(f"(Szűrve státuszra: {status_filter})")
    if partner_filter:
        lines.append(f"(Szűrve partnerre: {partner_filter})")

    return "\n".join(lines)


async def _partner_detail(args: dict, token: str) -> str:
    name_or_id = args.get("name_or_id", "")
    if not name_or_id:
        return "Hiányzó partner név vagy ID."

    # Search for partner
    partners = await service_client.pipeline(
        "/api/v1/partners", params={"search": name_or_id}, token=token
    )

    if not partners:
        return f"Nem találtam partnert: '{name_or_id}'"

    partner = partners[0] if isinstance(partners, list) else partners
    partner_id = partner.get("id", "")
    partner_name = partner.get("name", name_or_id)

    lines = [f"Partner: {partner_name}"]
    if partner.get("tax_id"):
        lines.append(f"Adószám: {partner['tax_id']}")

    # Fetch invoices
    try:
        invoices = await service_client.pipeline(
            f"/api/v1/partners/{partner_id}/invoices", token=token
        )
        if isinstance(invoices, list):
            total_amount = sum(inv.get("total_amount", 0) for inv in invoices)
            lines.append(f"Számlák száma: {len(invoices)}")
            lines.append(f"Összes összeg: {_huf(total_amount)}")
            for inv in invoices[:10]:
                lines.append(
                    f"  - {inv.get('invoice_number', '?')}: "
                    f"{_huf(inv.get('total_amount', 0))} "
                    f"({inv.get('status', '?')})"
                )
            if len(invoices) > 10:
                lines.append(f"  ... és még {len(invoices) - 10} számla")
    except Exception:
        lines.append("(Számla részletek nem elérhetők)")

    return "\n".join(lines)


async def _anomalies(args: dict, token: str) -> str:
    lines = ["Anomáliák és figyelmeztetések:"]

    try:
        alerts = await service_client.finance(
            "/api/v1/dashboard/cfo-alerts", token=token
        )
        severity_filter = args.get("severity")
        if isinstance(alerts, list):
            for alert in alerts:
                sev = alert.get("severity", "info")
                if severity_filter and sev != severity_filter:
                    continue
                icon = "🔴" if sev == "critical" else "🟡"
                lines.append(f"  {icon} [{sev}] {alert.get('message', '?')}")
    except Exception:
        lines.append("(CFO riasztások nem elérhetők)")

    try:
        duplicates = await service_client.pipeline(
            "/api/v1/extraction/duplicates", token=token
        )
        if isinstance(duplicates, list) and duplicates:
            lines.append(f"Duplikált gyanús számlák: {len(duplicates)} db")
            for dup in duplicates[:5]:
                lines.append(
                    f"  - {dup.get('invoice_number', '?')}: "
                    f"{dup.get('reason', '?')}"
                )
    except Exception:
        lines.append("(Duplikát adatok nem elérhetők)")

    if len(lines) == 1:
        lines.append("Nincs aktív anomália.")

    return "\n".join(lines)


async def _cash_position(args: dict, token: str) -> str:
    params: dict = {}
    dept_name = args.get("department")
    period = args.get("period")

    if dept_name:
        depts = await service_client.finance("/api/v1/departments/", token=token)
        match = next(
            (d for d in depts if dept_name.lower() in d["name"].lower()),
            None,
        )
        if match:
            params["department_id"] = match["id"]

    if period:
        params["period"] = period

    data = await service_client.finance(
        "/api/v1/controlling/ebitda", params=params, token=token
    )

    if not data:
        return "Nincs elérhető EBITDA / pénzügyi adat."

    lines = ["Pénzügyi helyzet:"]
    if isinstance(data, list):
        for item in data:
            lines.append(
                f"- {item.get('department_name', '?')}: "
                f"tervezett budget {_huf(item.get('planned_budget', 0))}, "
                f"tényleges költés {_huf(item.get('actual_cost', 0))}, "
                f"EBITDA {_huf(item.get('ebitda', 0))}, "
                f"margin {item.get('margin_pct', 0)}%"
            )
    elif isinstance(data, dict):
        lines.append(f"Tervezett budget: {_huf(data.get('planned_budget', 0))}")
        lines.append(f"Tényleges költés: {_huf(data.get('actual_cost', 0))}")
        lines.append(f"EBITDA: {_huf(data.get('ebitda', 0))}")
        if data.get("margin_pct") is not None:
            lines.append(f"Margin: {data['margin_pct']}%")

    return "\n".join(lines)


async def _search_history(args: dict) -> str:
    topic = args.get("topic", "")
    if not topic:
        return "Hiányzó keresési téma."

    try:
        from common.config import settings
        from common.vectorstore import VectorStoreManager

        vs = VectorStoreManager(
            qdrant_url=settings.QDRANT_URL,
            ollama_url=settings.OLLAMA_URL,
            embed_model=settings.EMBEDDING_MODEL,
        )
        results = vs.search(
            collection="text2sql_examples",
            text=topic,
            top_k=3,
            min_score=settings.RAG_MIN_SCORE,
        )
        vs.close()

        if not results:
            return f"Nincs korábbi hasonló kérdés a(z) '{topic}' témában."

        lines = [f"Korábbi hasonló kérdések ({len(results)} találat):"]
        for r in results:
            q = r["payload"].get("question", "?")
            sql = r["payload"].get("sql", "?")
            score = r.get("score", 0)
            lines.append(f"- [{score:.0%}] \"{q}\"")
            lines.append(f"  SQL: {sql[:150]}")
        return "\n".join(lines)
    except Exception as e:
        logger.debug("Search history failed: %s", e)
        return f"Keresési hiba: {str(e)[:200]}"


async def _execute_sql_tool(args: dict, db: AsyncSession) -> str:
    query = args.get("query", "")
    if not query:
        return "Hiányzó SQL lekérdezés."

    validation_error = validate_sql(query)
    if validation_error:
        return f"SQL validációs hiba: {validation_error}"

    try:
        rows, row_count = await _execute_sql(db, query)
    except Exception as e:
        return f"SQL futtatási hiba: {str(e)[:300]}"

    if row_count == 0:
        return "A lekérdezés nem adott vissza eredményt."

    lines = [f"SQL eredmény ({row_count} sor):"]
    for i, row in enumerate(rows[:20]):
        parts = [f"{k}={v}" for k, v in row.items()]
        lines.append(f"  {i + 1}. {', '.join(parts)}")
    if row_count > 20:
        lines.append(f"  ... és még {row_count - 20} további sor")

    return "\n".join(lines)


# === F1: Cash Flow Forecast ===

async def _forecast(db: AsyncSession) -> str:
    period = datetime.now().strftime("%Y-%m")
    forecast_keys = [
        "forecast_cash_in_30d", "forecast_cash_in_60d", "forecast_cash_in_90d",
        "forecast_cash_out_30d", "forecast_cash_out_60d", "forecast_cash_out_90d",
        "forecast_net_cash_30d", "forecast_net_cash_60d", "forecast_net_cash_90d",
    ]
    keys_sql = ", ".join(f"'{k}'" for k in forecast_keys)
    try:
        rows, _ = await _execute_sql(
            db,
            f"SELECT metric_key, value FROM cfo_metrics WHERE period = '{period}' AND metric_key IN ({keys_sql})",
        )
    except Exception as e:
        return f"Hiba az előrejelzés lekérdezésekor: {str(e)[:200]}"

    m = {r["metric_key"]: r["value"] for r in rows}

    lines = [f"Cash flow előrejelzés ({period}):"]
    lines.append("")
    lines.append("Várható bevétel (cash in):")
    lines.append(f"  30 nap: {_huf(m.get('forecast_cash_in_30d', 0))}")
    lines.append(f"  60 nap: {_huf(m.get('forecast_cash_in_60d', 0))}")
    lines.append(f"  90 nap: {_huf(m.get('forecast_cash_in_90d', 0))}")
    lines.append("")
    lines.append("Várható kiadás (cash out):")
    lines.append(f"  30 nap: {_huf(m.get('forecast_cash_out_30d', 0))}")
    lines.append(f"  60 nap: {_huf(m.get('forecast_cash_out_60d', 0))}")
    lines.append(f"  90 nap: {_huf(m.get('forecast_cash_out_90d', 0))}")
    lines.append("")
    lines.append("Nettó cash flow:")
    lines.append(f"  30 nap: {_huf(m.get('forecast_net_cash_30d', 0))}")
    lines.append(f"  60 nap: {_huf(m.get('forecast_net_cash_60d', 0))}")
    lines.append(f"  90 nap: {_huf(m.get('forecast_net_cash_90d', 0))}")

    if all(m.get(k, 0) == 0 for k in forecast_keys):
        lines.append("")
        lines.append("⚠ Az előrejelzés 0, mert nincs elegendő historikus adat.")

    return "\n".join(lines)


# === F2: What-If Scenario Simulation ===

async def _simulate_scenario(args: dict, db: AsyncSession) -> str:
    dept_name = _sanitize_name(args.get("department", ""))
    change_pct = args.get("budget_change_pct", 0)
    pnl_cat = args.get("pnl_category")

    if not dept_name:
        return "Hiányzó osztály név."

    if pnl_cat and pnl_cat not in _VALID_PNL_CATEGORIES:
        return f"Érvénytelen P&L kategória: '{pnl_cat}'"

    period = datetime.now().strftime("%Y-%m")

    # Get department budget lines (read-only via _execute_sql)
    pnl_filter = f"AND bl.pnl_category = '{pnl_cat}'" if pnl_cat else ""
    try:
        budget_rows, _ = await _execute_sql(db, f"""
            SELECT bl.pnl_category, SUM(bl.planned_amount) AS planned
            FROM budget_lines bl
            JOIN departments d ON d.id = bl.department_id
            WHERE LOWER(d.name) LIKE LOWER('%{dept_name}%')
              AND bl.period = '{period}' AND bl.plan_type = 'budget'
              {pnl_filter}
            GROUP BY bl.pnl_category
        """)
    except Exception as e:
        return f"Hiba a budget lekérdezésekor: {str(e)[:200]}"

    if not budget_rows:
        return f"Nincs budget adat a(z) '{dept_name}' osztályra ({period})."

    # Get actual spend
    try:
        actual_rows, _ = await _execute_sql(db, f"""
            SELECT COALESCE(SUM(ae.amount), 0) AS actual
            FROM accounting_entries ae
            JOIN departments d ON d.id = ae.department_id
            WHERE LOWER(d.name) LIKE LOWER('%{dept_name}%') AND ae.period = '{period}'
        """)
    except Exception as e:
        return f"Hiba a tényleges költés lekérdezésekor: {str(e)[:200]}"

    actual_spend = actual_rows[0]["actual"] if actual_rows else 0

    # Calculate current and simulated values
    total_planned = sum(r["planned"] for r in budget_rows)
    multiplier = 1 + (change_pct / 100)
    new_planned = total_planned * multiplier
    delta = new_planned - total_planned

    # Simplified P&L impact
    revenue = sum(r["planned"] for r in budget_rows if r["pnl_category"] == "revenue")
    costs = sum(r["planned"] for r in budget_rows if r["pnl_category"] != "revenue")
    new_revenue = revenue * multiplier if pnl_cat in (None, "revenue") else revenue
    new_costs = costs * multiplier if pnl_cat != "revenue" else costs

    current_margin = revenue - costs
    new_margin = new_revenue - new_costs

    lines = [f"What-if szimuláció: {dept_name} budget {change_pct:+.0f}%"]
    if pnl_cat:
        lines[0] += f" ({pnl_cat})"
    lines.append(f"Periódus: {period}")
    lines.append("")
    lines.append("Jelenlegi állapot:")
    lines.append(f"  Tervezett budget: {_huf(total_planned)}")
    lines.append(f"  Tényleges költés: {_huf(actual_spend)}")
    lines.append(f"  Margin (bevétel-költség): {_huf(current_margin)}")
    lines.append("")
    lines.append("Szimulált állapot:")
    lines.append(f"  Új tervezett budget: {_huf(new_planned)} ({change_pct:+.0f}%)")
    lines.append(f"  Budget delta: {_huf(delta)}")
    lines.append(f"  Új margin: {_huf(new_margin)}")
    lines.append(f"  Margin változás: {_huf(new_margin - current_margin)}")
    lines.append("")

    for r in budget_rows:
        cat = r["pnl_category"]
        orig = r["planned"]
        if pnl_cat is None or pnl_cat == cat:
            new_val = orig * multiplier
        else:
            new_val = orig
        lines.append(f"  {cat}: {_huf(orig)} → {_huf(new_val)}")

    return "\n".join(lines)


# === F3: YoY Comparison ===

async def _yoy_comparison(args: dict, db: AsyncSession) -> str:
    raw_period = args.get("period")
    if raw_period:
        period = _sanitize_period(raw_period)
        if not period:
            return f"Érvénytelen periódus formátum: '{raw_period}'. Használd: YYYY-MM"
    else:
        period = datetime.now().strftime("%Y-%m")
    dept_name = _sanitize_name(args.get("department", "")) if args.get("department") else None

    y, m_val = int(period[:4]), int(period[5:7])
    yoy_period = f"{y - 1}-{m_val:02d}"

    if dept_name:
        # Department-level YoY via SQL
        try:
            rows, _ = await _execute_sql(db, f"""
                SELECT
                    COALESCE(SUM(CASE WHEN bl.period = '{period}' THEN bl.planned_amount ELSE 0 END), 0) AS curr_revenue,
                    COALESCE(SUM(CASE WHEN bl.period = '{yoy_period}' THEN bl.planned_amount ELSE 0 END), 0) AS prev_revenue
                FROM budget_lines bl
                JOIN departments d ON d.id = bl.department_id
                WHERE LOWER(d.name) LIKE LOWER('%{dept_name}%')
                  AND bl.pnl_category = 'revenue' AND bl.plan_type = 'budget'
                  AND bl.period IN ('{period}', '{yoy_period}')
            """)
            actual_rows, _ = await _execute_sql(db, f"""
                SELECT
                    COALESCE(SUM(CASE WHEN ae.period = '{period}' THEN ae.amount ELSE 0 END), 0) AS curr_expense,
                    COALESCE(SUM(CASE WHEN ae.period = '{yoy_period}' THEN ae.amount ELSE 0 END), 0) AS prev_expense
                FROM accounting_entries ae
                JOIN departments d ON d.id = ae.department_id
                WHERE LOWER(d.name) LIKE LOWER('%{dept_name}%')
                  AND ae.period IN ('{period}', '{yoy_period}')
            """)
        except Exception as e:
            return f"Hiba a YoY lekérdezésekor: {str(e)[:200]}"

        r = rows[0] if rows else {}
        a = actual_rows[0] if actual_rows else {}
        curr_rev, prev_rev = r.get("curr_revenue", 0), r.get("prev_revenue", 0)
        curr_exp, prev_exp = a.get("curr_expense", 0), a.get("prev_expense", 0)

        def _pct(curr, prev):
            if prev == 0:
                return "n/a"
            return f"{(curr - prev) / abs(prev) * 100:+.1f}%"

        lines = [f"YoY összehasonlítás: {dept_name} ({period} vs {yoy_period})"]
        lines.append(f"  Bevétel: {_huf(curr_rev)} vs {_huf(prev_rev)} ({_pct(curr_rev, prev_rev)})")
        lines.append(f"  Kiadás: {_huf(curr_exp)} vs {_huf(prev_exp)} ({_pct(curr_exp, prev_exp)})")
        return "\n".join(lines)

    # Global YoY from cfo_metrics
    yoy_keys = [
        "revenue_yoy_change_pct", "expense_yoy_change_pct",
        "ebitda_yoy_change_pct", "invoice_count_yoy_change_pct",
    ]
    keys_sql = ", ".join(f"'{k}'" for k in yoy_keys)
    try:
        rows, _ = await _execute_sql(
            db,
            f"SELECT metric_key, value FROM cfo_metrics WHERE period = '{period}' AND metric_key IN ({keys_sql})",
        )
    except Exception as e:
        return f"Hiba a YoY lekérdezésekor: {str(e)[:200]}"

    m = {r["metric_key"]: r["value"] for r in rows}

    lines = [f"YoY összehasonlítás ({period} vs {yoy_period}):"]
    lines.append(f"  Bevétel változás: {m.get('revenue_yoy_change_pct', 0):+.1f}%")
    lines.append(f"  Kiadás változás: {m.get('expense_yoy_change_pct', 0):+.1f}%")
    lines.append(f"  EBITDA változás: {m.get('ebitda_yoy_change_pct', 0):+.1f}%")
    lines.append(f"  Számla darabszám változás: {m.get('invoice_count_yoy_change_pct', 0):+.1f}%")

    if all(m.get(k, 0) == 0 for k in yoy_keys):
        lines.append("")
        lines.append("⚠ Nincs előző évi adat az összehasonlításhoz.")

    return "\n".join(lines)


# === F4: Approval Bottleneck ===

async def _approval_bottleneck(args: dict, db: AsyncSession) -> str:
    raw_period = args.get("period")
    period = None
    if raw_period:
        period = _sanitize_period(raw_period)
        if not period:
            return f"Érvénytelen periódus formátum: '{raw_period}'. Használd: YYYY-MM"
    period_filter = f"AND TO_CHAR(i.created_at, 'YYYY-MM') = '{period}'" if period else ""

    lines = ["Jóváhagyási bottleneck elemzés:"]

    # 1. Average time per step/role
    try:
        rows, _ = await _execute_sql(db, f"""
            SELECT ia.step_name, ia.assigned_role,
                   ROUND(AVG(EXTRACT(EPOCH FROM (ia.decided_at - ia.created_at)) / 3600)::NUMERIC, 1) AS avg_hours,
                   COUNT(*) AS decisions
            FROM invoice_approvals ia
            JOIN invoices i ON i.id = ia.invoice_id
            WHERE ia.decided_at IS NOT NULL {period_filter}
            GROUP BY ia.step_name, ia.assigned_role
            ORDER BY avg_hours DESC
        """)
        if rows:
            lines.append("")
            lines.append("Átlagos döntési idő lépésenként:")
            for r in rows:
                lines.append(
                    f"  {r['step_name']} ({r['assigned_role']}): "
                    f"{r['avg_hours']} óra ({r['decisions']} döntés)"
                )
        else:
            lines.append("  Nincs jóváhagyási adat.")
    except Exception as e:
        lines.append(f"  Hiba: {str(e)[:100]}")

    # 2. Top 5 slowest decision makers
    try:
        rows, _ = await _execute_sql(db, f"""
            SELECT u.full_name, ia.step_name,
                   ROUND(AVG(EXTRACT(EPOCH FROM (ia.decided_at - ia.created_at)) / 3600)::NUMERIC, 1) AS avg_hours,
                   COUNT(*) AS decisions
            FROM invoice_approvals ia
            JOIN invoices i ON i.id = ia.invoice_id
            JOIN users u ON u.id = ia.decided_by
            WHERE ia.decided_at IS NOT NULL {period_filter}
            GROUP BY u.full_name, ia.step_name
            ORDER BY avg_hours DESC
            LIMIT 5
        """)
        if rows:
            lines.append("")
            lines.append("Top 5 leglassabb döntéshozó:")
            for i, r in enumerate(rows, 1):
                lines.append(
                    f"  {i}. {r['full_name']} ({r['step_name']}): "
                    f"{r['avg_hours']} óra átlag ({r['decisions']} döntés)"
                )
    except Exception as e:
        lines.append(f"  Hiba: {str(e)[:100]}")

    # 3. Pending approvals by step
    try:
        rows, _ = await _execute_sql(db, """
            SELECT ia.step_name, ia.assigned_role, COUNT(*) AS pending_count
            FROM invoice_approvals ia
            WHERE ia.status = 'pending'
            GROUP BY ia.step_name, ia.assigned_role
            ORDER BY pending_count DESC
        """)
        if rows:
            lines.append("")
            lines.append("Függő jóváhagyások:")
            total_pending = 0
            for r in rows:
                total_pending += r["pending_count"]
                lines.append(
                    f"  {r['step_name']} ({r['assigned_role']}): {r['pending_count']} db"
                )
            lines.append(f"  Összesen: {total_pending} db függő")
        else:
            lines.append("")
            lines.append("Nincs függő jóváhagyás.")
    except Exception as e:
        lines.append(f"  Hiba: {str(e)[:100]}")

    return "\n".join(lines)


# === F6: Supplier Risk ===

async def _supplier_risk(args: dict, db: AsyncSession) -> str:
    supplier_name = _sanitize_name(args.get("supplier", "")) if args.get("supplier") else None
    period = datetime.now().strftime("%Y-%m")

    if supplier_name:
        # Single supplier analysis
        try:
            rows, _ = await _execute_sql(db, f"""
                SELECT p.name,
                       COUNT(i.id) AS invoice_count,
                       COALESCE(SUM(i.gross_amount), 0) AS total_amount,
                       ROUND(AVG(EXTRACT(DAY FROM (i.approved_at - i.invoice_date)))::NUMERIC, 0) AS avg_pay_days,
                       COALESCE(AVG(i.gross_amount), 0) AS avg_amount
                FROM invoices i
                JOIN partners p ON p.id = i.partner_id
                WHERE LOWER(p.name) LIKE LOWER('%{supplier_name}%')
                  AND i.gross_amount IS NOT NULL
                GROUP BY p.name
            """)
        except Exception as e:
            return f"Hiba a szállítói lekérdezésekor: {str(e)[:200]}"

        if not rows:
            return f"Nem találtam szállítót: '{supplier_name}'"

        r = rows[0]
        lines = [f"Szállítói elemzés: {r['name']}"]
        lines.append(f"  Számlák száma: {r['invoice_count']}")
        lines.append(f"  Összes összeg: {_huf(r['total_amount'])}")
        lines.append(f"  Átlagos fizetési idő: {r['avg_pay_days'] or 'n/a'} nap")
        lines.append(f"  Átlagos számla összeg: {_huf(r['avg_amount'])}")
        return "\n".join(lines)

    # Global supplier risk from metrics
    risk_keys = ["avg_payment_days", "supplier_dependency_risk_count", "supplier_price_trend_pct"]
    keys_sql = ", ".join(f"'{k}'" for k in risk_keys)
    try:
        rows, _ = await _execute_sql(
            db,
            f"SELECT metric_key, value FROM cfo_metrics WHERE period = '{period}' AND metric_key IN ({keys_sql})",
        )
    except Exception as e:
        return f"Hiba a szállítói kockázat lekérdezésekor: {str(e)[:200]}"

    m = {r["metric_key"]: r["value"] for r in rows}

    avg_days = m.get("avg_payment_days", 0)
    dep_count = int(m.get("supplier_dependency_risk_count", 0))
    price_trend = m.get("supplier_price_trend_pct", 0)

    lines = ["Szállítói kockázat elemzés:"]
    lines.append(f"  Átlagos fizetési napok: {avg_days:.0f} nap")
    lines.append(f"  Magas függőségű szállítók (>20% részesedés): {dep_count} db")
    lines.append(f"  Átlagos ár trend (YoY): {price_trend:+.1f}%")

    # Risk assessment
    risks = []
    if avg_days > 30:
        risks.append(f"⚠ Magas átlagos fizetési idő ({avg_days:.0f} nap)")
    if dep_count > 0:
        risks.append(f"⚠ {dep_count} szállítótól való magas függőség")
    if abs(price_trend) > 10:
        direction = "emelkedő" if price_trend > 0 else "csökkenő"
        risks.append(f"⚠ Jelentős {direction} ártendencia ({price_trend:+.1f}%)")

    if risks:
        lines.append("")
        lines.append("Kockázati jelzések:")
        for r in risks:
            lines.append(f"  {r}")
    else:
        lines.append("")
        lines.append("✓ Nincs kiemelt kockázat.")

    return "\n".join(lines)
