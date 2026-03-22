"""
Code-based answer formatting for chat responses.
Deterministic, ~0ms — no LLM call needed for standard cases.
"""

from datetime import date, datetime
from typing import Any


def format_answer(question: str, results: list[dict], row_count: int) -> str | None:
    """
    Format query results into a human-readable Hungarian answer.
    Returns None if the result is too complex for code-based formatting (triggers LLM fallback).
    """
    if row_count == 0:
        return "A lekérdezés nem adott vissza eredményt."

    if row_count == 1 and len(results[0]) == 1:
        # Single value result (COUNT, SUM, AVG, etc.)
        col_name = list(results[0].keys())[0]
        value = results[0][col_name]
        return _format_single_value(col_name, value)

    if row_count == 1 and len(results[0]) <= 6:
        # Single row, multiple columns — bullet list
        lines = []
        for key, value in results[0].items():
            formatted = _format_value(value)
            label = key.replace("_", " ").capitalize()
            lines.append(f"- **{label}**: {formatted}")
        return "\n".join(lines)

    # Multiple rows — markdown table (cap at 100 rows)
    return _build_table(results[:100])


def _format_single_value(col_name: str, value: Any) -> str:
    """Format a single aggregate value with context from column name."""
    if value is None:
        return "Az eredmény: nincs adat (NULL)."

    col_lower = col_name.lower()

    if isinstance(value, (int, float)):
        formatted = _format_number(value)
        # Detect if it's a monetary amount
        is_money = any(
            kw in col_lower
            for kw in ["osszeg", "brutto", "netto", "amount", "koltes", "terv", "teny", "elteres"]
        )
        if is_money:
            return f"{formatted} Ft"

        # Detect if it's a count
        is_count = any(
            kw in col_lower
            for kw in ["db", "count", "szamla_db", "partner_db"]
        )
        if is_count:
            return f"{formatted}"

        return f"{formatted}"

    return str(value)


def _format_number(value: Any) -> str:
    """Format number with Hungarian convention (space as thousands separator)."""
    if value is None:
        return "—"

    if isinstance(value, float):
        if value == int(value):
            return f"{int(value):,}".replace(",", " ")
        return f"{value:,.2f}".replace(",", " ").replace(".", ",")

    if isinstance(value, int):
        return f"{value:,}".replace(",", " ")

    return str(value)


def _format_value(value: Any) -> str:
    """Format any value for display."""
    if value is None:
        return "—"

    if isinstance(value, (int, float)):
        return _format_number(value)

    if isinstance(value, date):
        return _format_date(value)

    if isinstance(value, datetime):
        return _format_date(value)

    return str(value)


def _format_date(value: date | datetime) -> str:
    """Format date in Hungarian style."""
    months = [
        "", "január", "február", "március", "április", "május", "június",
        "július", "augusztus", "szeptember", "október", "november", "december",
    ]
    if isinstance(value, datetime):
        return f"{value.year}. {months[value.month]} {value.day}."
    return f"{value.year}. {months[value.month]} {value.day}."


_TIME_KEYWORDS = {"period", "honap", "datum", "date", "month", "year", "ev", "het", "week", "quarter"}
_CATEGORY_KEYWORDS = {"name", "nev", "osztaly", "department", "partner", "status", "kategoria", "category", "step_name", "role"}


def detect_chart_data(question: str, results: list[dict], row_count: int) -> dict | None:
    """
    Detect if results are suitable for chart visualization.
    Returns chart_data dict or None.
    """
    if row_count < 2 or not results:
        return None

    headers = list(results[0].keys())
    if len(headers) < 2:
        return None

    first_col = headers[0].lower()
    # Find numeric columns
    numeric_cols = [
        h for h in headers
        if any(isinstance(r.get(h), (int, float)) for r in results if r.get(h) is not None)
    ]
    if not numeric_cols:
        return None

    labels = [str(r.get(headers[0], "")) for r in results]

    # Time-series → line chart
    if first_col in _TIME_KEYWORDS or any(kw in first_col for kw in _TIME_KEYWORDS):
        datasets = []
        for col in numeric_cols:
            if col == headers[0]:
                continue
            datasets.append({
                "label": col.replace("_", " ").capitalize(),
                "data": [r.get(col, 0) or 0 for r in results],
            })
        if datasets:
            return {"type": "line", "labels": labels, "datasets": datasets}

    # Category + number → bar chart
    if first_col in _CATEGORY_KEYWORDS or any(kw in first_col for kw in _CATEGORY_KEYWORDS):
        datasets = []
        for col in numeric_cols:
            if col == headers[0]:
                continue
            datasets.append({
                "label": col.replace("_", " ").capitalize(),
                "data": [r.get(col, 0) or 0 for r in results],
            })
        if datasets:
            return {"type": "bar", "labels": labels, "datasets": datasets}

    # Small result set with label + single count → pie chart
    if row_count <= 10 and len(numeric_cols) == 1:
        num_col = numeric_cols[0]
        if num_col != headers[0]:
            return {
                "type": "pie",
                "labels": labels,
                "datasets": [{
                    "label": num_col.replace("_", " ").capitalize(),
                    "data": [r.get(num_col, 0) or 0 for r in results],
                }],
            }

    return None


def _build_table(results: list[dict]) -> str:
    """Build a markdown table from query results."""
    if not results:
        return "Nincs adat."

    headers = list(results[0].keys())
    labels = [h.replace("_", " ").capitalize() for h in headers]

    # Header row
    header_line = "| " + " | ".join(labels) + " |"
    separator = "| " + " | ".join("---" for _ in headers) + " |"

    # Data rows
    rows = []
    for row in results:
        cells = []
        for h in headers:
            cells.append(_format_value(row.get(h)))
        rows.append("| " + " | ".join(cells) + " |")

    return "\n".join([header_line, separator] + rows)
