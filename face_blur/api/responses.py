from typing import Any


def ok(message: str, data: dict[str, Any] | None = None, status: str = "ok"):
    """Build a uniform success response payload."""
    payload: dict[str, Any] = {"status": status, "message": message}
    if data is not None:
        payload["data"] = data
    return payload
