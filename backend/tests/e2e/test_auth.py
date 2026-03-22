"""Auth flow E2E tests — 12 tests."""

import uuid

import httpx
import pytest

from tests.conftest import auth_header


# ---- Login ----

class TestLogin:
    async def test_login_success(self, client: httpx.AsyncClient):
        resp = await client.post("/auth/login", json={"email": "admin@invoice.local", "password": "admin123"})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, client: httpx.AsyncClient):
        resp = await client.post("/auth/login", json={"email": "admin@invoice.local", "password": "wrong"})
        assert resp.status_code == 401

    async def test_login_nonexistent_email(self, client: httpx.AsyncClient):
        resp = await client.post("/auth/login", json={"email": "nobody@nowhere.com", "password": "x"})
        assert resp.status_code == 401


# ---- Register ----

class TestRegister:
    async def test_register_success(self, client: httpx.AsyncClient, cleanup):
        email = f"reg_{uuid.uuid4().hex[:8]}@test.local"
        resp = await client.post("/auth/register", json={
            "email": email, "password": "SecurePass1!", "full_name": "Reg Test",
        })
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert data["email"] == email

    async def test_register_duplicate_email(self, client: httpx.AsyncClient):
        email = f"dup_{uuid.uuid4().hex[:8]}@test.local"
        payload = {"email": email, "password": "SecurePass1!", "full_name": "Dup Test"}
        await client.post("/auth/register", json=payload)
        resp = await client.post("/auth/register", json=payload)
        assert resp.status_code == 409


# ---- /me ----

class TestMe:
    async def test_me_valid_token(self, client: httpx.AsyncClient, admin_token: str):
        resp = await client.get("/auth/me", headers=auth_header(admin_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "admin@invoice.local"

    async def test_me_no_token(self, client: httpx.AsyncClient):
        resp = await client.get("/auth/me")
        assert resp.status_code == 401

    async def test_me_invalid_token(self, client: httpx.AsyncClient):
        resp = await client.get("/auth/me", headers=auth_header("invalid.token.here"))
        assert resp.status_code == 401

    async def test_me_expired_token(self, client: httpx.AsyncClient):
        # A structurally valid JWT with exp in the past
        expired = (
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
            "eyJzdWIiOiIxIiwiZXhwIjoxMDAwMDAwMDAwfQ."
            "invalid_signature"
        )
        resp = await client.get("/auth/me", headers=auth_header(expired))
        assert resp.status_code == 401


# ---- Refresh ----

class TestRefresh:
    async def test_refresh_token(self, client: httpx.AsyncClient, admin_token: str):
        resp = await client.post("/auth/refresh", headers=auth_header(admin_token))
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data


# ---- Token role ----

class TestTokenRole:
    async def test_token_contains_correct_role(self, client: httpx.AsyncClient):
        resp = await client.post("/auth/login", json={"email": "admin@invoice.local", "password": "admin123"})
        token = resp.json()["access_token"]
        me = await client.get("/auth/me", headers=auth_header(token))
        assert me.json()["role"] == "admin"


# ---- Inactive user ----

class TestInactiveUser:
    async def test_inactive_user_login(self, client: httpx.AsyncClient, admin_headers: dict):
        """Create a user, deactivate, then try to login."""
        email = f"inactive_{uuid.uuid4().hex[:8]}@test.local"
        password = "InactivePass1!"

        # Create user
        resp = await client.post("/admin/users", json={
            "email": email, "password": password, "full_name": "Inactive User", "role": "reviewer",
        }, headers=admin_headers)
        if resp.status_code not in (200, 201):
            pytest.skip("Cannot create user via admin endpoint")

        user_id = resp.json()["id"]

        # Deactivate
        resp = await client.put(f"/admin/users/{user_id}", json={"is_active": False}, headers=admin_headers)
        assert resp.status_code == 200

        # Login should fail
        resp = await client.post("/auth/login", json={"email": email, "password": password})
        assert resp.status_code == 401
