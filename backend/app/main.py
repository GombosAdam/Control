import os
import uuid
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import engine, Base
from app.exceptions import AppException, app_exception_handler
from app.api.v1.router import api_router

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all tables from models (idempotent — only creates missing tables)
    from sqlalchemy import create_engine
    sync_engine = create_engine(settings.DATABASE_URL_SYNC)
    Base.metadata.create_all(sync_engine)
    sync_engine.dispose()
    logger.info("Database tables ensured")

    # Create upload directory
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    # Seed admin user
    from app.database import async_session_factory
    from app.models.user import User, UserRole
    from app.utils.security import hash_password
    from sqlalchemy import select

    admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")
    async with async_session_factory() as db:
        result = await db.execute(select(User).where(User.email == "admin@invoice.local"))
        admin_user = result.scalar_one_or_none()
        if not admin_user:
            admin_user = User(
                email="admin@invoice.local",
                password_hash=hash_password(admin_password),
                full_name="Admin User",
                role=UserRole.admin,
            )
            db.add(admin_user)
            await db.commit()
            await db.refresh(admin_user)
            logger.info("Admin user created with password from ADMIN_PASSWORD env")

    # Seed default scenario
    from app.models.scenario import Scenario
    async with async_session_factory() as db:
        result = await db.execute(select(Scenario).where(Scenario.is_default == True))
        if not result.scalar_one_or_none():
            result2 = await db.execute(select(User).where(User.email == "admin@invoice.local"))
            admin = result2.scalar_one_or_none()
            if admin:
                default_scenario = Scenario(
                    id=str(uuid.uuid4()),
                    name="Base",
                    description="Alap szcenárió",
                    is_default=True,
                    created_by=admin.id,
                )
                db.add(default_scenario)
                await db.commit()

                from sqlalchemy import update
                from app.models.budget_line import BudgetLine
                await db.execute(
                    update(BudgetLine).where(BudgetLine.scenario_id == None).values(scenario_id=default_scenario.id)
                )
                await db.commit()

    # Seed accounting templates (könyvelési tükör)
    from app.models.accounting_template import AccountingTemplate
    async with async_session_factory() as db:
        result = await db.execute(select(AccountingTemplate).limit(1))
        if not result.scalar_one_or_none():
            templates = [
                ("51*", "Anyagköltség", "511", "454", "Anyag és alapanyag költségek"),
                ("52*", "Szolgáltatás", "521", "454", "Igénybe vett szolgáltatások"),
                ("53*", "Bérleti díj", "531", "454", "Bérleti és lízing díjak"),
                ("54*", "Marketing", "541", "454", "Marketing és reklám költségek"),
                ("55*", "IT költség", "551", "454", "Informatikai költségek"),
                ("*", "Egyéb költség", "599", "454", "Egyéb, nem kategorizált költségek"),
            ]
            for pattern, name, debit, credit, desc in templates:
                db.add(AccountingTemplate(
                    account_code_pattern=pattern, name=name,
                    debit_account=debit, credit_account=credit, description=desc,
                ))
            await db.commit()
            logger.info("Accounting templates seeded")

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

