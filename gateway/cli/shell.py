from __future__ import annotations

import asyncio
import json
from typing import Any, Optional

import typer
from rich.console import Console

from .client import GatewayClient
from .config import get_config

console = Console()


async def _fetch_credits(client: GatewayClient) -> Optional[int]:
    try:
        resp = await client.get_me()
        if resp.status_code == 200:
            data = resp.json()
            return data.get("credits")
    except Exception:
        return None
    return None


async def _print_error(resp) -> None:
    try:
        payload = resp.json()
    except Exception:
        console.print(f"[red]Error {resp.status_code}: {resp.text}[/]")
        return

    detail: Any = payload.get("detail", payload)
    if isinstance(detail, dict):
        detail = json.dumps(detail)
    console.print(f"[red]Error {resp.status_code}: {detail}[/]")


async def _print_command_result(data: dict[str, Any], client: GatewayClient) -> None:
    action = data.get("action_taken", "")
    rule_id = data.get("matched_rule_id")
    cost = data.get("cost")
    tx_id = data.get("tx_id")
    result = data.get("result")
    credits = await _fetch_credits(client)

    if action == "WAITING_APPROVAL":
        message = "WAITING_APPROVAL | approval requested"
        if rule_id:
            message += f" | rule id: {rule_id}"
        console.print(message)
    elif action == "REJECTED":
        reason = result or "Rejected"
        message = f"REJECTED | {reason}"
        if rule_id:
            message += f" | rule id: {rule_id}"
        console.print(message)
    elif action == "PENDING":
        message = f"PENDING | cost: {cost}"
        if tx_id:
            message += f" | tx: {tx_id}"
        console.print(message)
    elif action == "EXECUTED":
        message = f"EXECUTED | cost: {cost}"
        if result:
            message += f" | result: {result}"
        console.print(message)
    else:
        console.print(f"{action or 'UNKNOWN'} | {result or ''}")

    if credits is not None:
        console.print(f"credits: {credits}")


async def _session_loop() -> None:
    config = get_config()
    if not config.api_key:
        console.print("[red]Set GATEWAY_API_KEY before starting a session.[/]")
        return

    console.print("Command Gateway Session")
    console.print("Type raw command to execute it. Type 'exit' to quit.\n")

    async with GatewayClient(config) as client:
        while True:
            try:
                line = input("> ").strip()
            except EOFError:
                console.print()
                break

            if not line:
                continue
            if line.lower() in {"exit", "quit"}:
                break

            resp = await client.execute_command(line)
            if resp.status_code == 201:
                data = resp.json()
                await _print_command_result(data, client)
            else:
                await _print_error(resp)


def run_session() -> None:
    try:
        asyncio.run(_session_loop())
    except KeyboardInterrupt:
        console.print()
        return


def session_command() -> None:
    """Typer entrypoint wrapper."""
    run_session()
