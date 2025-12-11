from fastapi import FastAPI

from app.api.commands import router as commands_router
from app.api.health import router as health_router
from app.api.rules import router as rules_router
from app.api.users import router as users_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.db import init_db

settings = get_settings()

configure_logging()

app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION)

app.include_router(health_router)
app.include_router(users_router)
app.include_router(rules_router)
app.include_router(commands_router)


@app.on_event("startup")
async def on_startup() -> None:
    await init_db()
    if settings.DEBUG:
        app.state._startup_notice = "debug-mode enabled"


@app.get("/", include_in_schema=False)
async def readiness_probe() -> dict[str, str]:
    return {"status": "ready"}
