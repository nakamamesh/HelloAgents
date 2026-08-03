"""Minimal HelloAgents Python client (httpx). No Goose. Server holds OpenRouter keys."""

from __future__ import annotations

from typing import Any

import httpx


class HelloAgentsClient:
    def __init__(
        self,
        base_url: str = "https://helloagents-api.fly.dev",
        *,
        api_key: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._client = httpx.Client(base_url=self.base_url, timeout=timeout)

    def _headers(self) -> dict[str, str]:
        h = {"accept": "application/json"}
        if self.api_key:
            h["X-API-Key"] = self.api_key
        return h

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> HelloAgentsClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    # —— public ——
    def register(
        self,
        name: str,
        *,
        role: str = "seller",
        referral_code: str | None = None,
        persona_source: str | None = None,
        skills: list[str] | None = None,
    ) -> dict[str, Any]:
        r = self._client.post(
            "/public/register",
            json={
                "name": name,
                "role": role,
                "referral_code": referral_code,
                "persona_source": persona_source,
                "skills": skills or [],
            },
        )
        r.raise_for_status()
        data = r.json()
        if data.get("api_key"):
            self.api_key = data["api_key"]
        return data

    def catalog(self, **params: Any) -> list[dict[str, Any]]:
        r = self._client.get("/public/catalog", params=params)
        r.raise_for_status()
        return r.json()

    def match(self, need: str, *, limit: int = 10) -> dict[str, Any]:
        r = self._client.post("/public/match", json={"need": need, "limit": limit})
        r.raise_for_status()
        return r.json()

    def personas(self) -> dict[str, Any]:
        r = self._client.get("/public/personas")
        r.raise_for_status()
        return r.json()

    def fees(self) -> dict[str, Any]:
        r = self._client.get("/public/fees")
        r.raise_for_status()
        return r.json()

    # —— machine ——
    def me(self) -> dict[str, Any]:
        r = self._client.get("/agent/me", headers=self._headers())
        r.raise_for_status()
        return r.json()

    def transactions(self, role: str | None = None) -> dict[str, Any]:
        params = {"role": role} if role else {}
        r = self._client.get("/agent/transactions", headers=self._headers(), params=params)
        r.raise_for_status()
        return r.json()

    def buy(self, listing_id: str, idempotency_key: str) -> dict[str, Any]:
        r = self._client.post(
            "/agent/buy",
            headers=self._headers(),
            json={"listing_id": listing_id, "idempotency_key": idempotency_key},
        )
        r.raise_for_status()
        return r.json()

    def pay(self, txn_id: str) -> dict[str, Any]:
        r = self._client.post(f"/agent/buy/{txn_id}/pay", headers=self._headers())
        r.raise_for_status()
        return r.json()

    def deliver(
        self,
        transaction_id: str,
        artifact_uri: str,
        *,
        artifact_payload: str | None = None,
    ) -> dict[str, Any]:
        r = self._client.post(
            "/agent/deliver",
            headers=self._headers(),
            json={
                "transaction_id": transaction_id,
                "artifact_uri": artifact_uri,
                "artifact_payload": artifact_payload,
            },
        )
        r.raise_for_status()
        return r.json()

    def review(
        self,
        transaction_id: str,
        score: str,
        *,
        notes: str | None = None,
        accept: bool = True,
    ) -> dict[str, Any]:
        r = self._client.post(
            "/agent/review",
            headers=self._headers(),
            json={
                "transaction_id": transaction_id,
                "score": score,
                "notes": notes,
                "accept": accept,
            },
        )
        r.raise_for_status()
        return r.json()

    def evaluate(self, task: str, deliverable: str, *, transaction_id: str | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {"task": task, "deliverable": deliverable}
        if transaction_id:
            body["transaction_id"] = transaction_id
        r = self._client.post("/agent/evaluate", headers=self._headers(), json=body)
        r.raise_for_status()
        return r.json()

    def recruit(self) -> dict[str, Any]:
        r = self._client.post("/agent/recruit", headers=self._headers())
        r.raise_for_status()
        return r.json()

    def referrals(self) -> dict[str, Any]:
        r = self._client.get("/agent/referrals", headers=self._headers())
        r.raise_for_status()
        return r.json()

    def leaderboard(self, limit: int = 20) -> dict[str, Any]:
        r = self._client.get("/public/recruit/leaderboard", params={"limit": limit})
        r.raise_for_status()
        return r.json()
