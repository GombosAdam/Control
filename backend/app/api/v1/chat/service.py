import json
import logging
import re
import time
import uuid

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.api.v1.chat.formatter import format_answer
from app.api.v1.chat.schemas import ChatResponse
from app.api.v1.chat.semantic_schema import DDL_SCHEMA, BUSINESS_RULES, FEW_SHOT_EXAMPLES
from app.models.audit import AuditLog

logger = logging.getLogger(__name__)

FORBIDDEN_KEYWORDS = re.compile(
    r'\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|EXEC|COPY|PG_)\b',
    re.IGNORECASE,
)

ANSWER_PROMPT = """Te egy pénzügyi asszisztens vagy egy magyar nyelvű vállalatirányítási rendszerben.

Szabályok:
1. Magyarul válaszolj, közérthetően.
2. Összegeket olvashatóan formázd (pl. "1 234 567 Ft" vagy "1,2 millió Ft").
3. Dátumokat magyar formátumban írd (pl. "2025. január").
4. Ne említsd az SQL lekérdezést, csak az eredményt foglald össze.
5. Ha az eredmény üres, mondd meg hogy nem található adat.
6. Ha táblázatos adat van, rendezd logikusan.
7. Maximum 500 szó.
8. Légy precíz a számokkal, ne kerekíts feleslegesen.
"""


def _strip_xml_blocks(text_content: str) -> str:
    """Remove <think>, <plan>, and other XML-style blocks from the response."""
    text_content = re.sub(r'<think>.*?</think>', '', text_content, flags=re.DOTALL)
    text_content = re.sub(r'<plan>.*?</plan>', '', text_content, flags=re.DOTALL)
    return text_content.strip()


def _extract_sql_from_fences(text_content: str) -> str | None:
    """Extract SQL from ```sql ... ``` code fences anywhere in the text."""
    match = re.search(r'```(?:sql)?\s*\n(.*?)```', text_content, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None


def _strip_sql_fences(text_content: str) -> str:
    """Remove markdown code fences if the entire text is wrapped in them."""
    text_content = text_content.strip()
    if text_content.startswith('```'):
        lines = text_content.split('\n')
        lines = lines[1:]
        if lines and lines[-1].strip() == '```':
            lines = lines[:-1]
        text_content = '\n'.join(lines).strip()
    return text_content


def parse_sql_response(raw: str) -> str:
    """
    Parse SQL from model response. Handles:
    1. ```sql ... ``` code fences
    2. Plain SQL
    3. XML blocks (<think>, <answer>, etc.) with SQL inside
    """
    # Try extracting from code fences first
    sql_from_fences = _extract_sql_from_fences(raw)
    if sql_from_fences:
        return sql_from_fences

    # Try <answer> block (Arctic compat)
    answer_match = re.search(r'<answer>(.*?)</answer>', raw, re.DOTALL)
    if answer_match:
        sql = answer_match.group(1).strip()
        sql = _strip_sql_fences(sql)
        return sql.strip()

    # Strip any XML blocks and fences
    sql = _strip_xml_blocks(raw)
    sql = _strip_sql_fences(sql)
    return sql.strip()


def validate_sql(sql: str) -> str | None:
    """Validate SQL is a safe SELECT query. Returns error message or None if valid."""
    cleaned = sql.strip().rstrip(';').strip()

    if not cleaned.upper().startswith('SELECT'):
        return "Csak SELECT lekérdezések engedélyezettek."

    if FORBIDDEN_KEYWORDS.search(cleaned):
        return "Tiltott SQL kulcsszó található a lekérdezésben."

    # Check for multiple statements (remove string literals first)
    no_strings = re.sub(r"'[^']*'", '', cleaned)
    if ';' in no_strings:
        return "Csak egyetlen SQL utasítás engedélyezett."

    return None


async def _call_ollama_chat(
    model: str,
    messages: list[dict],
    num_predict: int | None = None,
    think: bool | None = None,
) -> str:
    """Call Ollama /api/chat endpoint (proper chat format for instruct models)."""
    options: dict = {"temperature": 0.0}
    if num_predict is not None:
        options["num_predict"] = num_predict

    payload: dict = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": options,
    }
    if think is not None:
        payload["think"] = think

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{settings.OLLAMA_URL}/api/chat",
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        # Log timing details from Ollama
        prompt_eval_ms = data.get("prompt_eval_duration", 0) / 1e6
        eval_ms = data.get("eval_duration", 0) / 1e6
        eval_count = data.get("eval_count", 0)
        prompt_count = data.get("prompt_eval_count", 0)
        logger.warning(
            "Ollama [%s]: prompt_tokens=%d (%.0fms) | gen_tokens=%d (%.0fms) | raw=%s",
            model, prompt_count, prompt_eval_ms, eval_count, eval_ms,
            data.get("message", {}).get("content", "")[:200],
        )
        return data.get("message", {}).get("content", "")


async def _execute_sql(db: AsyncSession, sql: str) -> tuple[list[dict], int]:
    """Execute read-only SQL and return results."""
    cleaned = sql.strip().rstrip(';')
    if 'LIMIT' not in cleaned.upper():
        cleaned += ' LIMIT 100'

    result = await db.execute(text(cleaned))
    columns = list(result.keys())
    rows = [dict(zip(columns, row)) for row in result.fetchall()]
    return rows, len(rows)


def _build_few_shot_text(examples: list[dict[str, str]]) -> str:
    """Format few-shot examples for the prompt."""
    lines = []
    for ex in examples:
        lines.append(f"Question: {ex['question']}")
        lines.append(f"SQL: {ex['sql']}")
        lines.append("")
    return "\n".join(lines)


def _build_instructions(few_shots: list[dict[str, str]]) -> str:
    """Build instructions block with business rules and few-shot examples."""
    parts = [BUSINESS_RULES]
    if few_shots:
        parts.append("")
        parts.append("Here are some example question-SQL pairs:")
        for ex in few_shots:
            parts.append(f"Question: {ex['question']}")
            parts.append(f"SQL: {ex['sql']}")
            parts.append("")
    return "\n".join(parts)


def build_messages(
    question: str,
    few_shots: list[dict[str, str]],
    error_context: str | None = None,
) -> list[dict]:
    """
    Build chat messages for the sqlcoder model.
    Uses the defog prompt format: question + instructions + DDL in user message,
    assistant prefill with "The following SQL query best answers the question".
    """
    instructions = _build_instructions(few_shots)

    user_content = f"Generate a SQL query to answer this question: `{question}`\n"
    user_content += f"{instructions}\n\n"
    user_content += f"DDL statements:\n{DDL_SCHEMA}"

    if error_context:
        user_content += f"\n\nThe previous SQL attempt failed:\n{error_context}\nPlease fix the SQL query."

    messages: list[dict] = [
        {"role": "user", "content": user_content},
        {"role": "assistant", "content": f'The following SQL query best answers the question `{question}`:\n```sql'},
    ]

    return messages


async def generate_sql_with_retry(
    question: str,
    db: AsyncSession,
    few_shots: list[dict[str, str]],
    max_retries: int | None = None,
) -> tuple[str, list[dict], int, int, int]:
    """
    Self-correction loop: generate SQL, validate, execute, retry on error.
    Returns: (sql, results, row_count, retry_count, sql_generation_ms)
    """
    if max_retries is None:
        max_retries = settings.SQL_MAX_RETRIES

    error_context: str | None = None
    total_sql_ms = 0

    for attempt in range(max_retries):
        # Build messages
        messages = build_messages(question, few_shots, error_context)

        # Generate SQL via chat API
        t0 = time.monotonic()
        raw = await _call_ollama_chat(
            settings.SQL_MODEL, messages, num_predict=300,
        )
        sql_ms = int((time.monotonic() - t0) * 1000)
        total_sql_ms += sql_ms

        sql = parse_sql_response(raw)

        # Validate
        validation_error = validate_sql(sql)
        if validation_error:
            logger.warning(
                "SQL validation failed (attempt %d/%d): %s | SQL: %s",
                attempt + 1, max_retries, validation_error, sql,
            )
            error_context = f"SQL: {sql}\nError: {validation_error}"
            continue

        # Execute
        try:
            results, row_count = await _execute_sql(db, sql)
            return sql, results, row_count, attempt, total_sql_ms
        except Exception as e:
            error_msg = str(e)
            logger.warning(
                "SQL execution failed (attempt %d/%d): %s | SQL: %s",
                attempt + 1, max_retries, error_msg[:200], sql,
            )
            error_context = f"SQL: {sql}\nDatabase error: {error_msg[:300]}"
            continue

    raise Text2SqlError(
        f"Nem sikerült érvényes SQL-t generálni {max_retries} próbálkozás után.",
        last_sql=sql if 'sql' in dir() else None,
        retry_count=max_retries,
        sql_generation_ms=total_sql_ms,
    )


class Text2SqlError(Exception):
    """Raised when SQL generation fails after all retries."""

    def __init__(
        self,
        message: str,
        last_sql: str | None = None,
        retry_count: int = 0,
        sql_generation_ms: int = 0,
    ):
        super().__init__(message)
        self.last_sql = last_sql
        self.retry_count = retry_count
        self.sql_generation_ms = sql_generation_ms


async def _log_chat(
    db: AsyncSession,
    user_id: str,
    question: str,
    sql: str | None,
    success: bool,
    response_time_ms: int,
) -> None:
    """Write audit log entry for a chat query."""
    try:
        log = AuditLog(
            id=str(uuid.uuid4()),
            user_id=user_id,
            action="chat_query",
            entity_type="chat",
            details={
                "question": question,
                "sql": sql,
                "success": success,
                "response_time_ms": response_time_ms,
            },
        )
        db.add(log)
        await db.commit()
    except Exception:
        logger.exception("Failed to write chat audit log")
        await db.rollback()


class ChatService:

    @staticmethod
    async def chat(db: AsyncSession, question: str, user_id: str) -> ChatResponse:
        """Orchestrate the full chat flow: SQL generation → validation → execution → formatting → audit."""
        t_start = time.monotonic()

        # Load few-shot examples (hardcoded for Phase 1)
        few_shots = FEW_SHOT_EXAMPLES

        # Generate SQL with self-correction
        try:
            sql, results, row_count, retry_count, sql_gen_ms = await generate_sql_with_retry(
                question, db, few_shots,
            )
        except Text2SqlError as e:
            elapsed_ms = int((time.monotonic() - t_start) * 1000)
            await _log_chat(db, user_id, question, e.last_sql, False, elapsed_ms)
            return ChatResponse(
                answer="Sajnálom, nem sikerült érvényes SQL lekérdezést generálni a kérdésedből. Kérlek próbáld újrafogalmazni.",
                sql=e.last_sql,
                error=str(e),
                retry_count=e.retry_count,
                response_time_ms=elapsed_ms,
                sql_generation_ms=e.sql_generation_ms,
                model_used=settings.SQL_MODEL,
            )
        except Exception as e:
            elapsed_ms = int((time.monotonic() - t_start) * 1000)
            await _log_chat(db, user_id, question, None, False, elapsed_ms)
            return ChatResponse(
                answer="Sajnálom, hiba történt a kérdés feldolgozása közben. Kérlek próbáld újra.",
                error=f"Hiba: {str(e)[:200]}",
                response_time_ms=elapsed_ms,
                model_used=settings.SQL_MODEL,
            )

        # Format answer — code-based first, LLM fallback if None
        answer = format_answer(question, results, row_count)

        if answer is None:
            # LLM fallback for complex results
            try:
                result_text = f"Eredmény ({row_count} sor):\n"
                for i, row in enumerate(results[:50]):
                    result_text += f"{i+1}. {row}\n"
                if row_count > 50:
                    result_text += f"... és még {row_count - 50} további sor.\n"

                user_prompt = f'Eredeti kérdés: "{question}"\n\n{result_text}\n\nFogalmazd meg a választ magyarul, közérthetően.'
                raw_answer = await _call_ollama_chat(
                    settings.ANSWER_MODEL,
                    [
                        {"role": "system", "content": ANSWER_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    think=False,
                )
                answer = _strip_xml_blocks(raw_answer)
            except Exception:
                logger.exception("LLM answer generation failed, using raw results")
                answer = f"Az adatok lekérdezése sikeres volt ({row_count} sor), de a válasz formázása sikertelen."

        elapsed_ms = int((time.monotonic() - t_start) * 1000)

        # Audit log
        await _log_chat(db, user_id, question, sql, True, elapsed_ms)

        return ChatResponse(
            answer=answer,
            sql=sql,
            row_count=row_count,
            response_time_ms=elapsed_ms,
            sql_generation_ms=sql_gen_ms,
            retry_count=retry_count,
            model_used=settings.SQL_MODEL,
        )
