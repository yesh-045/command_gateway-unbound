from __future__ import annotations

import asyncio
import logging
import smtplib
from email.message import EmailMessage
from typing import Sequence

import httpx

from app.core.config import get_settings
from app.db.models import Command, Rule, User

logger = logging.getLogger(__name__)
settings = get_settings()


def _format_message(command: Command, rule: Rule | None, requester: User, required: int) -> str:
    rule_desc = rule.pattern if rule else "DEFAULT"
    return (
        f"Command #{command.id} from {requester.username} requires approval\n"
        f"Command: {command.command_text}\n"
        f"Rule: {rule_desc}\n"
        f"Needed approvals: {required}\n"
    )


async def _send_telegram(message: str) -> None:
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(url, json={"chat_id": settings.TELEGRAM_CHAT_ID, "text": message})
    except Exception as exc:  # best-effort notification
        logger.warning("telegram notification failed: %s", exc)


def _send_email(message: str) -> None:
    if not settings.EMAIL_SMTP_HOST or not settings.EMAIL_FROM or not settings.EMAIL_TO:
        return
    email = EmailMessage()
    email["Subject"] = "Approval requested"
    email["From"] = settings.EMAIL_FROM
    email["To"] = settings.EMAIL_TO
    email.set_content(message)

    try:
        with smtplib.SMTP(settings.EMAIL_SMTP_HOST, settings.EMAIL_SMTP_PORT, timeout=10) as smtp:
            smtp.starttls()
            if settings.EMAIL_USERNAME and settings.EMAIL_PASSWORD:
                smtp.login(settings.EMAIL_USERNAME, settings.EMAIL_PASSWORD)
            smtp.send_message(email)
    except Exception as exc:  # best-effort notification
        logger.warning("email notification failed: %s", exc)


async def notify_approval_request(
    command: Command,
    rule: Rule | None,
    requester: User,
    admins: Sequence[User],
) -> None:
    if not admins:
        return

    required = max(1, command.required_approvals or settings.DEFAULT_APPROVAL_THRESHOLD)
    message = _format_message(command, rule, requester, required)

    tasks = []
    tasks.append(_send_telegram(message))
    tasks.append(asyncio.to_thread(_send_email, message))

    await asyncio.gather(*tasks, return_exceptions=True)
