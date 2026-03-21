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

    if row_count <= 50:
        # Multiple rows — markdown table
        return _build_table(results)

    # Too many rows or too complex
    return None


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
