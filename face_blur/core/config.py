from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    rabbitmq_url: str = Field(default="")
    redis_url: str = Field(default="")
    backend_url: str = Field(default="")
    storage_dir: str = Field(default="")
    allowed_extensions: str = Field(default="")
    max_upload_mb: int = Field(default=25, ge=1)
    blur_rate_limit: str = Field(default="10/minute")
    storage_ttl_minutes: int = Field(default=60, ge=1)
    storage_cleanup_interval_minutes: int = Field(default=30, ge=0)
    log_level: str = Field(default="INFO")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @field_validator(
        "rabbitmq_url",
        "redis_url",
        "backend_url",
        "storage_dir",
        "allowed_extensions",
    )
    @classmethod
    def _required_values(cls, value, info):
        if not str(value).strip():
            raise ValueError(f"{info.field_name} must be set")
        return value

    def allowed_extensions_set(self):
        return {
            ext.strip().lstrip(".").lower()
            for ext in self.allowed_extensions.split(",")
            if ext.strip()
        }

    def max_upload_bytes(self):
        return int(self.max_upload_mb) * 1024 * 1024


settings = Settings()
