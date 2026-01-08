import base64
import io
import zipfile
from pathlib import Path

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from taskiq_redis.exceptions import ResultIsMissingError

from face_blur.api.errors import (
    ConfigurationError,
    PayloadTooLargeError,
    ResultMissingError,
    ResultPayloadMissingError,
    TaskFailedError,
    UnsupportedMediaTypeError,
    ValidationError,
)
from face_blur.api.limiter import limiter
from face_blur.api.responses import ok
from face_blur.api.schemas import ErrorResponse, QueuedResponse, SuccessResponse
from face_blur.core.config import settings
from face_blur.storage.filesystem import cleanup_paths, read_bytes

router = APIRouter()


def _validate_extension(filename: str):
    """Validate file extension against allowlist."""
    extension = Path(filename).suffix.lower().lstrip(".")
    if not extension:
        raise ValidationError("File extension is required.")
    allowed = settings.allowed_extensions_set()
    if extension not in allowed:
        allowed_list = ", ".join(sorted(allowed))
        raise UnsupportedMediaTypeError(
            f"Unsupported file type '.{extension}'. Allowed: {allowed_list}."
        )


def _encode_uploads(files):
    """Read uploads and encode them as base64 payloads for Taskiq."""
    payload = []
    for file in files:
        raw = file["bytes"]
        if not raw:
            raise ValidationError("Empty file upload detected.")
        payload.append(
            {
                "filename": file["filename"],
                "content_type": file["content_type"],
                "data": base64.b64encode(raw).decode("ascii"),
            }
        )
    return payload


def _load_results(items):
    """Load result file bytes from disk for response."""
    results = []
    for item in items:
        path = Path(item["path"])
        if not path.exists():
            raise ResultMissingError("Processed files are missing.")
        results.append(
            {
                "filename": item["filename"],
                "content_type": item.get("content_type") or "image/jpeg",
                "bytes": read_bytes(path),
                "path": str(path),
            }
        )
    return results


def _zip_results(items):
    """Bundle multiple outputs into an in-memory ZIP archive."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(
        buffer, mode="w", compression=zipfile.ZIP_DEFLATED
    ) as zip_file:
        for item in items:
            zip_file.writestr(item["filename"], item["bytes"])
    buffer.seek(0)
    return buffer.getvalue()


async def _get_task_result(task_id: str, broker):
    """Fetch a task result from the Taskiq result backend."""
    if broker.result_backend is None:
        raise ConfigurationError("Result backend is not configured.")
    try:
        return await broker.result_backend.get_result(task_id)
    except ResultIsMissingError:
        return None


@router.get("/health", response_model=SuccessResponse)
async def health():
    return ok(message="Service is healthy.")


@router.post(
    "/blur",
    response_model=QueuedResponse,
    responses={
        400: {"model": ErrorResponse},
        413: {"model": ErrorResponse},
        415: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
    },
)
@limiter.limit(settings.blur_rate_limit)
async def submit_blur(request: Request, files: list[UploadFile] = File(...)):
    if not files:
        raise ValidationError("No files uploaded.")

    uploads = []
    for file in files:
        filename = file.filename or "upload"
        _validate_extension(filename)
        data = await file.read()
        if len(data) > settings.max_upload_bytes():
            raise PayloadTooLargeError(
                "Uploaded file exceeds size limit.",
                details={"max_mb": settings.max_upload_mb, "filename": filename},
            )
        uploads.append(
            {
                "filename": filename,
                "content_type": file.content_type or "application/octet-stream",
                "bytes": data,
            }
        )

    task = await request.app.state.task_submitter(_encode_uploads(uploads))
    return ok(
        message=f"Queued {len(uploads)} image(s) for processing.",
        status="queued",
        data={"task_id": task.task_id},
    )


@router.get(
    "/results/{task_id}",
    responses={
        202: {"model": SuccessResponse},
        410: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
async def fetch_result(request: Request, task_id: str):
    result = await _get_task_result(task_id, request.app.state.broker)
    if result is None:
        return JSONResponse(
            status_code=202,
            content=ok(
                message="Image blur is still running.",
                status="pending",
            ),
        )

    if getattr(result, "is_err", False):
        raise TaskFailedError("Task failed while blurring faces.")

    return_value = getattr(result, "return_value", None)
    if return_value is None and isinstance(result, dict):
        return_value = result.get("return_value") or result.get("result")
    if not return_value:
        raise ResultPayloadMissingError("Task result payload is missing.")

    items = _load_results(return_value)
    cleanup_paths([item["path"] for item in items])

    if len(items) == 1:
        item = items[0]
        return Response(content=item["bytes"], media_type=item["content_type"])

    archive = _zip_results(items)
    return Response(
        content=archive,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="blurred_images.zip"'},
    )
