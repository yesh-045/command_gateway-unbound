from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class CLIConfig:
    base_url: str
    api_key: str | None


def get_config() -> CLIConfig:
    base_url = os.getenv("GATEWAY_BASE_URL", "http://localhost:8000").rstrip("/")
    api_key = os.getenv("GATEWAY_API_KEY")
    return CLIConfig(base_url=base_url, api_key=api_key)
