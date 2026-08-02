from datetime import datetime, timedelta, timezone
from hashlib import sha256
from typing import Any
from uuid import UUID

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.session import get_db
from app.models.orm import Agent, AgentStatus

bearer_scheme = HTTPBearer(auto_error=False)


def hash_api_key(raw_key: str) -> str:
    return sha256(raw_key.encode("utf-8")).hexdigest()


def create_agent_jwt(agent_id: UUID, *, expires_minutes: int | None = None) -> str:
    settings = get_settings()
    ttl = expires_minutes if expires_minutes is not None else settings.jwt_expires_minutes
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(agent_id),
        "typ": "agent",
        "iat": now,
        "exp": now + timedelta(minutes=ttl),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_agent_jwt(token: str) -> UUID:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc
    if payload.get("typ") != "agent" or not payload.get("sub"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token claims")
    return UUID(payload["sub"])


async def require_admin(
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
) -> None:
    settings = get_settings()
    if not x_admin_key or x_admin_key != settings.admin_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin key required")


async def get_current_agent(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
) -> Agent:
    """Accept Bearer JWT or X-API-Key / Bearer ha_… API key."""
    raw_key: str | None = x_api_key
    token: str | None = credentials.credentials if credentials else None

    agent: Agent | None = None

    if token and token.startswith("ha_"):
        raw_key = token
        token = None

    if token:
        agent_id = decode_agent_jwt(token)
        agent = await db.get(Agent, agent_id)
    elif raw_key:
        digest = hash_api_key(raw_key)
        result = await db.execute(select(Agent).where(Agent.api_key_hash == digest))
        agent = result.scalar_one_or_none()
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Provide Bearer JWT or X-API-Key",
        )

    if agent is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown credentials")
    if agent.status == AgentStatus.SUSPENDED:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Agent suspended")
    return agent
