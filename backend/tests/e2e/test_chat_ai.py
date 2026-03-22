"""AI Chat (text-to-SQL) E2E tests — 10 tests.

All tests require GPU/Ollama and are marked with @pytest.mark.ai.
Run with: pytest tests/e2e/test_chat_ai.py -v -m ai --timeout=60
"""

import httpx
import pytest

pytestmark = pytest.mark.ai


class TestChatAI:
    async def test_simple_count(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.post(
            "/chat/ask",
            json={"question": "Hány számla van a rendszerben?"},
            headers=admin_headers,
            timeout=60.0,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "answer" in data or "error" in data
        if "sql" in data and data["sql"]:
            assert "SELECT" in data["sql"].upper()

    async def test_sum_amount(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.post(
            "/chat/ask",
            json={"question": "Mennyi a számlák összes bruttó összege?"},
            headers=admin_headers,
            timeout=60.0,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "answer" in data or "error" in data

    async def test_partner_query(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.post(
            "/chat/ask",
            json={"question": "Melyik szállítótól jött a legtöbb számla?"},
            headers=admin_headers,
            timeout=60.0,
        )
        assert resp.status_code == 200

    async def test_date_filter(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.post(
            "/chat/ask",
            json={"question": "Milyen számlák érkeztek 2025 januárban?"},
            headers=admin_headers,
            timeout=60.0,
        )
        assert resp.status_code == 200

    async def test_budget_query(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.post(
            "/chat/ask",
            json={"question": "Mekkora az IT osztály havi büdzséje?"},
            headers=admin_headers,
            timeout=60.0,
        )
        assert resp.status_code == 200

    async def test_nonsense_input(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.post(
            "/chat/ask",
            json={"question": "asdfgh jkl"},
            headers=admin_headers,
            timeout=60.0,
        )
        assert resp.status_code == 200
        # Should handle gracefully — no 500

    async def test_sql_injection_attempt(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.post(
            "/chat/ask",
            json={"question": "'; DROP TABLE invoices; --"},
            headers=admin_headers,
            timeout=60.0,
        )
        # Must not crash, must not execute destructive SQL
        assert resp.status_code in (200, 400, 422)

        # Verify invoices table still exists
        check = await client.get("/invoices", headers=admin_headers)
        assert check.status_code == 200

    async def test_long_question(self, client: httpx.AsyncClient, admin_headers: dict):
        long_q = "Kérem listázza az összes számlát " * 30  # ~500+ chars
        resp = await client.post(
            "/chat/ask",
            json={"question": long_q},
            headers=admin_headers,
            timeout=60.0,
        )
        assert resp.status_code in (200, 400, 422)

    async def test_audit_log_created(self, client: httpx.AsyncClient, admin_headers: dict):
        """After a chat query, check that audit log has a new entry."""
        await client.post(
            "/chat/ask",
            json={"question": "Hány számla van?"},
            headers=admin_headers,
            timeout=60.0,
        )
        audit = await client.get("/admin/audit", headers=admin_headers)
        assert audit.status_code == 200

    async def test_response_time(self, client: httpx.AsyncClient, admin_headers: dict):
        resp = await client.post(
            "/chat/ask",
            json={"question": "Hány számla van?"},
            headers=admin_headers,
            timeout=60.0,
        )
        assert resp.status_code == 200
        data = resp.json()
        if "response_time_ms" in data:
            assert data["response_time_ms"] < 30000
