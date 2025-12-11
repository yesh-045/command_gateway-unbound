from collections.abc import AsyncIterator
import logging
from pathlib import Path
import secrets

from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, select
from sqlalchemy import func

from app.core.config import get_settings
from app.core.rules import validate_regex
from app.db.models import Rule, User

settings = get_settings()
logger = logging.getLogger(__name__)


def _normalize_db_url(url: str) -> str:
	"""Ensure SQLite URLs are absolute so cwd does not affect DB location."""
	parsed = make_url(url)
	if parsed.drivername.startswith("sqlite") and parsed.database:
		db_path = Path(parsed.database)
		if not db_path.is_absolute():
			project_root = Path(__file__).resolve().parents[3]
			db_path = (project_root / db_path).resolve()
			parsed = parsed.set(database=str(db_path))
	return str(parsed)


engine: AsyncEngine = create_async_engine(
	_normalize_db_url(settings.DATABASE_URL),
	echo=settings.DEBUG,
	future=True,
)

async_session_factory = sessionmaker(
	engine, expire_on_commit=False, class_=AsyncSession
)


async def _seed_admin(session: AsyncSession) -> None:
	count = await session.scalar(select(func.count(User.id)))
	if count:
		return
	api_key = secrets.token_urlsafe(32)
	admin = User(
		username=settings.SEED_ADMIN_USERNAME,
		role="admin",
		credits=settings.SEED_ADMIN_CREDITS,
		api_key=api_key,
	)
	session.add(admin)
	await session.commit()
	logger.warning("Seeded default admin user '%s' with api_key=%s", admin.username, api_key)


async def _seed_rules(session: AsyncSession) -> None:
	count = await session.scalar(select(func.count(Rule.id)))
	if count:
		return
	starter_rules = [
		(":(){ :|:& };:", "AUTO_REJECT", 10),
		("rm\\s+-rf\\s+/", "AUTO_REJECT", 20),
		("mkfs\\.", "AUTO_REJECT", 30),
		("git\\s+(status|log|diff)", "AUTO_ACCEPT", 90),
		("^(ls|cat|pwd|echo)", "AUTO_ACCEPT", 100),
	]
	for pattern, action, priority in starter_rules:
		validate_regex(pattern)
		session.add(
			Rule(pattern=pattern, action=action, priority=priority, created_by=1)
		)
	await session.commit()
	logger.info("Seeded starter rules (%d)", len(starter_rules))


async def _seed_defaults() -> None:
	async with async_session_factory() as session:
		if settings.SEED_ADMIN_ENABLED:
			await _seed_admin(session)
		if settings.SEED_STARTER_RULES:
			await _seed_rules(session)


async def init_db() -> None:
	async with engine.begin() as conn:
		await conn.run_sync(SQLModel.metadata.create_all)
	await _seed_defaults()


async def get_session() -> AsyncIterator[AsyncSession]:
	async with async_session_factory() as session:
		yield session
