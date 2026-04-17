"""
NAV Online Számla mirror routes for the legacy monolith.
Proxies requests to the nav-service microservice at port 8004.
In production, nginx routes /api/v1/nav/* directly to nav-service,
so these routes are only used in local development without nginx.
"""

from fastapi import APIRouter, Request, Response
import httpx

router = APIRouter()

NAV_SERVICE_URL = "http://localhost:8004"


async def _proxy(request: Request, path: str) -> Response:
    """Forward request to nav-service."""
    url = f"{NAV_SERVICE_URL}/api/v1/nav/{path}"
    headers = dict(request.headers)
    headers.pop("host", None)

    async with httpx.AsyncClient(timeout=60.0) as client:
        body = await request.body()
        response = await client.request(
            method=request.method,
            url=url,
            headers=headers,
            content=body,
            params=dict(request.query_params),
        )

    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=dict(response.headers),
    )


@router.api_route("/config{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_config(request: Request, path: str = ""):
    return await _proxy(request, f"config{path}")


@router.api_route("/sync{path:path}", methods=["GET", "POST"])
async def proxy_sync(request: Request, path: str = ""):
    return await _proxy(request, f"sync{path}")


@router.api_route("/submit{path:path}", methods=["POST"])
async def proxy_submit(request: Request, path: str = ""):
    return await _proxy(request, f"submit{path}")


@router.api_route("/taxpayer{path:path}", methods=["POST"])
async def proxy_taxpayer(request: Request, path: str = ""):
    return await _proxy(request, f"taxpayer{path}")


@router.api_route("/transactions{path:path}", methods=["GET", "POST"])
async def proxy_transactions(request: Request, path: str = ""):
    return await _proxy(request, f"transactions{path}")
