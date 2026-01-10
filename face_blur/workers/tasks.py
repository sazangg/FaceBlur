import base64
import logging
import uuid
from pathlib import Path

from face_blur.core.config import settings
from face_blur.services.blur_service import process_image_blur
from face_blur.services.video_service import process_video_blur
from face_blur.storage.filesystem import ensure_dir, write_bytes
from face_blur.workers.broker import broker

logger = logging.getLogger(__name__)


def _safe_output_name(filename: str, index: int):
    """Build a stable output filename for a blurred image."""
    if filename:
        stem = Path(filename).stem
        return f"{stem}_blurred.jpg"
    return f"blurred_{index}.jpg"


def _safe_video_output_name(filename: str):
    """Build a stable output filename for a blurred video."""
    if filename:
        stem = Path(filename).stem
        return f"{stem}_blurred.mp4"
    return "blurred_video.mp4"


def _decode_payload_item(item):
    """Decode a base64 payload item into raw bytes and metadata."""
    raw_bytes = base64.b64decode(item["data"])
    filename = item.get("filename") or ""
    return raw_bytes, filename


def _build_task_dir():
    """Create a unique directory for task outputs."""
    task_dir = Path(settings.storage_dir) / uuid.uuid4().hex
    ensure_dir(task_dir)
    return task_dir


@broker.task
def blur_images(items):
    task_dir = _build_task_dir()
    results = []
    for index, item in enumerate(items):
        raw_bytes, filename = _decode_payload_item(item)
        blurred = process_image_blur(raw_bytes)
        output_name = _safe_output_name(filename, index)
        output_path = task_dir / output_name
        write_bytes(output_path, blurred)
        results.append(
            {
                "filename": output_name,
                "content_type": "image/jpeg",
                "path": str(output_path),
            }
        )
    return results


@broker.task
def blur_videos(items):
    task_dir = _build_task_dir()
    results = []
    for item in items:
        raw_bytes, filename = _decode_payload_item(item)
        input_name = Path(filename or "upload").name
        input_path = task_dir / input_name
        write_bytes(input_path, raw_bytes)
        logger.info(
            "Video task input saved path=%s size_bytes=%s",
            input_path,
            len(raw_bytes),
        )

        output_name = _safe_video_output_name(filename)
        output_path = task_dir / output_name
        logger.info(
            "Video task processing input=%s output=%s detect_scale=%.2f",
            input_path,
            output_path,
            settings.video_detect_scale,
        )
        meta = process_video_blur(
            input_path,
            output_path,
            detect_scale=settings.video_detect_scale,
            detect_every_n=settings.video_detect_every_n,
            max_fps=settings.video_max_fps,
            preserve_audio=settings.video_preserve_audio,
            transcode_h264=settings.video_transcode_h264,
        )
        try:
            input_path.unlink()
        except FileNotFoundError:
            pass
        logger.info(
            "Video task completed output=%s frames=%s duration=%.2fs",
            output_path,
            meta.get("frames"),
            meta.get("duration_seconds", 0),
        )
        results.append(
            {
                "type": "video",
                "filename": output_name,
                "content_type": "video/mp4",
                "path": str(output_path),
                "duration_seconds": meta["duration_seconds"],
            }
        )
    return results
