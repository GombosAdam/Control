import os
import uuid
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from common.config import settings
from common.database import engine, Base
from common.exceptions import AppException, app_exception_handler

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Database tables are managed by Alembic migrations
    # Do NOT use Base.metadata.create_all() — it masks migration drift
    logger.info("Finance service starting (tables managed by Alembic)")

    # Create upload directory
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    # Seed admin user
    from common.database import async_session_factory
    from common.models.user import User, UserRole
    from common.utils.security import hash_password
    from sqlalchemy import select

    admin_password = os.environ.get("ADMIN_PASSWORD", "")
    if not admin_password:
        logger.warning("ADMIN_PASSWORD not set — skipping admin seed. Set ADMIN_PASSWORD env var.")
    else:
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
    from common.models.scenario import Scenario
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
                from common.models.budget_line import BudgetLine
                await db.execute(
                    update(BudgetLine).where(BudgetLine.scenario_id == None).values(scenario_id=default_scenario.id)
                )
                await db.commit()

    # Seed accounting templates
    from common.models.accounting_template import AccountingTemplate
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

    await engine.dispose()


app = FastAPI(
    title="Finance Service",
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

# Routers
from app.api.auth.router import router as auth_router
from app.api.dashboard.router import router as dashboard_router
from app.api.budget.router import router as budget_router
from app.api.purchase_orders.router import router as purchase_orders_router
from app.api.accounting.router import router as accounting_router
from app.api.controlling.router import router as controlling_router
from app.api.scenarios.router import router as scenarios_router
from app.api.departments.router import router as departments_router
from app.api.admin.router import router as admin_router
from app.api.reports.router import router as reports_router
from app.api.planning_periods.router import router as planning_periods_router
from app.api.positions.router import router as positions_router

app.include_router(auth_router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(dashboard_router, prefix="/api/v1/dashboard", tags=["Dashboard"])
app.include_router(budget_router, prefix="/api/v1/budget", tags=["Budget"])
app.include_router(purchase_orders_router, prefix="/api/v1/purchase-orders", tags=["Purchase Orders"])
app.include_router(accounting_router, prefix="/api/v1/accounting", tags=["Accounting"])
app.include_router(controlling_router, prefix="/api/v1/controlling", tags=["Controlling"])
app.include_router(scenarios_router, prefix="/api/v1/scenarios", tags=["Scenarios"])
app.include_router(departments_router, prefix="/api/v1/departments", tags=["Departments"])
app.include_router(admin_router, prefix="/api/v1/admin", tags=["Admin"])
app.include_router(reports_router, prefix="/api/v1/reports", tags=["Reports"])
app.include_router(planning_periods_router, prefix="/api/v1/planning-periods", tags=["Planning Periods"])
app.include_router(positions_router, prefix="/api/v1/positions", tags=["Positions"])


@app.get("/")
async def health():
    return {"status": "ok", "service": "finance-service", "version": "1.0.0"}
