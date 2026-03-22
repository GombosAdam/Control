import logging
import time
import uuid

import anthropic
from sqlalchemy.ext.asyncio import AsyncSession

from common.config import settings
from common.models.audit import AuditLog
from app.api.agent.pulse import get_pulse
from app.api.agent.prompts import build_system_prompt
from app.api.agent.tools import TOOL_DEFINITIONS
from app.api.agent.tool_executor import execute_tool
from app.api.agent.schemas import AgentResponse, ToolCallLog

logger = logging.getLogger(__name__)

_client: anthropic.AsyncAnthropic | None = None


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client


async def _log_agent(
    db: AsyncSession,
    user_id: str,
    question: str,
    tool_calls: list[dict],
    answer: str,
    total_ms: int,
) -> None:
    try:
        log = AuditLog(
            id=str(uuid.uuid4()),
            user_id=user_id,
            action="agent_query",
            entity_type="agent",
            details={
                "question": question,
                "tool_calls": tool_calls,
                "answer": answer[:500],
                "response_time_ms": total_ms,
            },
        )
        db.add(log)
        await db.commit()
    except Exception:
        logger.exception("Failed to write agent audit log")
        await db.rollback()


class AgentService:
    @staticmethod
    async def ask(
        db: AsyncSession,
        question: str,
        user_id: str,
        token: str,
    ) -> AgentResponse:
        start = time.time()

        try:
            # 1. Pulse
            pulse = await get_pulse(db)

            # 2. System prompt
            system = build_system_prompt(pulse)

            # 3. Messages
            messages: list[dict] = [
                {"role": "user", "content": question},
            ]

            tool_call_log: list[dict] = []
            answer = ""
            client = _get_client()

            # 4. Tool-calling loop
            for _i in range(settings.AGENT_MAX_TOOL_CALLS):
                response = await client.messages.create(
                    model=settings.AGENT_MODEL,
                    max_tokens=2048,
                    system=system,
                    tools=TOOL_DEFINITIONS,
                    messages=messages,
                )

                logger.warning(
                    "Claude Agent [%s]: input=%d output=%d stop=%s",
                    settings.AGENT_MODEL,
                    response.usage.input_tokens,
                    response.usage.output_tokens,
                    response.stop_reason,
                )

                # If end_turn or no tool_use blocks → final answer
                if response.stop_reason == "end_turn":
                    text_blocks = [b.text for b in response.content if b.type == "text"]
                    answer = "\n".join(text_blocks)
                    break

                # Process tool_use blocks
                tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
                if not tool_use_blocks:
                    text_blocks = [b.text for b in response.content if b.type == "text"]
                    answer = "\n".join(text_blocks)
                    break

                # Append assistant message with all content blocks
                messages.append({
                    "role": "assistant",
                    "content": [b.model_dump() for b in response.content],
                })

                # Execute each tool and build tool_result blocks
                tool_results = []
                for block in tool_use_blocks:
                    fn_name = block.name
                    fn_args = block.input

                    tc_start = time.time()
                    result = await execute_tool(fn_name, fn_args, token, db)
                    tc_ms = int((time.time() - tc_start) * 1000)

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

                    tool_call_log.append({
                        "tool": fn_name,
                        "params": fn_args,
                        "latency_ms": tc_ms,
                    })

                messages.append({"role": "user", "content": tool_results})

            else:
                # Max tool calls reached — force final answer
                messages.append({
                    "role": "user",
                    "content": "Válaszolj a rendelkezésedre álló információk alapján.",
                })
                response = await client.messages.create(
                    model=settings.AGENT_MODEL,
                    max_tokens=2048,
                    system=system,
                    messages=messages,
                )
                text_blocks = [b.text for b in response.content if b.type == "text"]
                answer = "\n".join(text_blocks)

            total_ms = int((time.time() - start) * 1000)

            # 5. Audit log
            await _log_agent(db, user_id, question, tool_call_log, answer, total_ms)

            return AgentResponse(
                answer=answer,
                tool_calls=[ToolCallLog(**tc) for tc in tool_call_log],
                response_time_ms=total_ms,
                model_used=settings.AGENT_MODEL,
            )

        except Exception as e:
            total_ms = int((time.time() - start) * 1000)
            logger.exception("Agent error")
            return AgentResponse(
                answer="Sajnálom, hiba történt a kérdés feldolgozása közben.",
                error=str(e)[:300],
                response_time_ms=total_ms,
                model_used=settings.AGENT_MODEL,
            )
