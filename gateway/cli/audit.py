from __future__ import annotations

import asyncio
import json
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from .client import GatewayClient
from .config import get_config

console = Console()
audit_app = typer.Typer(help="Admin audit log")


def _print_error(resp) -> None:
    try:
        payload = resp.json()
    except Exception:
        console.print(f"[red]Error {resp.status_code}: {resp.text}[/]")
        return
    detail = payload.get("detail", payload)
    if isinstance(detail, dict):
        detail = json.dumps(detail)
    console.print(f"[red]Error {resp.status_code}: {detail}[/]")


audit_action_option = typer.Option(None, help="Filter by action (PENDING/EXECUTED/REJECTED/WAITING_APPROVAL)")
audit_user_option = typer.Option(None, help="Filter by user id")
audit_rule_option = typer.Option(None, help="Filter by rule id")


@audit_app.command("list")
def list_audit(
    user_id: Optional[int] = audit_user_option,
    rule_id: Optional[int] = audit_rule_option,
    action_taken: Optional[str] = audit_action_option,
) -> None:
    """Show audit log entries with optional filters."""

    async def _run() -> None:
        async with GatewayClient(get_config()) as client:
            resp = await client.audit_commands(user_id=user_id, rule_id=rule_id, action_taken=action_taken)
            if resp.status_code != 200:
                _print_error(resp)
                return
            table = Table(
                "id",
                "user_id",
                "action",
                "command",
                "rule_id",
                "cost",
                "result",
                "created_at",
                "executed_at",
            )
            for cmd in resp.json():
                table.add_row(
                    str(cmd.get("id")),
                    str(cmd.get("user_id")),
                    str(cmd.get("action_taken")),
                    str(cmd.get("command_text")),
                    str(cmd.get("matched_rule_id")),
                    str(cmd.get("cost")),
                    str(cmd.get("result")),
                    str(cmd.get("created_at")),
                    str(cmd.get("executed_at")),
                )
            console.print(table)

    asyncio.run(_run())
