from __future__ import annotations

import asyncio
import json

import typer
from rich.console import Console
from rich.table import Table

from .client import GatewayClient
from .config import get_config

console = Console()
rules_app = typer.Typer(help="Admin rule management")


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


@rules_app.command("create")
def create_rule() -> None:
    pattern = typer.prompt("Pattern (regex)")
    action = typer.prompt("Action", default="AUTO_REJECT")
    priority = typer.prompt("Priority", default=100, type=int)

    async def _run() -> None:
        async with GatewayClient(get_config()) as client:
            resp = await client.create_rule(pattern=pattern, action=action, priority=priority)
            if resp.status_code == 201:
                data = resp.json()
                console.print(
                    f"Rule created id={data.get('id')} pattern={data.get('pattern')} action={data.get('action')} priority={data.get('priority')}"
                )
            else:
                _print_error(resp)

    asyncio.run(_run())


@rules_app.command("list")
def list_rules() -> None:
    async def _run() -> None:
        async with GatewayClient(get_config()) as client:
            resp = await client.get_rules()
            if resp.status_code != 200:
                _print_error(resp)
                return
            table = Table("id", "pattern", "action", "priority")
            for rule in resp.json():
                table.add_row(
                    str(rule.get("id")),
                    str(rule.get("pattern")),
                    str(rule.get("action")),
                    str(rule.get("priority")),
                )
            console.print(table)

    asyncio.run(_run())


@rules_app.command("delete")
def delete_rule(
    rule_id: int = typer.Argument(None, help="Rule id to delete; prompts if omitted"),
) -> None:
    if rule_id is None:
        rule_id = typer.prompt("Rule id", type=int)

    async def _run() -> None:
        async with GatewayClient(get_config()) as client:
            resp = await client.delete_rule(rule_id)
            if resp.status_code in (200, 204):
                console.print(f"Rule {rule_id} deleted")
            else:
                _print_error(resp)

    asyncio.run(_run())
