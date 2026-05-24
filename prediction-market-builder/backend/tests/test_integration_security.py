"""Integration + E2E tests for Task 4.2: Security Hardening.

Tests the full FastAPI stack: rate limiter, security headers,
encryption, JWT refresh flow, and auth endpoints.
"""
import pytest
from httpx import AsyncClient, ASGITransport


class TestSecurityHeaders:
    """Integration: every response carries security headers."""

    @pytest.mark.asyncio
    async def test_health_has_security_headers(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.headers.get("x-content-type-options") == "nosniff"
        assert resp.headers.get("x-frame-options") == "DENY"
        assert resp.headers.get("x-xss-protection") == "1; mode=block"
        assert resp.headers.get("strict-transport-security") == "max-age=31536000; includeSubDomains"
        assert resp.headers.get("referrer-policy") == "strict-origin-when-cross-origin"


class TestRateLimiterIntegration:
    """Integration: rate limiter middleware blocks excess requests."""

    @pytest.mark.asyncio
    async def test_rate_limit_on_auth_endpoint(self, client: AsyncClient):
        login_payload = {"email": "spam@test.com", "password": "password123"}
        for _ in range(3):
            resp = await client.post("/api/auth/login", json=login_payload)
            assert resp.status_code == 401
        resp = await client.post("/api/auth/login", json=login_payload)
        assert resp.status_code == 429

    @pytest.mark.asyncio
    async def test_health_bypasses_rate_limit(self, client: AsyncClient):
        for _ in range(100):
            resp = await client.get("/health")
            assert resp.status_code == 200


class TestAuthE2E:
    """E2E: full authentication lifecycle."""

    @pytest.mark.asyncio
    async def test_register_then_login_then_refresh(self, client: AsyncClient):
        register = await client.post("/api/auth/register", json={
            "email": "e2e@test.com", "password": "strongpass123",
        })
        assert register.status_code == 200
        data = register.json()
        assert "access_token" in data
        assert "refresh_token" in data
        user_id = data["user_id"]

        me = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {data['access_token']}"})
        assert me.status_code == 200
        assert me.json()["email"] == "e2e@test.com"

        refreshed = await client.post("/api/auth/refresh", json={"refresh_token": data["refresh_token"]})
        assert refreshed.status_code == 200
        new_tokens = refreshed.json()
        assert new_tokens["access_token"] != data["access_token"]

        me2 = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {new_tokens['access_token']}"})
        assert me2.status_code == 200
        assert me2.json()["id"] == user_id

    @pytest.mark.asyncio
    async def test_access_token_rejected_on_protected_route(self, client: AsyncClient):
        me = await client.get("/api/auth/me", headers={"Authorization": "Bearer invalid-token"})
        assert me.status_code == 401

    @pytest.mark.asyncio
    async def test_password_minimum_length(self, client: AsyncClient):
        resp = await client.post("/api/auth/register", json={
            "email": "short@test.com", "password": "123",
        })
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient):
        await client.post("/api/auth/register", json={
            "email": "dup@test.com", "password": "strongpass123",
        })
        resp = await client.post("/api/auth/register", json={
            "email": "dup@test.com", "password": "strongpass456",
        })
        assert resp.status_code == 400
        assert "already registered" in resp.text.lower()


class TestEncryptionIntegration:
    """Integration: encrypted keys appear in /me endpoint."""

    @pytest.mark.asyncio
    async def test_user_has_encrypted_key_status(self, client: AsyncClient):
        reg = await client.post("/api/auth/register", json={
            "email": "keytest@test.com", "password": "strongpass123",
        })
        token = reg.json()["access_token"]

        me = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200
        data = me.json()
        assert "has_polymarket_key" in data
        assert data["has_polymarket_key"] is False
