from __future__ import annotations

import asyncio
import random
from datetime import datetime

from app.db.db import async_session_factory
from app.db.models import Command


async def _execute_command(command_id: int, command_text: str) -> None:
    await asyncio.sleep(random.uniform(0.5, 1.5))

    async with async_session_factory() as session:
        command = await session.get(Command, command_id)
        if not command:
            return

        # If command was already handled (e.g., approved flow), do not double-execute
        if command.action_taken not in {"PENDING", "EXECUTED", "WAITING_APPROVAL"}:
            return

        command.action_taken = "EXECUTED"
        command.executed_at = datetime.utcnow()
        command.result = f"mock: would run: {command_text}"
        await session.commit()


async def schedule_command_execution(command_id: int, command_text: str) -> None:
    asyncio.create_task(_execute_command(command_id, command_text))
