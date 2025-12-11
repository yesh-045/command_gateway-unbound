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
users_app = typer.Typer(help="Admin user management")


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


@users_app.command("create")
def create_user() -> None:
    username = typer.prompt("Username")
    role = typer.prompt("Role", default="member")
    credits_input = typer.prompt("Credits", default="", show_default=False)
    credits: Optional[int] = int(credits_input) if credits_input else None

    async def _run() -> None:
        async with GatewayClient(get_config()) as client:
            resp = await client.create_user(username=username, role=role, credits=credits)
            if resp.status_code == 201:
                data = resp.json()
                console.print("User created. API key: [bold]{}[/]".format(data.get("api_key")))
            else:
                _print_error(resp)

    asyncio.run(_run())


@users_app.command("list")
def list_users() -> None:
    async def _run() -> None:
        async with GatewayClient(get_config()) as client:
            resp = await client.list_users()
            if resp.status_code != 200:
                _print_error(resp)
                return
            table = Table("id", "username", "role", "credits")
            for user in resp.json():
                table.add_row(
                    str(user.get("id")),
                    str(user.get("username")),
                    str(user.get("role")),
                    str(user.get("credits")),
                )
            console.print(table)

    asyncio.run(_run())


@users_app.command("credits")
def update_credits() -> None:
    username = typer.prompt("Username")
    new_value = typer.prompt("New credits", type=int)

    async def _run() -> None:
        async with GatewayClient(get_config()) as client:
            try:
                resp = await client.update_credits(username=username, credits=new_value)
            except ValueError as exc:
                console.print(f"[red]{exc}[/]")
                return
            if resp.status_code == 200:
                data = resp.json()
                console.print(
                    f"Credits updated for {data.get('username')}: {data.get('credits')}"
                )
            else:
                _print_error(resp)

    asyncio.run(_run())
