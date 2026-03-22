import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.agent.http_client import service_client
from app.api.chat.service import validate_sql, _execute_sql

logger = logging.getLogger(__name__)


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
