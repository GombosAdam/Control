import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from common.config import settings
from common.database import engine
from common.exceptions import AppException, app_exception_handler

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    logger.info("Invoice Pipeline started")
    yield
    await engine.dispose()


app = FastAPI(
    title="Invoice Pipeline",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(AppException, app_exception_handler)

from app.api.invoices.router import router as invoices_router
from app.api.extraction.router import router as extraction_router
from app.api.reconciliation.router import router as reconciliation_router
from app.api.partners.router import router as partners_router

app.include_router(invoices_router, prefix="/api/v1/invoices", tags=["Invoices"])
app.include_router(extraction_router, prefix="/api/v1/extraction", tags=["Extraction"])
app.include_router(reconciliation_router, prefix="/api/v1/reconciliation", tags=["Reconciliation"])
app.include_router(partners_router, prefix="/api/v1/partners", tags=["Partners"])


@app.get("/")
async def health():
    return {"status": "ok", "service": "invoice-pipeline", "version": "1.0.0"}
