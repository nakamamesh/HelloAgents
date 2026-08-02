"""Phase 2 registry + machine API tests (requires Postgres)."""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.main import create_app


@pytest.fixture
def admin_headers() -> dict[str, str]:
    return {"X-Admin-Key": get_settings().admin_api_key}


@pytest.fixture
async def client():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_agent_listing_crud_and_machine_auth(client: AsyncClient, admin_headers: dict):
    slug = f"growth-hacker-{uuid.uuid4().hex[:8]}"

    # create agent
    r = await client.post(
        "/agents",
        headers=admin_headers,
        json={
            "slug": slug,
            "name": "Growth Hacker",
            "role": "seller",
            "description": "seed seller",
            "referral_budget": "10.000000",
            "reputation_score": "1.000000",
        },
    )
    assert r.status_code == 201, r.text
    created = r.json()
    assert created["slug"] == slug
    assert created["api_key"].startswith("ha_live_")
    agent_id = created["id"]
    api_key = created["api_key"]

    # reject float money
    bad = await client.post(
        "/agents",
        headers=admin_headers,
        json={"slug": "x-float", "name": "X", "role": "buyer", "referral_budget": 1.5},
    )
    assert bad.status_code == 422

    # admin listing create
    r = await client.post(
        "/listings",
        headers=admin_headers,
        json={
            "agent_id": agent_id,
            "title": "SEO audit",
            "price_usdc": "5.500000",
            "description": "one-shot audit",
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["price_usdc"] == "5.500000"

    # machine: me via API key
    r = await client.get("/agent/me", headers={"X-API-Key": api_key})
    assert r.status_code == 200
    assert r.json()["id"] == agent_id

    # machine: exchange JWT
    r = await client.post("/agent/token", headers={"X-API-Key": api_key})
    assert r.status_code == 200
    token = r.json()["access_token"]

    r = await client.get("/agent/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200

    # machine: create own listing
    r = await client.post(
        "/agent/listings",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "Content pack", "price_usdc": "12.000000", "capabilities": ["copy"]},
    )
    assert r.status_code == 201, r.text

    r = await client.get("/agent/listings", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert len(r.json()) >= 2

    # unauthorized
    r = await client.get("/agents")
    assert r.status_code == 401
