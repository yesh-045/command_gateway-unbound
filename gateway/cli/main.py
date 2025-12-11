from __future__ import annotations

import typer
from rich.console import Console

from .approvals import approvals_app
from .audit import audit_app
from .rules import rules_app
from .shell import session_command
from .users import users_app

app = typer.Typer(add_completion=False, help="Command Gateway CLI")
console = Console()


@app.callback(invoke_without_command=True)
def _entry(ctx: typer.Context) -> None:
    """Default entry: start interactive session when no subcommand is provided."""
    if ctx.invoked_subcommand is None:
        session_command()


@app.command("session")
def session() -> None:
    """Start an interactive command session."""
    session_command()


def _register_subcommands() -> None:
    app.add_typer(users_app, name="users")
    app.add_typer(rules_app, name="rules")
    app.add_typer(approvals_app, name="approvals")
    app.add_typer(audit_app, name="audit")


_register_subcommands()


def run() -> None:
    app()


if __name__ == "__main__":
    run()
