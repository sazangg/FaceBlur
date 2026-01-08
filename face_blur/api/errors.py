from dataclasses import dataclass
from typing import Any

from fastapi.responses import JSONResponse


@dataclass
class AppError(Exception):
    """Base error type for consistent API error responses."""

    message: str
    status_code: int = 400
    code: str = "error"
    details: dict[str, Any] | None = None

    def to_response(self):
        payload: dict[str, Any] = {
            "status": "error",
            "code": self.code,
            "message": self.message,
        }
        if self.details:
            payload["details"] = self.details
        return JSONResponse(status_code=self.status_code, content=payload)


class ValidationError(AppError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            message=message, status_code=400, code="validation_error", details=details
        )


class PayloadTooLargeError(AppError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            message=message, status_code=413, code="payload_too_large", details=details
        )


class UnsupportedMediaTypeError(AppError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            status_code=415,
            code="unsupported_media_type",
            details=details,
        )


class ResultMissingError(AppError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            message=message, status_code=410, code="result_missing", details=details
        )


class ConfigurationError(AppError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            message=message, status_code=500, code="config_error", details=details
        )


class TaskFailedError(AppError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            message=message, status_code=500, code="task_failed", details=details
        )


class ResultPayloadMissingError(AppError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            status_code=500,
            code="result_payload_missing",
            details=details,
        )
