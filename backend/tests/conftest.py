"""
Shared fixtures for Invoice Manager E2E tests.

All tests hit a running instance (local or remote) via HTTP.
Set TEST_BASE_URL env var to override the default http://localhost:8000.
"""

import os
import uuid
import asyncio
from pathlib import Path
from typing import AsyncGenerator

import httpx
import pytest
import pytest_asyncio

FIXTURES_DIR = Path(__file__).parent / "fixtures"

# ---------------------------------------------------------------------------
# Base URL
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def base_url() -> str:
    return os.environ.get("TEST_BASE_URL", "http://localhost:8000")


@pytest.fixture(scope="session")
def api_url(base_url: str) -> str:
    return f"{base_url}/api/v1"


# ---------------------------------------------------------------------------
# Event loop (session-scoped for reuse)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ---------------------------------------------------------------------------
# HTTP client
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def client(api_url: str) -> AsyncGenerator[httpx.AsyncClient, None]:
    async with httpx.AsyncClient(base_url=api_url, timeout=30.0) as c:
        yield c


@pytest_asyncio.fixture(scope="session")
async def session_client(api_url: str) -> AsyncGenerator[httpx.AsyncClient, None]:
    async with httpx.AsyncClient(base_url=api_url, timeout=30.0) as c:
        yield c


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

async def _login(client: httpx.AsyncClient, email: str, password: str) -> str:
    """Login and return Bearer token string."""
    resp = await client.post("/auth/login", json={"email": email, "password": password})
    resp.raise_for_status()
    return resp.json()["access_token"]


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Admin token (session-scoped)
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="session")
async def admin_token(session_client: httpx.AsyncClient) -> str:
    return await _login(session_client, "admin@invoice.local", "admin123")


@pytest_asyncio.fixture(scope="session")
async def admin_headers(admin_token: str) -> dict:
    return auth_header(admin_token)


# ---------------------------------------------------------------------------
# Role tokens — admin creates test users, logs in as each role
# ---------------------------------------------------------------------------

ROLES = ["reviewer", "accountant", "department_head", "cfo"]


@pytest_asyncio.fixture(scope="session")
async def role_tokens(session_client: httpx.AsyncClient, admin_headers: dict) -> dict[str, str]:
    """Dict of role -> Bearer token. Creates ephemeral users for each role."""
    tokens: dict[str, str] = {}
    suffix = uuid.uuid4().hex[:8]

    for role in ROLES:
        email = f"test_{role}_{suffix}@test.local"
        password = f"Test{role}Pass1!"

        # Register user via admin endpoint
        resp = await session_client.post(
            "/admin/users",
            json={"email": email, "password": password, "full_name": f"Test {role}", "role": role},
            headers=admin_headers,
        )
        if resp.status_code not in (200, 201, 409):
            # If admin create fails, try self-register
            resp = await session_client.post(
                "/auth/register",
                json={"email": email, "password": password, "full_name": f"Test {role}", "role": role},
            )

        tokens[role] = await _login(session_client, email, password)

    return tokens


def role_header(role_tokens: dict, role: str) -> dict:
    return auth_header(role_tokens[role])


# ---------------------------------------------------------------------------
# Test department
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="session")
async def test_department(session_client: httpx.AsyncClient, admin_headers: dict) -> dict:
    resp = await session_client.post(
        "/departments/",
        json={"name": f"Test Dept {uuid.uuid4().hex[:6]}", "code": f"TD{uuid.uuid4().hex[:4]}"},
        headers=admin_headers,
    )
    assert resp.status_code in (200, 201)
    return resp.json()


# ---------------------------------------------------------------------------
# Test partner
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="session")
async def test_partner(session_client: httpx.AsyncClient, admin_headers: dict) -> dict:
    resp = await session_client.post(
        "/partners",
        json={
            "name": f"Test Partner {uuid.uuid4().hex[:6]}",
            "tax_number": f"99{uuid.uuid4().hex[:6]}-2-42",
            "partner_type": "supplier",
        },
        headers=admin_headers,
    )
    assert resp.status_code in (200, 201)
    return resp.json()


# ---------------------------------------------------------------------------
# Cleanup collector
# ---------------------------------------------------------------------------

class Cleanup:
    """Collects (method, url) pairs and deletes them on teardown."""

    def __init__(self, client: httpx.AsyncClient, headers: dict):
        self._client = client
        self._headers = headers
        self._items: list[str] = []

    def add(self, url: str):
        self._items.append(url)

    async def run(self):
        for url in reversed(self._items):
            try:
                await self._client.delete(url, headers=self._headers)
            except Exception:
                pass


@pytest_asyncio.fixture
async def cleanup(client: httpx.AsyncClient, admin_headers: dict):
    c = Cleanup(client, admin_headers)
    yield c
    await c.run()


# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_pdf() -> Path:
    return FIXTURES_DIR / "sample_invoice.pdf"


@pytest.fixture
def invalid_file() -> Path:
    return FIXTURES_DIR / "invalid_file.txt"
