import base64
import uuid
from pathlib import Path

from face_blur.core.config import settings
from face_blur.services.blur_service import process_image_blur
from face_blur.storage.filesystem import ensure_dir, write_bytes
from face_blur.workers.broker import broker


def _safe_output_name(filename: str, index: int):
    """Build a stable output filename for a blurred image."""
    if filename:
        stem = Path(filename).stem
        return f"{stem}_blurred.jpg"
    return f"blurred_{index}.jpg"


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
