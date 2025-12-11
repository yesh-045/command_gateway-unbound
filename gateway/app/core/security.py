from __future__ import annotations

import secrets
import time
from collections import defaultdict
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.db import get_session
from app.db.models import User

settings = get_settings()
api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)
_rate_counters: dict[str, tuple[int, int]] = defaultdict(lambda: (0, 0))


def generate_api_key() -> str:
    return secrets.token_urlsafe(32)


async def enforce_rate_limit(api_key: Optional[str] = Depends(api_key_header)) -> None:
    limit = settings.RATE_LIMIT_PER_MINUTE
    if not api_key or limit <= 0:
        return

    now_window = int(time.time() // 60)
    window, count = _rate_counters[api_key]
    if window != now_window:
        _rate_counters[api_key] = (now_window, 1)
        return

    if count >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="rate limit exceeded",
        )

    _rate_counters[api_key] = (window, count + 1)


async def get_current_user(
    api_key: Optional[str] = Depends(api_key_header),
    session: AsyncSession = Depends(get_session),
) -> User:
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing API key",
        )

    result = await session.execute(select(User).where(User.api_key == api_key))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid API key",
        )
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="admin access required",
        )
    return user


async def require_admin_or_bootstrap(
    session: AsyncSession = Depends(get_session),
    api_key: Optional[str] = Depends(api_key_header),
) -> Optional[User]:
    """Allow first user creation when no users exist; otherwise require admin."""
    has_user = await session.execute(select(User.id))
    if not has_user.first():
        return None

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing API key",
        )

    result = await session.execute(select(User).where(User.api_key == api_key))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid API key",
        )
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="admin access required",
        )
    return user
