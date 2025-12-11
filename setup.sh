#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$ROOT_DIR/.env"
EXAMPLE_FILE="$ROOT_DIR/.env.example"
VENV_DIR="$ROOT_DIR/.venv"

if [[ ! -f "$ENV_FILE" && -f "$EXAMPLE_FILE" ]]; then
  cp "$EXAMPLE_FILE" "$ENV_FILE"
  echo "Created .env from .env.example"
fi

if [[ ! -d "$VENV_DIR" ]]; then
  python -m venv "$VENV_DIR"
  echo "Created virtualenv at $VENV_DIR"
fi

# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"

pip install --upgrade pip
pip install -r "$ROOT_DIR/gateway/requirements.txt"

echo "Environment ready. Activate with: source .venv/bin/activate"
echo "Run API: uvicorn app.main:app --app-dir gateway/app --reload"
