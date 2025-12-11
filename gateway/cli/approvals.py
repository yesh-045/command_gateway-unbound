from __future__ import annotations

import asyncio
import json

import typer
from rich.console import Console
from rich.table import Table

from .client import GatewayClient
from .config import get_config

console = Console()
approvals_app = typer.Typer(help="Admin approval flow")


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


@approvals_app.command("pending")
def pending() -> None:
    async def _run() -> None:
        async with GatewayClient(get_config()) as client:
            resp = await client.list_pending_approvals()
            if resp.status_code != 200:
                _print_error(resp)
                return
            table = Table("id", "command", "user_id", "action", "matched_rule_id", "created_at")
            for cmd in resp.json():
                table.add_row(
                    str(cmd.get("id")),
                    str(cmd.get("command_text")),
                    str(cmd.get("user_id")),
                    str(cmd.get("action_taken")),
                    str(cmd.get("matched_rule_id")),
                    str(cmd.get("created_at")),
                )
            console.print(table)

    asyncio.run(_run())


@approvals_app.command("approve")
def approve(
    command_id: int = typer.Argument(None, help="Command id to approve; prompts if omitted"),
) -> None:
    if command_id is None:
        command_id = typer.prompt("Command id", type=int)

    async def _run() -> None:
        async with GatewayClient(get_config()) as client:
            resp = await client.submit_approval(command_id, decision=True)
            if resp.status_code == 200:
                console.print(f"Command {command_id} approved")
            else:
                _print_error(resp)

    asyncio.run(_run())


@approvals_app.command("reject")
def reject(
    command_id: int = typer.Argument(None, help="Command id to reject; prompts if omitted"),
) -> None:
    if command_id is None:
        command_id = typer.prompt("Command id", type=int)

    async def _run() -> None:
        async with GatewayClient(get_config()) as client:
            resp = await client.submit_approval(command_id, decision=False)
            if resp.status_code == 200:
                console.print(f"Command {command_id} rejected")
            else:
                _print_error(resp)

    asyncio.run(_run())
