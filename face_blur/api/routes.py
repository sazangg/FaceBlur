import base64
import io
import tempfile
import uuid
import zipfile
from pathlib import Path

import cv2
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
from face_blur.api.metrics import (
    BLUR_RESULTS_SERVED,
    BLUR_TASKS_SUBMITTED,
    VIDEO_DURATION_SECONDS,
    VIDEO_RESULTS_SERVED,
    VIDEO_TASKS_SUBMITTED,
)
from face_blur.api.responses import ok
from face_blur.api.schemas import ErrorResponse, QueuedResponse, SuccessResponse
from face_blur.core.config import settings
from face_blur.stats.store import (
    get_stats_async,
    increment_stat_async,
    increment_stats_async,
    record_visitor_async,
)
from face_blur.storage.filesystem import cleanup_paths, read_bytes

router = APIRouter()


def _validate_extension(filename: str):
    """Validate file extension against allowlist."""
    extension = Path(filename).suffix.lower().lstrip(".")
    if not extension:
        raise ValidationError(
            "File extension is required.",
            details={"suggestion": "Add a file extension like .jpg or .png."},
        )
    allowed = settings.allowed_extensions_set()
    if extension not in allowed:
        allowed_list = ", ".join(sorted(allowed))
        raise UnsupportedMediaTypeError(
            f"Unsupported file type '.{extension}'. Allowed: {allowed_list}.",
            details={"suggestion": f"Supported images: {allowed_list}."},
        )


def _validate_video_extension(filename: str):
    """Validate video file extension against allowlist."""
    extension = Path(filename).suffix.lower().lstrip(".")
    if not extension:
        raise ValidationError(
            "File extension is required.",
            details={"suggestion": "Add a file extension like .mp4 or .mov."},
        )
    allowed = settings.allowed_video_extensions_set()
    if extension not in allowed:
        allowed_list = ", ".join(sorted(allowed))
        raise UnsupportedMediaTypeError(
            f"Unsupported video type '.{extension}'. Allowed: {allowed_list}.",
            details={"suggestion": f"Supported videos: {allowed_list}."},
        )


def _sniff_media(data: bytes):
    """Detect media type based on file signature."""
    if len(data) < 12:
        return None
    header = data[:16]
    if header.startswith(b"\xff\xd8\xff"):
        return ("image", "jpg")
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return ("image", "png")
    if header.startswith((b"GIF87a", b"GIF89a")):
        return ("image", "gif")
    if header.startswith(b"BM"):
        return ("image", "bmp")
    if header.startswith((b"II*\x00", b"MM\x00*")):
        return ("image", "tiff")
    if header.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return ("image", "webp")
    if data[4:8] == b"ftyp":
        brand = data[8:12]
        if brand == b"qt  ":
            return ("video", "mov")
        return ("video", "mp4")
    if header.startswith(b"\x1A\x45\xDF\xA3"):
        doc = data[:128].lower()
        if b"webm" in doc:
            return ("video", "webm")
        return ("video", "mkv")
    if header.startswith(b"RIFF") and data[8:12] == b"AVI ":
        return ("video", "avi")
    return None


def _video_extensions_match(extension: str, detected: str):
    if extension == detected:
        return True
    matroska = {"mkv", "webm"}
    return extension in matroska and detected in matroska


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


def _load_video_result(item):
    """Load a blurred video file from disk for response."""
    path = Path(item["path"])
    if not path.exists():
        raise ResultMissingError("Processed video is missing.")
    return {
        "filename": item["filename"],
        "content_type": item.get("content_type") or "video/mp4",
        "bytes": read_bytes(path),
        "path": str(path),
        "duration_seconds": item.get("duration_seconds"),
    }


def _video_duration_seconds(path: Path):
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise ValidationError("Unable to read video file.")
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    cap.release()
    if fps <= 0 or frame_count <= 0:
        return 0
    return frame_count / fps


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


async def _get_queue_status(broker):
    """Fetch current queue size from the broker channel."""
    channel = getattr(broker, "write_channel", None)
    if channel is None:
        return {
            "queued": 0,
            "consumers": 0,
            "available": False,
            "error": "Broker channel is not ready.",
        }
    queue_name = getattr(broker, "_queue_name", "taskiq")
    try:
        queue = await channel.declare_queue(queue_name, passive=True)
    except Exception as exc:
        return {
            "queued": 0,
            "consumers": 0,
            "available": False,
            "error": str(exc),
        }
    result = queue.declaration_result
    return {
        "queued": result.message_count,
        "consumers": result.consumer_count,
        "available": True,
    }


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
    if len(files) > settings.max_upload_files:
        raise ValidationError(
            "Too many files uploaded.",
            details={
                "max_files": settings.max_upload_files,
                "suggestion": f"Upload up to {settings.max_upload_files} images.",
            },
        )

    uploads = []
    for file in files:
        filename = file.filename or "upload"
        _validate_extension(filename)
        data = await file.read()
        sniffed = _sniff_media(data)
        if sniffed is None:
            raise UnsupportedMediaTypeError(
                "Could not determine file type.",
                details={
                    "suggestion": "Upload a supported image file like jpg or png.",
                },
            )
        kind, detected_ext = sniffed
        if kind != "image":
            raise UnsupportedMediaTypeError(
                "Uploaded file is not an image.",
                details={
                    "suggestion": "Upload images to /blur or use /blur/video for videos.",
                },
            )
        allowed = settings.allowed_extensions_set()
        if detected_ext not in allowed:
            allowed_list = ", ".join(sorted(allowed))
            raise UnsupportedMediaTypeError(
                f"Unsupported image type '.{detected_ext}'. Allowed: {allowed_list}.",
                details={"suggestion": f"Supported images: {allowed_list}."},
            )
        extension = Path(filename).suffix.lower().lstrip(".")
        if extension and extension != detected_ext:
            raise ValidationError(
                "File extension does not match detected type.",
                details={
                    "detected": detected_ext,
                    "suggestion": f"Rename the file to .{detected_ext} or upload a matching file.",
                },
            )
        if len(data) > settings.max_upload_bytes():
            raise PayloadTooLargeError(
                "Uploaded file exceeds size limit.",
                details={
                    "max_mb": settings.max_upload_mb,
                    "filename": filename,
                    "suggestion": "Try a smaller image or reduce its resolution.",
                },
            )
        uploads.append(
            {
                "filename": filename,
                "content_type": file.content_type or "application/octet-stream",
                "bytes": data,
            }
        )

    task = await request.app.state.task_submitter(_encode_uploads(uploads))
    BLUR_TASKS_SUBMITTED.inc()
    await increment_stat_async(settings.stats_db_path, "total_tasks")
    return ok(
        message=f"Queued {len(uploads)} image(s) for processing.",
        status="queued",
        data={"task_id": task.task_id},
    )


@router.post(
    "/blur/video",
    response_model=QueuedResponse,
    responses={
        400: {"model": ErrorResponse},
        413: {"model": ErrorResponse},
        415: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
    },
)
@limiter.limit(settings.blur_rate_limit)
async def submit_blur_video(request: Request, file: UploadFile = File(...)):
    if not file:
        raise ValidationError("No video uploaded.")

    filename = file.filename or "upload"
    _validate_video_extension(filename)
    data = await file.read()
    sniffed = _sniff_media(data)
    if sniffed is None:
        raise UnsupportedMediaTypeError(
            "Could not determine file type.",
            details={
                "suggestion": "Upload a supported video file like mp4 or mov.",
            },
        )
    kind, detected_ext = sniffed
    if kind != "video":
        raise UnsupportedMediaTypeError(
            "Uploaded file is not a video.",
            details={
                "suggestion": "Upload videos to /blur/video or use /blur for images.",
            },
        )
    allowed = settings.allowed_video_extensions_set()
    if detected_ext not in allowed:
        allowed_list = ", ".join(sorted(allowed))
        raise UnsupportedMediaTypeError(
            f"Unsupported video type '.{detected_ext}'. Allowed: {allowed_list}.",
            details={"suggestion": f"Supported videos: {allowed_list}."},
        )
    extension = Path(filename).suffix.lower().lstrip(".")
    if extension and not _video_extensions_match(extension, detected_ext):
        raise ValidationError(
            "File extension does not match detected type.",
            details={
                "detected": detected_ext,
                "suggestion": f"Rename the file to .{detected_ext} or upload a matching file.",
            },
        )
    if len(data) > settings.max_video_bytes():
        raise PayloadTooLargeError(
            "Uploaded video exceeds size limit.",
            details={
                "max_mb": settings.max_video_mb,
                "filename": filename,
                "suggestion": "Try a smaller video or reduce its resolution/length.",
            },
        )

    suffix = Path(filename).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(data)
        temp_path = Path(temp_file.name)

    try:
        duration = _video_duration_seconds(temp_path)
    finally:
        temp_path.unlink(missing_ok=True)

    if duration and duration > settings.max_video_seconds:
        raise ValidationError(
            "Uploaded video exceeds duration limit.",
            details={
                "max_seconds": settings.max_video_seconds,
                "duration_seconds": round(duration, 2),
                "suggestion": "Trim the video or lower the duration before uploading.",
            },
        )

    uploads = [
        {
            "filename": filename,
            "content_type": file.content_type or "video/mp4",
            "bytes": data,
        }
    ]
    task = await request.app.state.video_task_submitter(_encode_uploads(uploads))
    VIDEO_TASKS_SUBMITTED.inc()
    await increment_stat_async(settings.stats_db_path, "total_tasks")
    return ok(
        message="Queued video for processing.",
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
        error = getattr(result, "error", None)
        details = None
        if error is not None:
            details = {
                "type": error.__class__.__name__,
                "message": str(error),
            }
        raise TaskFailedError("Task failed while blurring faces.", details=details)

    return_value = getattr(result, "return_value", None)
    if return_value is None and isinstance(result, dict):
        return_value = result.get("return_value") or result.get("result")
    if not return_value:
        raise ResultPayloadMissingError("Task result payload is missing.")

    if isinstance(return_value, list) and return_value:
        if return_value[0].get("type") == "video":
            item = _load_video_result(return_value[0])
            VIDEO_RESULTS_SERVED.inc()
            duration_seconds = item.get("duration_seconds")
            if duration_seconds:
                VIDEO_DURATION_SECONDS.inc(duration_seconds)
            await increment_stats_async(
                settings.stats_db_path,
                {
                    "total_videos": 1,
                    "total_video_seconds": int(round(duration_seconds or 0)),
                },
            )
            cleanup_paths([item["path"]])
            return Response(content=item["bytes"], media_type=item["content_type"])

        items = _load_results(return_value)
        await increment_stat_async(settings.stats_db_path, "total_images", len(items))
        cleanup_paths([item["path"] for item in items])

        if len(items) == 1:
            item = items[0]
            BLUR_RESULTS_SERVED.labels(type="single").inc()
            return Response(content=item["bytes"], media_type=item["content_type"])

        archive = _zip_results(items)
        BLUR_RESULTS_SERVED.labels(type="zip").inc()
        return Response(
            content=archive,
            media_type="application/zip",
            headers={"Content-Disposition": 'attachment; filename="blurred_images.zip"'},
        )

    if isinstance(return_value, dict) and return_value.get("type") == "video":
        item = _load_video_result(return_value)
        VIDEO_RESULTS_SERVED.inc()
        duration_seconds = item.get("duration_seconds")
        if duration_seconds:
            VIDEO_DURATION_SECONDS.inc(duration_seconds)
        await increment_stats_async(
            settings.stats_db_path,
            {
                "total_videos": 1,
                "total_video_seconds": int(round(duration_seconds or 0)),
            },
        )
        cleanup_paths([item["path"]])
        return Response(content=item["bytes"], media_type=item["content_type"])

    raise ResultPayloadMissingError("Task result payload is missing.")


@router.get("/stats", response_model=SuccessResponse)
async def stats(request: Request):
    visitor_cookie = settings.visitor_cookie_name
    visitor_id = request.cookies.get(visitor_cookie)
    if not visitor_id:
        visitor_id = str(uuid.uuid4())
        await record_visitor_async(settings.stats_db_path, visitor_id)
    data = await get_stats_async(settings.stats_db_path)
    response = JSONResponse(content=ok(message="Stats loaded.", data=data))
    if visitor_id and not request.cookies.get(visitor_cookie):
        response.set_cookie(
            visitor_cookie,
            visitor_id,
            max_age=settings.visitor_cookie_max_age_days * 24 * 60 * 60,
            httponly=True,
            samesite="lax",
            path="/",
        )
    return response


@router.get("/queue", response_model=SuccessResponse)
async def queue_status(request: Request):
    status = await _get_queue_status(request.app.state.broker)
    return ok(message="Queue status loaded.", data=status)
