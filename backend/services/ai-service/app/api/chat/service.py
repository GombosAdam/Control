import json
import logging
import re
import time
import uuid

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from common.config import settings
from app.api.chat.formatter import format_answer, detect_chart_data
from app.api.chat.schemas import ChatResponse
from app.api.chat.semantic_schema import DDL_SCHEMA, BUSINESS_RULES, FEW_SHOT_EXAMPLES
from common.models.audit import AuditLog

logger = logging.getLogger(__name__)

FORBIDDEN_KEYWORDS = re.compile(
    r'\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|EXEC|COPY|PG_|'
    r'SET\s+ROLE|SET\s+SESSION|LOAD|IMPORT|EXPORT|DO\s*\$|LO_|'
    r'VACUUM|ANALYZE|REINDEX|CLUSTER|DISCARD|RESET|NOTIFY|LISTEN|UNLISTEN)\b',
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
    # Strip string literals and comments before checking structure
    no_strings = re.sub(r"'[^']*'", '', cleaned)
    no_strings = re.sub(r'--.*$', '', no_strings, flags=re.MULTILINE)
    no_strings = re.sub(r'/\*.*?\*/', '', no_strings, flags=re.DOTALL)
    if ';' in no_strings:
        return "Csak egyetlen SQL utasítás engedélyezett."
    # Block dollar-quoting (PostgreSQL-specific injection vector)
    if re.search(r'\$[a-zA-Z_]*\$', no_strings):
        return "Dollar-quoting nem engedélyezett."
    # Block function calls that could be dangerous
    dangerous_funcs = re.compile(
        r'\b(pg_read_file|pg_read_binary_file|pg_ls_dir|pg_stat_file|'
        r'lo_import|lo_export|lo_get|lo_put|'
        r'dblink|dblink_exec|'
        r'current_setting\s*\(\s*[\'"]superuser)',
        re.IGNORECASE,
    )
    if dangerous_funcs.search(no_strings):
        return "Tiltott PostgreSQL függvényhívás."
    return None


async def _call_ollama_chat(
    model: str,
    messages: list[dict],
    num_predict: int | None = None,
    think: bool | None = None,
) -> str:
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
    cleaned = sql.strip().rstrip(';')
    if 'LIMIT' not in cleaned.upper():
        cleaned += ' LIMIT 100'
    # Force read-only transaction to prevent any writes
    await db.execute(text("SET TRANSACTION READ ONLY"))
    try:
        result = await db.execute(text(cleaned))
        columns = list(result.keys())
        rows = [dict(zip(columns, row)) for row in result.fetchall()]
        return rows, len(rows)
    finally:
        await db.rollback()


def _build_few_shot_text(examples: list[dict[str, str]]) -> str:
    lines = []
    for ex in examples:
        lines.append(f"Question: {ex['question']}")
        lines.append(f"SQL: {ex['sql']}")
        lines.append("")
    return "\n".join(lines)


def _build_instructions(few_shots: list[dict[str, str]]) -> str:
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
    messages: list[dict] = [
        {"role": "system", "content": system_content},
    ]
    user_content = question
    if error_context:
        user_content += f"\n\nAz előző SQL hibás volt:\n{error_context}\nJavítsd ki."
    messages.append({"role": "user", "content": user_content})
    return messages


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
    for attempt in range(max_retries):
        messages = build_messages(question, few_shots, error_context)
        t0 = time.monotonic()
        raw = await _call_ollama_chat(
            settings.SQL_MODEL, messages, num_predict=300, think=False,
        )
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
        last_sql=sql if 'sql' in dir() else None,
        retry_count=max_retries,
        sql_generation_ms=total_sql_ms,
    )


class Text2SqlError(Exception):
    def __init__(self, message: str, last_sql: str | None = None, retry_count: int = 0, sql_generation_ms: int = 0):
        super().__init__(message)
        self.last_sql = last_sql
        self.retry_count = retry_count
        self.sql_generation_ms = sql_generation_ms


async def _log_chat(db: AsyncSession, user_id: str, question: str, sql: str | None, success: bool, response_time_ms: int) -> None:
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


def _get_rag_examples(question: str) -> list[dict[str, str]]:
    """Fetch similar examples from Qdrant RAG store."""
    try:
        from common.vectorstore import VectorStoreManager
        vs = VectorStoreManager(
            qdrant_url=settings.QDRANT_URL,
            ollama_url=settings.OLLAMA_URL,
            embed_model=settings.EMBEDDING_MODEL,
        )
        results = vs.search(
            collection="text2sql_examples",
            text=question,
            top_k=3,
            min_score=settings.RAG_MIN_SCORE,
        )
        vs.close()
        return [
            {"question": r["payload"]["question"], "sql": r["payload"]["sql"]}
            for r in results
        ]
    except Exception as e:
        logger.debug("RAG lookup failed (non-critical): %s", e)
        return []


class ChatService:
    @staticmethod
    async def chat(db: AsyncSession, question: str, user_id: str) -> ChatResponse:
        t_start = time.monotonic()

        # RAG: fetch similar examples, prepend to hardcoded few-shots
        rag_examples = _get_rag_examples(question)
        # RAG first, then hardcoded — max 8 total
        few_shots = rag_examples + FEW_SHOT_EXAMPLES
        if len(few_shots) > 8:
            few_shots = rag_examples[:3] + FEW_SHOT_EXAMPLES[:5]

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
        answer = format_answer(question, results, row_count)
        if answer is None:
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
        await _log_chat(db, user_id, question, sql, True, elapsed_ms)

        # Store successful query in RAG (async via Celery)
        try:
            from app.workers.celery_app import celery_app
            celery_app.send_task("store_chat_example", args=[question, sql])
        except Exception:
            logger.debug("Failed to queue RAG store task")

        chart = detect_chart_data(question, results, row_count)

        return ChatResponse(
            answer=answer,
            sql=sql,
            row_count=row_count,
            response_time_ms=elapsed_ms,
            sql_generation_ms=sql_gen_ms,
            retry_count=retry_count,
            model_used=settings.SQL_MODEL,
            chart_data=chart,
        )
