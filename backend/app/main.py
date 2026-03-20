import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import engine, Base
from app.exceptions import AppException, app_exception_handler
from app.api.v1.router import api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables if needed
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create upload directory
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    # Seed admin user
    from app.database import async_session_factory
    from app.models.user import User, UserRole
    from app.utils.security import hash_password
    from sqlalchemy import select

    async with async_session_factory() as db:
        result = await db.execute(select(User).where(User.email == "admin@invoice.local"))
        if not result.scalar_one_or_none():
            admin = User(
                email="admin@invoice.local",
                password_hash=hash_password("admin123"),
                full_name="Admin User",
                role=UserRole.admin,
            )
            db.add(admin)
            await db.commit()

    yield

    # Shutdown
    await engine.dispose()

app = FastAPI(
    title=settings.APP_NAME,
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

# API routes
app.include_router(api_router, prefix="/api/v1")

# Health check
@app.get("/")
async def health():
    return {"status": "ok", "app": settings.APP_NAME, "version": "1.0.0"}

