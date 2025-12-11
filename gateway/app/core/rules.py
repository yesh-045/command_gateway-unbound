from __future__ import annotations

import re
import time
from typing import Optional, Sequence

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.db.models import Rule

_REGEX_BUDGET_SECONDS = 0.1
_SENTINEL = "x" * 4096


def validate_regex(pattern: str) -> re.Pattern[str]:
    start = time.perf_counter()
    try:
        compiled = re.compile(pattern)
    except re.error as exc:  # surface clear message to admin
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"invalid regex: {exc}",
        ) from exc

    # quick-and-simple runaway guard
    compiled.search(_SENTINEL)
    duration = time.perf_counter() - start
    if duration > _REGEX_BUDGET_SECONDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="regex too slow or complex; simplify pattern",
        )
    return compiled


async def get_ordered_rules(session: AsyncSession) -> list[Rule]:
    result = await session.execute(select(Rule).order_by(Rule.priority, Rule.id))
    return list(result.scalars().all())


def match_rule(command_text: str, rules: Sequence[Rule]) -> Optional[Rule]:
    for rule in rules:
        try:
            compiled = re.compile(rule.pattern)
        except re.error:
            # Already validated on insert; skip if database contains legacy bad data
            continue
        if compiled.search(command_text):
            return rule
    return None
