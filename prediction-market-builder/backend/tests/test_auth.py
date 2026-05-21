"""Tests for auth endpoints — register, login, token validation."""


async def test_register(client):
    resp = await client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "strongpass123",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "user_id" in data


async def test_login(client):
    await client.post("/api/auth/register", json={
        "email": "login@example.com",
        "password": "strongpass123",
    })
    resp = await client.post("/api/auth/login", json={
        "email": "login@example.com",
        "password": "strongpass123",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data


async def test_register_duplicate_email(client):
    await client.post("/api/auth/register", json={
        "email": "dup@example.com",
        "password": "strongpass123",
    })
    resp = await client.post("/api/auth/register", json={
        "email": "dup@example.com",
        "password": "strongpass123",
    })
    assert resp.status_code == 400


async def test_login_invalid_credentials(client):
    resp = await client.post("/api/auth/login", json={
        "email": "nobody@example.com",
        "password": "wrongpass",
    })
    assert resp.status_code == 401
