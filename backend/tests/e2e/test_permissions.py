"""Permission system E2E tests — full flow.

Tests the dynamic permission system:
1. Admin login → permission matrix visible
2. Admin gets all permissions via /auth/me/permissions
3. User switch → switched user gets limited permissions
4. Admin modifies permission matrix → change takes effect
5. Revoke a permission → user loses access
6. Re-grant → user regains access
7. Non-admin cannot access permission management
"""

import uuid

import httpx
import pytest

from tests.conftest import auth_header


def _h(role_tokens: dict, role: str) -> dict:
    return auth_header(role_tokens[role])


class TestPermissionMatrix:
    """Admin can read and modify the permission matrix."""

    async def test_get_matrix(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.get("/admin/permissions/matrix", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "roles" in data
        assert "permissions" in data
        assert "granted" in data
        assert "admin" in data["roles"]
        assert len(data["permissions"]) > 0

    async def test_matrix_has_all_roles(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.get("/admin/permissions/matrix", headers=admin_headers)
        roles = resp.json()["roles"]
        for role in ["admin", "cfo", "department_head", "accountant", "reviewer", "clerk"]:
            assert role in roles

    async def test_matrix_admin_has_all_permissions(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.get("/admin/permissions/matrix", headers=admin_headers)
        data = resp.json()
        admin_perms = set(data["granted"].get("admin", []))
        all_perm_ids = {p["id"] for p in data["permissions"]}
        assert admin_perms == all_perm_ids, "Admin should have all permissions"

    async def test_non_admin_cannot_access_matrix(self, client: httpx.AsyncClient, role_tokens: dict):
        for role in ["reviewer", "accountant", "department_head", "cfo"]:
            resp = await client.get("/admin/permissions/matrix", headers=_h(role_tokens, role))
            assert resp.status_code == 403, f"{role} should not access permission matrix"


class TestMyPermissions:
    """Users can see their own effective permissions."""

    async def test_admin_gets_all_permissions(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.get("/auth/me/permissions", headers=admin_headers)
        assert resp.status_code == 200
        perms = resp.json()["permissions"]
        assert len(perms) > 0
        # Admin should have admin-specific permissions
        assert any("admin" in p for p in perms)

    async def test_reviewer_gets_limited_permissions(self, client: httpx.AsyncClient, role_tokens: dict):
        resp = await client.get("/auth/me/permissions", headers=_h(role_tokens, "reviewer"))
        assert resp.status_code == 200
        perms = set(resp.json()["permissions"])
        # Reviewer should have dashboard and invoices read
        assert "dashboard:read" in perms
        assert "invoices:read" in perms
        # Reviewer should NOT have admin or budget
        assert not any(p.startswith("admin.") for p in perms)
        assert not any(p.startswith("budget:") for p in perms)

    async def test_accountant_has_accounting_permissions(self, client: httpx.AsyncClient, role_tokens: dict):
        resp = await client.get("/auth/me/permissions", headers=_h(role_tokens, "accountant"))
        perms = set(resp.json()["permissions"])
        assert "accounting:read" in perms
        assert "accounting:create" in perms
        assert "invoices:upload" in perms

    async def test_cfo_has_controlling_permissions(self, client: httpx.AsyncClient, role_tokens: dict):
        resp = await client.get("/auth/me/permissions", headers=_h(role_tokens, "cfo"))
        perms = set(resp.json()["permissions"])
        assert "controlling:read" in perms
        assert "reports:read" in perms
        assert "budget:delete" in perms

    async def test_department_head_permissions(self, client: httpx.AsyncClient, role_tokens: dict):
        resp = await client.get("/auth/me/permissions", headers=_h(role_tokens, "department_head"))
        perms = set(resp.json()["permissions"])
        assert "orders:create" in perms
        assert "controlling:read" in perms
        # dept_head should NOT have accounting create
        assert "accounting:create" not in perms


class TestUserSwitchPermissions:
    """Admin switches user and gets correct permissions for switched user."""

    async def test_switch_to_reviewer_and_check_permissions(
        self, client: httpx.AsyncClient, admin_headers: dict, role_tokens: dict,
    ):
        # Get list of users
        resp = await client.get("/admin/users?limit=200", headers=admin_headers)
        assert resp.status_code == 200
        users = resp.json()["items"] if "items" in resp.json() else resp.json()

        # Find a reviewer user
        reviewer = next((u for u in users if u["role"] == "reviewer" and u["is_active"]), None)
        if not reviewer:
            pytest.skip("No active reviewer user found")

        # Switch to reviewer
        resp = await client.post(f"/auth/switch-user/{reviewer['id']}", headers=admin_headers)
        assert resp.status_code == 200
        reviewer_token = resp.json()["token"]
        reviewer_headers = auth_header(reviewer_token)

        # Check permissions as reviewer
        resp = await client.get("/auth/me/permissions", headers=reviewer_headers)
        assert resp.status_code == 200
        perms = set(resp.json()["permissions"])

        # Reviewer should see invoices but not admin
        assert "invoices:read" in perms
        assert not any(p.startswith("admin.") for p in perms)

        # Reviewer should NOT be able to access admin endpoints
        resp = await client.get("/admin/users", headers=reviewer_headers)
        assert resp.status_code == 403


class TestPermissionToggle:
    """Admin can grant/revoke permissions and changes take effect."""

    async def test_revoke_and_regrant_permission(
        self, client: httpx.AsyncClient, admin_headers: dict, role_tokens: dict,
    ):
        # 1. Get the matrix to find the "invoices:approve" permission for reviewer
        resp = await client.get("/admin/permissions/matrix", headers=admin_headers)
        data = resp.json()

        approve_perm = next(
            (p for p in data["permissions"] if p["resource"] == "invoices" and p["action"] == "approve"),
            None,
        )
        if not approve_perm:
            pytest.skip("invoices:approve permission not found")

        reviewer_perms = set(data["granted"].get("reviewer", []))
        had_permission = approve_perm["id"] in reviewer_perms

        # 2. Verify reviewer currently has invoices:approve
        resp = await client.get("/auth/me/permissions", headers=_h(role_tokens, "reviewer"))
        initial_perms = set(resp.json()["permissions"])
        assert "invoices:approve" in initial_perms, "Reviewer should start with invoices:approve"

        # 3. Revoke invoices:approve from reviewer
        resp = await client.put("/admin/permissions/matrix", json={
            "role": "reviewer",
            "permission_id": approve_perm["id"],
            "granted": False,
        }, headers=admin_headers)
        assert resp.status_code == 200

        # 4. Verify reviewer no longer has it
        resp = await client.get("/auth/me/permissions", headers=_h(role_tokens, "reviewer"))
        after_revoke = set(resp.json()["permissions"])
        assert "invoices:approve" not in after_revoke, "Permission should be revoked"

        # 5. Re-grant it
        resp = await client.put("/admin/permissions/matrix", json={
            "role": "reviewer",
            "permission_id": approve_perm["id"],
            "granted": True,
        }, headers=admin_headers)
        assert resp.status_code == 200

        # 6. Verify it's back
        resp = await client.get("/auth/me/permissions", headers=_h(role_tokens, "reviewer"))
        after_regrant = set(resp.json()["permissions"])
        assert "invoices:approve" in after_regrant, "Permission should be restored"

    async def test_cannot_toggle_admin_permissions(
        self, client: httpx.AsyncClient, admin_headers: dict,
    ):
        """Even though UI prevents it, verify toggling admin perms works without error
        (admin has implicit bypass, so the toggle is cosmetic)."""
        resp = await client.get("/admin/permissions/matrix", headers=admin_headers)
        data = resp.json()
        any_perm = data["permissions"][0]

        # This should succeed (adding/removing from admin role_permissions table)
        # but admin still passes all checks due to hardcoded bypass
        resp = await client.put("/admin/permissions/matrix", json={
            "role": "admin",
            "permission_id": any_perm["id"],
            "granted": False,
        }, headers=admin_headers)
        assert resp.status_code == 200

        # Re-grant to keep clean state
        resp = await client.put("/admin/permissions/matrix", json={
            "role": "admin",
            "permission_id": any_perm["id"],
            "granted": True,
        }, headers=admin_headers)
        assert resp.status_code == 200

    async def test_non_admin_cannot_toggle(self, client: httpx.AsyncClient, role_tokens: dict):
        resp = await client.put("/admin/permissions/matrix", json={
            "role": "reviewer",
            "permission_id": "fake-id",
            "granted": True,
        }, headers=_h(role_tokens, "cfo"))
        assert resp.status_code == 403
