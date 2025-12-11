from __future__ import annotations

import argparse
import asyncio
import os
from typing import Any

import httpx

DEFAULT_RULES: list[dict[str, Any]] = [
    {"pattern": r"rm\s+-rf\s+/", "action": "AUTO_REJECT", "priority": 10},
    {"pattern": r":\(\)\{ :\|:& \};:", "action": "AUTO_REJECT", "priority": 20},
    {"pattern": r"mkfs\.\w+", "action": "AUTO_REJECT", "priority": 30},
    {"pattern": r"sudo\s+.*", "action": "REQUIRE_APPROVAL", "priority": 40, "approval_threshold": 2},
    {"pattern": r"chmod\s+777", "action": "REQUIRE_APPROVAL", "priority": 50, "approval_threshold": 2},
    {"pattern": r"chown\s+", "action": "REQUIRE_APPROVAL", "priority": 60, "approval_threshold": 2},
    {"pattern": r"docker\s+run", "action": "REQUIRE_APPROVAL", "priority": 70, "approval_threshold": 2, "user_thresholds": {"junior": 3, "lead": 1}},
    {"pattern": r"kubectl\s+apply", "action": "REQUIRE_APPROVAL", "priority": 80, "approval_threshold": 3, "user_thresholds": {"junior": 4, "senior": 2, "lead": 1}},
    {"pattern": r"systemctl\s+(stop|restart)", "action": "REQUIRE_APPROVAL", "priority": 90, "approval_threshold": 2},
    {"pattern": r"iptables|ufw", "action": "REQUIRE_APPROVAL", "priority": 100, "approval_threshold": 2},
    {"pattern": r"^(ls|pwd|whoami)$", "action": "AUTO_ACCEPT", "priority": 200},
    {"pattern": r"^(cat|head|tail)\s+", "action": "AUTO_ACCEPT", "priority": 210},
    {"pattern": r"^echo\s+", "action": "AUTO_ACCEPT", "priority": 220},
    {"pattern": r"git\s+(status|log|diff)", "action": "AUTO_ACCEPT", "priority": 230},
    {"pattern": r"^curl\s+https?://", "action": "REQUIRE_APPROVAL", "priority": 240, "approval_threshold": 2},
]

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed gateway rules")
    parser.add_argument("--api-key", help="Admin API key (or set GATEWAY_API_KEY)")
    parser.add_argument(
        "--base-url",
        default=os.getenv("GATEWAY_BASE_URL", "http://localhost:8000"),
        help="Gateway base URL",
    )
    return parser.parse_args()


async def main() -> None:
    args = _parse_args()
    api_key = args.api_key or os.getenv("GATEWAY_API_KEY")
    if not api_key:
        raise SystemExit("Provide --api-key or set GATEWAY_API_KEY")

    async with httpx.AsyncClient(
        base_url=args.base_url, headers={"x-api-key": api_key}, timeout=10
    ) as client:
        created = 0
        for rule in DEFAULT_RULES:
            resp = await client.post("/rules", json=rule)
            if resp.status_code == 201:
                created += 1
            elif resp.status_code == 409:
                continue
            else:
                print(f"Failed to create rule {rule['pattern']}: {resp.status_code} {resp.text}")
        print(f"Created {created} rules")


if __name__ == "__main__":
    asyncio.run(main())
