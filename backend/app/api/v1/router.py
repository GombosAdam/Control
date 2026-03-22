from fastapi import APIRouter
from app.api.v1.auth.router import router as auth_router
from app.api.v1.invoices.router import router as invoices_router
from app.api.v1.extraction.router import router as extraction_router
from app.api.v1.partners.router import router as partners_router
from app.api.v1.reports.router import router as reports_router
from app.api.v1.dashboard.router import router as dashboard_router
from app.api.v1.admin.router import router as admin_router
from app.api.v1.accounting.router import router as accounting_router
from app.api.v1.departments.router import router as departments_router
from app.api.v1.budget.router import router as budget_router
from app.api.v1.purchase_orders.router import router as purchase_orders_router
from app.api.v1.reconciliation.router import router as reconciliation_router
from app.api.v1.controlling.router import router as controlling_router
from app.api.v1.scenarios.router import router as scenarios_router
from app.api.v1.chat.router import router as chat_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["Auth"])
api_router.include_router(dashboard_router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(invoices_router, prefix="/invoices", tags=["Invoices"])
api_router.include_router(extraction_router, prefix="/extraction", tags=["Extraction"])
api_router.include_router(accounting_router, prefix="/accounting", tags=["Accounting"])
api_router.include_router(partners_router, prefix="/partners", tags=["Partners"])
api_router.include_router(reports_router, prefix="/reports", tags=["Reports"])
api_router.include_router(admin_router, prefix="/admin", tags=["Admin"])
api_router.include_router(departments_router, prefix="/departments", tags=["Departments"])
api_router.include_router(budget_router, prefix="/budget", tags=["Budget"])
api_router.include_router(purchase_orders_router, prefix="/purchase-orders", tags=["Purchase Orders"])
api_router.include_router(reconciliation_router, prefix="/reconciliation", tags=["Reconciliation"])
api_router.include_router(controlling_router, prefix="/controlling", tags=["Controlling"])
api_router.include_router(scenarios_router, prefix="/scenarios", tags=["Scenarios"])
api_router.include_router(chat_router, prefix="/chat", tags=["Chat"])
