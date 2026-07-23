from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite+aiosqlite:///./data/pipeline.db"

    groq_api_key: str | None = None
    llm_model: str = "llama-3.3-70b-versatile"

    max_repair_attempts: int = 3
    max_upload_rows: int = 10000
    max_concurrent_diagnoses: int = 8

    alert_slack_webhook_url: str | None = None
    alert_email_smtp_host: str | None = None
    alert_email_smtp_port: int | None = None
    alert_email_from: str | None = None
    alert_email_to: str | None = None

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    cors_allowed_origins: str = "http://localhost:5173"

    @property
    def cors_allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]

    @field_validator(
        "groq_api_key",
        "alert_slack_webhook_url",
        "alert_email_smtp_host",
        "alert_email_smtp_port",
        "alert_email_from",
        "alert_email_to",
        mode="before",
    )
    @classmethod
    def blank_to_none(cls, v):
        return None if v == "" else v


settings = Settings()
