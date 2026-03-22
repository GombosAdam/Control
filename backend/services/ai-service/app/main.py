import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from common.config import settings
from common.database import engine
from common.exceptions import AppException, app_exception_handler
from common.events import event_bus

logger = logging.getLogger(__name__)


async def _event_listener():
    """Listen for events that trigger AI tasks and metrics recalculation."""
    try:
        async for event in event_bus.subscribe(
            "invoice.posted", "invoice.approved", "invoice.enriched",
            "budget.locked", "budget.approved",
            "po.approved",
            "extraction.corrected",
        ):
            event_type = event.get("event")
            payload = event.get("payload", {})
            logger.info("Received event: %s", event_type)
            try:
                from app.workers.celery_app import celery_app

                if event_type == "invoice.enriched":
                    invoice_id = payload.get("invoice_id")
                    if invoice_id:
                        celery_app.send_task("suggest_budget_category", args=[invoice_id])
                        celery_app.send_task("suggest_po_match", args=[invoice_id])
                        celery_app.send_task("detect_anomalies", args=[invoice_id])
                elif event_type == "extraction.corrected":
                    invoice_id = payload.get("invoice_id")
                    if invoice_id:
                        celery_app.send_task("store_supplier_template", args=[invoice_id])
                else:
                    celery_app.send_task("calculate_cfo_metrics")
            except Exception:
                logger.exception("Failed to dispatch task for event %s", event_type)
    except asyncio.CancelledError:
        pass
    except Exception:
        logger.exception("Event listener crashed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start event listener
    listener_task = asyncio.create_task(_event_listener())
    logger.info("AI Service started — event listener active")

    yield

    # Shutdown
    listener_task.cancel()
    try:
        await listener_task
    except asyncio.CancelledError:
        pass
    await event_bus.close()
    await engine.dispose()


app = FastAPI(
    title="AI Service",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
app.add_exception_handler(AppException, app_exception_handler)

# Routers
from app.api.chat.router import router as chat_router
from app.api.dashboard.router import router as dashboard_router
from app.api.agent.router import router as agent_router

app.include_router(chat_router, prefix="/api/v1/chat", tags=["Chat"])
app.include_router(dashboard_router, prefix="/api/v1/dashboard", tags=["Dashboard"])
app.include_router(agent_router, prefix="/api/v1/agent", tags=["Agent"])

# Health check
@app.get("/")
async def health():
    return {"status": "ok", "service": "ai-service", "version": "1.0.0"}
