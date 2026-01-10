from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    rabbitmq_url: str = Field(default="")
    redis_url: str = Field(default="")
    backend_url: str = Field(default="")
    storage_dir: str = Field(default="")
    allowed_extensions: str = Field(default="")
    allowed_video_extensions: str = Field(default="mp4,webm,mov,mkv")
    max_upload_mb: int = Field(default=25, ge=1)
    max_upload_files: int = Field(default=10, ge=1)
    max_video_mb: int = Field(default=50, ge=1)
    max_video_seconds: int = Field(default=60, ge=1)
    video_detect_scale: float = Field(default=0.5, ge=0.1, le=1.0)
    video_detect_every_n: int = Field(default=4, ge=1)
    video_max_fps: int = Field(default=20, ge=1)
    video_preserve_audio: bool = Field(default=True)
    video_transcode_h264: bool = Field(default=True)
    blur_rate_limit: str = Field(default="10/minute")
    storage_ttl_minutes: int = Field(default=60, ge=1)
    storage_cleanup_interval_minutes: int = Field(default=30, ge=0)
    log_level: str = Field(default="INFO")
    stats_db_path: str = Field(default="stats.db")
    visitor_cookie_name: str = Field(default="visitor_id")
    visitor_cookie_max_age_days: int = Field(default=365, ge=1)
    cors_allow_origins: str = Field(default="http://localhost:5173")

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

    def allowed_video_extensions_set(self):
        return {
            ext.strip().lstrip(".").lower()
            for ext in self.allowed_video_extensions.split(",")
            if ext.strip()
        }

    def max_upload_bytes(self):
        return int(self.max_upload_mb) * 1024 * 1024

    def max_video_bytes(self):
        return int(self.max_video_mb) * 1024 * 1024

    def cors_allow_origins_list(self):
        origins = [
            origin.strip()
            for origin in self.cors_allow_origins.split(",")
            if origin.strip()
        ]
        return origins or ["http://localhost:5173"]


settings = Settings()
