from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base
from app.exceptions import AppException, app_exception_handler

from app.api.config.router import router as config_router
from app.api.sync.router import router as sync_router
from app.api.submit.router import router as submit_router
from app.api.taxpayer.router import router as taxpayer_router
from app.api.transactions.router import router as transactions_router

# Import models so tables get created
import app.models  # noqa


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="NAV Online Számla Service",
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

# Register routers
app.include_router(config_router, prefix="/api/v1/nav/config", tags=["NAV Config"])
app.include_router(sync_router, prefix="/api/v1/nav/sync", tags=["NAV Sync"])
app.include_router(submit_router, prefix="/api/v1/nav/submit", tags=["NAV Submit"])
app.include_router(taxpayer_router, prefix="/api/v1/nav/taxpayer", tags=["NAV Taxpayer"])
app.include_router(transactions_router, prefix="/api/v1/nav/transactions", tags=["NAV Transactions"])


@app.get("/")
async def health():
    return {"status": "ok", "service": "nav-service"}
