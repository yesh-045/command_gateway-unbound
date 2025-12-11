# Unbound Hackathon: Command Gateway

FastAPI + SQLModel gateway with regex rules, API-key auth, credits, approvals, and mock execution. SQLite by default;



## Highlights
- Regex rule engine with validation (rejects invalid/slow patterns before save)
- Actions: `AUTO_ACCEPT`, `AUTO_REJECT`, `REQUIRE_APPROVAL`
- Approval thresholds per rule plus per-seniority overrides (`junior/standard/senior/lead`)
- Credits deducted only on accept; concurrent-safe with async SQLModel
- Notifications: Telegram or SMTP (Gmail-friendly via App Password)
- CLI for users/rules/approvals/audit; seed script for 15 starter rules
- Mock execution worker; never runs real shell commands
## How It Works
1. Clients send commands with header `x-api-key`.
2. Ordered rules (`priority ASC, id ASC`) are compiled; invalid regex is rejected.
3. Action resolves to rule action or fallback `DEFAULT_RULE_ACTION`.
4. `REQUIRE_APPROVAL` stores `WAITING_APPROVAL`, sets `required_approvals`, notifies admins (Telegram/Email if configured), and auto-transitions to `PENDING` once threshold is met.
5. `AUTO_ACCEPT` deducts credits and schedules mock execution; `AUTO_REJECT` records rejection.
6. Worker marks `EXECUTED` and stores `result="mock: would run: <cmd>"`.

## Data Model (SQLModel)
- **users**: `username` UNIQUE, `api_key` UNIQUE, `role` ∈ {admin, member}, `seniority` (junior/standard/senior/lead), `credits`, `created_at`.
- **rules**: `pattern`, `action` ∈ {AUTO_ACCEPT, AUTO_REJECT, REQUIRE_APPROVAL}, `priority`, `approval_threshold`, `user_thresholds` (per-seniority override), `created_by`, `created_at`.
- **commands**: user FK, `command_text`, `matched_rule_id`, `action_taken` ∈ {PENDING, EXECUTED, REJECTED, FAILED, WAITING_APPROVAL}, `cost`, `required_approvals`, `result`, `tx_id`, timestamps.
- **approvals**: admin decisions (`decision`, `decided_at`), one per admin per command.
- Indexes on api_key, rule priority/id, command user/rule, approvals command.

## Rule Matching
- Order: `priority ASC, id ASC`.
- On create, compile regex; reject invalid or patterns taking >100ms on sentinel.
- Match via `regex.search(command_text)`; first match wins.
- No match → fallback action (default `AUTO_REJECT` or your env value).

## Command Flow (POST /commands)
1. Begin transaction; reload user row.
2. If credits ≤ 0 and action would be AUTO_ACCEPT → record `REJECTED`, return 403.
3. If AUTO_REJECT → record `REJECTED`, cost 0.
4. If REQUIRE_APPROVAL → record `WAITING_APPROVAL`, cost 0, set `required_approvals`, notify admins.
5. If AUTO_ACCEPT → deduct cost (default 1), record `PENDING`, commit, schedule mock execution.
6. Worker sleeps ~0.5–1.5s, sets `EXECUTED`, writes `result`, stamps `executed_at`.

## API Surface
- **Health**: `GET /health`, readiness `GET /`.
- **Auth**: header `x-api-key`; per-key rate limit (env `RATE_LIMIT_PER_MINUTE`).
- **Member**: `GET /users/me`, `POST /commands`, `GET /commands`, `GET /commands/{id}` (own/admin).
- **Admin**: `POST /users` (returns API key once), `GET /users`, `PATCH /users/{id}`; `POST /rules`, `GET /rules`, `PATCH /rules/{id}`, `DELETE /rules/{id}`, `POST /rules/test`; `POST /commands/{id}/approve`; `GET /commands/audit` with filters.

## Quickstart
```sh
# clone and enter repo
./setup.sh             # copies .env.example if missing, creates .venv, installs deps
source .venv/bin/activate
uvicorn app.main:app --app-dir gateway/app --reload
```

## Setup & Run
1. `cp .env.example .env` and adjust values (or run `./setup.sh`).
2. Create virtualenv: `python -m venv .venv && source .venv/bin/activate`.
3. Install deps: `pip install -r gateway/requirements.txt` (or `pip install -e .[dev]` for tests).
4. Run API: `uvicorn app.main:app --app-dir gateway/app --reload`.
5. Optional: set `TELEGRAM_*` and `EMAIL_*` vars to receive approval notifications.

### Gmail SMTP (example)
```
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_FROM=you@gmail.com
EMAIL_TO=you@gmail.com
EMAIL_USERNAME=you@gmail.com
EMAIL_PASSWORD=<Gmail App Password>
```
Use a Gmail App Password (required; normal passwords are blocked). Restart the API after editing `.env`.

### Environment
- `DATABASE_URL` (default `sqlite+aiosqlite:///./gateway.db`)
- `DEFAULT_RULE_ACTION` (`AUTO_REJECT` | `REQUIRE_APPROVAL`)
- `DEFAULT_APPROVAL_THRESHOLD` (default 1)
- `DEFAULT_COMMAND_COST` (default 1)
- `DEFAULT_CREDITS` (default 100)
- `RATE_LIMIT_PER_MINUTE` (default 60)
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` (optional, for approval pings)
- `EMAIL_SMTP_HOST`, `EMAIL_SMTP_PORT` (default 587), `EMAIL_FROM`, `EMAIL_TO`, `EMAIL_USERNAME`, `EMAIL_PASSWORD` (optional)

## CLI Demo (Typer)
```sh
# Create users
gateway-cli users create --username alice --role admin --credits 200
gateway-cli users create --username bob --role member --credits 100

# Rules
gateway-cli rules create   # prompts for pattern/action/priority
gateway-cli rules delete <rule_id>
gateway-cli rules list

# Submit command (member key)
gateway-cli commands submit "ls -la"

# Approvals (admin)
gateway-cli approvals pending
gateway-cli approvals approve <command_id>
gateway-cli approvals reject <command_id>

# Audit
gateway-cli audit --rule-id 1
```

## Testing Checklist
- Invalid regex rejected on rule create.
- Credits not deducted on rejected commands.
- Credits deducted once on accept.
- Concurrent submits never go negative.
- Audit shows matched rule id for accept/reject.
- Mock execution flips to EXECUTED and stores result.
- Admin-only endpoints block members.

Run tests:
```sh
pip install -e .[dev]
pytest gateway/tests
```

## Seed 15 Rules
```sh
# via env
GATEWAY_API_KEY=<ADMIN_KEY> python gateway/scripts/seed_rules.py

# or flags
python gateway/scripts/seed_rules.py --api-key <ADMIN_KEY> --base-url http://localhost:8000
```

## Notes
- SQLite lacks `SELECT FOR UPDATE`; use Postgres for stronger concurrency.
- API keys are long random (`secrets.token_urlsafe(32)`); treat like passwords.
- Execution is mocked—no shell commands run.

## Submission Checklist
- Update `.env` (or use `.env.example`) and restart API.
- Run tests: `pytest gateway/tests`.
- Record demo video (2–3 minutes) showing rule create, submission, approval, audit, and notifications.
- Submit GitHub repo + video via the provided form before 2PM IST.
