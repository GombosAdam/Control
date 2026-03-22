import httpx
from common.config import settings


class ServiceClient:
    """Async HTTP client for calling finance-service and invoice-pipeline."""

    def __init__(self) -> None:
        self.client = httpx.AsyncClient(timeout=10.0)

    async def finance(self, path: str, params: dict | None = None, token: str = "") -> dict | list:
        resp = await self.client.get(
            f"{settings.FINANCE_SERVICE_URL}{path}",
            params=params,
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
        return resp.json()

    async def pipeline(self, path: str, params: dict | None = None, token: str = "") -> dict | list:
        resp = await self.client.get(
            f"{settings.INVOICE_PIPELINE_URL}{path}",
            params=params,
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
        return resp.json()

    async def close(self) -> None:
        await self.client.aclose()


service_client = ServiceClient()
