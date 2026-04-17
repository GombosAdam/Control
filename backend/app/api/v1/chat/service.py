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
    text_content = re.sub(r'<think>.*?</think>', '', text_content, flags=re.DOTALL)
    text_content = re.sub(r'<plan>.*?</plan>', '', text_content, flags=re.DOTALL)
    return text_content.strip()


def _extract_sql_from_fences(text_content: str) -> str | None:
    match = re.search(r'```(?:sql)?\s*\n(.*?)```', text_content, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None


def _strip_sql_fences(text_content: str) -> str:
    text_content = text_content.strip()
    if text_content.startswith('```'):
        lines = text_content.split('\n')
        lines = lines[1:]
        if lines and lines[-1].strip() == '```':
            lines = lines[:-1]
        text_content = '\n'.join(lines).strip()
    return text_content


def parse_sql_response(raw: str) -> str:
    stripped = raw.strip()
    sql_from_fences = _extract_sql_from_fences(stripped)
    if sql_from_fences:
        return sql_from_fences
    answer_match = re.search(r'<answer>(.*?)</answer>', stripped, re.DOTALL)
    if answer_match:
        sql = answer_match.group(1).strip()
        sql = _strip_sql_fences(sql)
        return sql.strip()
    if stripped.endswith('```'):
        stripped = stripped[:-3].strip()
    stripped = _strip_xml_blocks(stripped)
    stripped = _strip_sql_fences(stripped)
    stripped = re.sub(r'^(?:SQL\s*:\s*)', '', stripped, flags=re.IGNORECASE).strip()
    return stripped


def validate_sql(sql: str) -> str | None:
    cleaned = sql.strip().rstrip(';').strip()
    if not cleaned.upper().startswith('SELECT'):
        return "Csak SELECT lekérdezések engedélyezettek."
    if FORBIDDEN_KEYWORDS.search(cleaned):
        return "Tiltott SQL kulcsszó található a lekérdezésben."
    no_strings = re.sub(r"'[^']*'", '', cleaned)
    if ';' in no_strings:
        return "Csak egyetlen SQL utasítás engedélyezett."
    return None


async def _call_claude(
    system: str,
    messages: list[dict],
    max_tokens: int = 1024,
) -> str:
    """Call Anthropic Messages API."""
    api_key = settings.ANTHROPIC_API_KEY
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not configured")

    payload = {
        "model": settings.CLAUDE_MODEL,
        "max_tokens": max_tokens,
        "system": system,
        "messages": messages,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        content = data.get("content", [])
        text_parts = [block["text"] for block in content if block.get("type") == "text"]
        result = "\n".join(text_parts)
        input_tokens = data.get("usage", {}).get("input_tokens", 0)
        output_tokens = data.get("usage", {}).get("output_tokens", 0)
        logger.warning(
            "Claude [%s]: input_tokens=%d | output_tokens=%d | raw=%s",
            settings.CLAUDE_MODEL, input_tokens, output_tokens, result[:200],
        )
        return result


async def _execute_sql(db: AsyncSession, sql: str) -> tuple[list[dict], int]:
    cleaned = sql.strip().rstrip(';')
    if 'LIMIT' not in cleaned.upper():
        cleaned += ' LIMIT 100'
    result = await db.execute(text(cleaned))
    columns = list(result.keys())
    rows = [dict(zip(columns, row)) for row in result.fetchall()]
    return rows, len(rows)


def _build_few_shot_text(examples: list[dict[str, str]]) -> str:
    lines = []
    for ex in examples:
        lines.append(f"Question: {ex['question']}")
        lines.append(f"SQL: {ex['sql']}")
        lines.append("")
    return "\n".join(lines)


def build_messages(
    question: str,
    few_shots: list[dict[str, str]],
    error_context: str | None = None,
) -> tuple[str, list[dict]]:
    """Build system prompt and user messages for Claude API."""
    system_content = "\n\n".join([
        "Te egy SQL lekérdezés generátor vagy egy pénzügyi rendszerhez. "
        "CSAK a nyers SQL-t add vissza, semmilyen magyarázatot, markdown formázást vagy gondolkodást ne adj. "
        "Csak SELECT lekérdezéseket írj.",
        "Database schema:",
        DDL_SCHEMA,
        "Business rules:",
        BUSINESS_RULES,
    ])

    if few_shots:
        examples = _build_few_shot_text(few_shots)
        system_content += f"\n\nPéldák:\n{examples}"

    user_content = question
    if error_context:
        user_content += f"\n\nAz előző SQL hibás volt:\n{error_context}\nJavítsd ki."

    messages = [{"role": "user", "content": user_content}]
    return system_content, messages


async def generate_sql_with_retry(
    question: str,
    db: AsyncSession,
    few_shots: list[dict[str, str]],
    max_retries: int | None = None,
) -> tuple[str, list[dict], int, int, int]:
    if max_retries is None:
        max_retries = settings.SQL_MAX_RETRIES

    error_context: str | None = None
    total_sql_ms = 0
    sql = ""

    for attempt in range(max_retries):
        system, messages = build_messages(question, few_shots, error_context)

        t0 = time.monotonic()
        raw = await _call_claude(system, messages, max_tokens=400)
        sql_ms = int((time.monotonic() - t0) * 1000)
        total_sql_ms += sql_ms

        sql = parse_sql_response(raw)

        validation_error = validate_sql(sql)
        if validation_error:
            logger.warning(
                "SQL validation failed (attempt %d/%d): %s | SQL: %s",
                attempt + 1, max_retries, validation_error, sql,
            )
            error_context = f"SQL: {sql}\nError: {validation_error}"
            continue

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
        last_sql=sql,
        retry_count=max_retries,
        sql_generation_ms=total_sql_ms,
    )


class Text2SqlError(Exception):
    def __init__(self, message: str, last_sql: str | None = None,
                 retry_count: int = 0, sql_generation_ms: int = 0):
        super().__init__(message)
        self.last_sql = last_sql
        self.retry_count = retry_count
        self.sql_generation_ms = sql_generation_ms


async def _log_chat(db: AsyncSession, user_id: str, question: str,
                    sql: str | None, success: bool, response_time_ms: int) -> None:
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
        t_start = time.monotonic()
        few_shots = FEW_SHOT_EXAMPLES

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
                model_used=settings.CLAUDE_MODEL,
            )
        except Exception as e:
            elapsed_ms = int((time.monotonic() - t_start) * 1000)
            await _log_chat(db, user_id, question, None, False, elapsed_ms)
            return ChatResponse(
                answer="Sajnálom, hiba történt a kérdés feldolgozása közben. Kérlek próbáld újra.",
                error=f"Hiba: {str(e)[:200]}",
                response_time_ms=elapsed_ms,
                model_used=settings.CLAUDE_MODEL,
            )

        answer = format_answer(question, results, row_count)

        if answer is None:
            try:
                result_text = f"Eredmény ({row_count} sor):\n"
                for i, row in enumerate(results[:50]):
                    result_text += f"{i+1}. {row}\n"
                if row_count > 50:
                    result_text += f"... és még {row_count - 50} további sor.\n"

                user_prompt = f'Eredeti kérdés: "{question}"\n\n{result_text}\n\nFogalmazd meg a választ magyarul, közérthetően.'
                answer = await _call_claude(
                    ANSWER_PROMPT,
                    [{"role": "user", "content": user_prompt}],
                    max_tokens=800,
                )
                answer = _strip_xml_blocks(answer)
            except Exception:
                logger.exception("LLM answer generation failed, using raw results")
                answer = f"Az adatok lekérdezése sikeres volt ({row_count} sor), de a válasz formázása sikertelen."

        elapsed_ms = int((time.monotonic() - t_start) * 1000)
        await _log_chat(db, user_id, question, sql, True, elapsed_ms)

        return ChatResponse(
            answer=answer,
            sql=sql,
            row_count=row_count,
            response_time_ms=elapsed_ms,
            sql_generation_ms=sql_gen_ms,
            retry_count=retry_count,
            model_used=settings.CLAUDE_MODEL,
        )
