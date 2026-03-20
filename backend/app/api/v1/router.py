from fastapi import APIRouter
from app.api.v1.auth.router import router as auth_router
from app.api.v1.invoices.router import router as invoices_router
from app.api.v1.extraction.router import router as extraction_router
from app.api.v1.partners.router import router as partners_router
from app.api.v1.reports.router import router as reports_router
from app.api.v1.dashboard.router import router as dashboard_router
from app.api.v1.admin.router import router as admin_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["Auth"])
api_router.include_router(dashboard_router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(invoices_router, prefix="/invoices", tags=["Invoices"])
api_router.include_router(extraction_router, prefix="/extraction", tags=["Extraction"])
api_router.include_router(partners_router, prefix="/partners", tags=["Partners"])
api_router.include_router(reports_router, prefix="/reports", tags=["Reports"])
api_router.include_router(admin_router, prefix="/admin", tags=["Admin"])
