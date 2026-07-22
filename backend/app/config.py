from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./data/pipeline.db"

    groq_api_key: str | None = None
    llm_model: str = "llama-3.3-70b-versatile"

    max_repair_attempts: int = 3
    max_upload_rows: int = 10000

    alert_slack_webhook_url: str | None = None
    alert_email_smtp_host: str | None = None
    alert_email_smtp_port: int | None = None
    alert_email_from: str | None = None
    alert_email_to: str | None = None

    api_host: str = "0.0.0.0"
    api_port: int = 8000

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
