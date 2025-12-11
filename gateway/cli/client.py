from __future__ import annotations

from typing import Any, Optional

import httpx

from .config import CLIConfig, get_config


class GatewayClient:
    def __init__(self, config: CLIConfig | None = None) -> None:
        self.config = config or get_config()
        headers: dict[str, str] = {}
        if self.config.api_key:
            headers["x-api-key"] = self.config.api_key
        self._client = httpx.AsyncClient(
            base_url=self.config.base_url,
            headers=headers,
            timeout=20,
        )

    async def __aenter__(self) -> "GatewayClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def close(self) -> None:
        await self._client.aclose()

    async def execute_command(self, command_text: str) -> httpx.Response:
        return await self._client.post("/commands", json={"command_text": command_text})

    async def list_history(self) -> httpx.Response:
        return await self._client.get("/commands")

    async def get_me(self) -> httpx.Response:
        return await self._client.get("/users/me")

    async def create_user(self, username: str, role: str, credits: Optional[int]) -> httpx.Response:
        payload: dict[str, Any] = {"username": username, "role": role}
        if credits is not None:
            payload["credits"] = credits
        return await self._client.post("/users", json=payload)

    async def list_users(self) -> httpx.Response:
        return await self._client.get("/users")

    async def update_credits(self, username: str, credits: int) -> httpx.Response:
        users_resp = await self.list_users()
        if users_resp.status_code != 200:
            return users_resp
        users = users_resp.json()
        target = next((u for u in users if u.get("username") == username), None)
        if not target:
            raise ValueError(f"user '{username}' not found")
        user_id = target["id"]
        return await self._client.patch(f"/users/{user_id}", json={"credits": credits})

    async def create_rule(self, pattern: str, action: str, priority: int) -> httpx.Response:
        return await self._client.post(
            "/rules",
            json={"pattern": pattern, "action": action, "priority": priority},
        )

    async def get_rules(self) -> httpx.Response:
        return await self._client.get("/rules")

    async def delete_rule(self, rule_id: int) -> httpx.Response:
        return await self._client.delete(f"/rules/{rule_id}")

    async def list_pending_approvals(self) -> httpx.Response:
        return await self._client.get("/commands/audit", params={"action_taken": "WAITING_APPROVAL"})

    async def submit_approval(self, command_id: int, decision: bool) -> httpx.Response:
        return await self._client.post(
            f"/commands/{command_id}/approve",
            json={"approved": decision},
        )

    async def audit_commands(
        self,
        user_id: int | None = None,
        rule_id: int | None = None,
        action_taken: str | None = None,
    ) -> httpx.Response:
        params: dict[str, object] = {}
        if user_id is not None:
            params["user_id"] = user_id
        if rule_id is not None:
            params["rule_id"] = rule_id
        if action_taken is not None:
            params["action_taken"] = action_taken
        return await self._client.get("/commands/audit", params=params)
