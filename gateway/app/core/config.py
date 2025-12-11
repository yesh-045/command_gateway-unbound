from functools import lru_cache

from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = Field("Gateway", env="PROJECT_NAME")
    VERSION: str = Field("0.1.0", env="PROJECT_VERSION")
    ENVIRONMENT: str = Field("local", env="ENVIRONMENT")
    DEBUG: bool = Field(False, env="DEBUG")
    HOST: str = Field("0.0.0.0", env="HOST")
    PORT: int = Field(8000, env="PORT")

    DATABASE_URL: str = Field(
        "sqlite+aiosqlite:///./gateway.db",
        env="DATABASE_URL",
        description="SQLModel database URL",
    )
    DEFAULT_CREDITS: int = Field(100, env="DEFAULT_CREDITS")
    DEFAULT_COMMAND_COST: int = Field(1, env="DEFAULT_COMMAND_COST")
    DEFAULT_RULE_ACTION: str = Field(
        "AUTO_REJECT", env="DEFAULT_RULE_ACTION"
    )  # AUTO_REJECT | REQUIRE_APPROVAL
    DEFAULT_APPROVAL_THRESHOLD: int = Field(1, env="DEFAULT_APPROVAL_THRESHOLD")
    RATE_LIMIT_PER_MINUTE: int = Field(60, env="RATE_LIMIT_PER_MINUTE")

    # Notifications (best-effort)
    TELEGRAM_BOT_TOKEN: str | None = Field(default=None, env="TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID: str | None = Field(default=None, env="TELEGRAM_CHAT_ID")
    EMAIL_SMTP_HOST: str | None = Field(default=None, env="EMAIL_SMTP_HOST")
    EMAIL_SMTP_PORT: int = Field(default=587, env="EMAIL_SMTP_PORT")
    EMAIL_FROM: str | None = Field(default=None, env="EMAIL_FROM")
    EMAIL_TO: str | None = Field(default=None, env="EMAIL_TO")
    EMAIL_USERNAME: str | None = Field(default=None, env="EMAIL_USERNAME")
    EMAIL_PASSWORD: str | None = Field(default=None, env="EMAIL_PASSWORD")

    # Seeding controls
    SEED_ADMIN_ENABLED: bool = Field(True, env="SEED_ADMIN_ENABLED")
    SEED_ADMIN_USERNAME: str = Field("admin", env="SEED_ADMIN_USERNAME")
    SEED_ADMIN_CREDITS: int = Field(100, env="SEED_ADMIN_CREDITS")
    SEED_STARTER_RULES: bool = Field(True, env="SEED_STARTER_RULES")

    class Config:
        env_file = ".env"
        case_sensitive = False
        env_file_encoding = "utf-8"

    @validator("DEFAULT_RULE_ACTION")
    def validate_default_rule_action(cls, value: str) -> str:  # noqa: N805
        allowed = {"AUTO_REJECT", "REQUIRE_APPROVAL"}
        if value not in allowed:
            raise ValueError(f"DEFAULT_RULE_ACTION must be one of {allowed}")
        return value


@lru_cache()
def get_settings() -> Settings:
    return Settings()
