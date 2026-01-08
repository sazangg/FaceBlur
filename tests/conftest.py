import os


def _set_env_defaults():
    os.environ.setdefault("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
    os.environ.setdefault("BACKEND_URL", "http://localhost:8000")
    os.environ.setdefault("STORAGE_DIR", "storage")
    os.environ.setdefault("ALLOWED_EXTENSIONS", "jpg,jpeg,png")
    os.environ.setdefault("MAX_UPLOAD_MB", "25")
    os.environ.setdefault("BLUR_RATE_LIMIT", "100/minute")
    os.environ.setdefault("STORAGE_TTL_MINUTES", "60")
    os.environ.setdefault("STORAGE_CLEANUP_INTERVAL_MINUTES", "0")


_set_env_defaults()
