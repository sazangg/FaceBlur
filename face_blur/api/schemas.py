from typing import Any

from pydantic import BaseModel


class SuccessResponse(BaseModel):
    status: str
    message: str
    data: dict[str, Any] | None = None


class QueuedData(BaseModel):
    task_id: str


class QueuedResponse(BaseModel):
    status: str
    message: str
    data: QueuedData


class ErrorResponse(BaseModel):
    status: str
    code: str
    message: str
    details: dict[str, Any] | None = None
