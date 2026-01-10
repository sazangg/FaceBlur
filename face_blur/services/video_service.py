import logging
import shutil
import subprocess
import time
from pathlib import Path

import cv2

from face_blur.services.blur_service import apply_blur, detect_faces
from face_blur.storage.filesystem import ensure_dir

logger = logging.getLogger(__name__)


def _ffmpeg_path():
    return shutil.which("ffmpeg")


def _open_video_writer(output_path: Path, fps: float, size: tuple[int, int]):
    """Try multiple codecs to initialize a VideoWriter."""
    codec_candidates = ["mp4v", "avc1", "H264"]
    for codec in codec_candidates:
        fourcc = cv2.VideoWriter_fourcc(*codec)  # type: ignore
        writer = cv2.VideoWriter(str(output_path), fourcc, fps, size)
        if writer.isOpened():
            logger.info("Video writer initialized with codec=%s", codec)
            return writer
        writer.release()
    raise ValueError(
        "Could not initialize video writer. Tried: " + ", ".join(codec_candidates)
    )


def _mux_audio(
    video_path: Path,
    audio_source: Path,
    output_path: Path,
    transcode_video: bool,
):
    """Mux audio from audio_source into video_path output."""
    ffmpeg = _ffmpeg_path()
    if not ffmpeg:
        logger.warning("ffmpeg not found; returning video without audio.")
        return False

    video_codec = ["-c:v", "copy"]
    if transcode_video:
        video_codec = [
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            "-pix_fmt",
            "yuv420p",
        ]

    command = [
        ffmpeg,
        "-y",
        "-i",
        str(video_path),
        "-i",
        str(audio_source),
        "-map",
        "0:v:0",
        "-map",
        "1:a:0?",
        *video_codec,
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-shortest",
        str(output_path),
    ]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        logger.warning(
            "ffmpeg mux failed: %s",
            (result.stderr or "").strip(),
        )
        return False
    return True


def _transcode_video(video_path: Path, output_path: Path):
    """Transcode a video to H.264 for browser-friendly playback."""
    ffmpeg = _ffmpeg_path()
    if not ffmpeg:
        logger.warning("ffmpeg not found; returning original video.")
        return False

    command = [
        ffmpeg,
        "-y",
        "-i",
        str(video_path),
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-pix_fmt",
        "yuv420p",
        "-an",
        str(output_path),
    ]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        logger.warning(
            "ffmpeg transcode failed: %s",
            (result.stderr or "").strip(),
        )
        return False
    return True


def process_video_blur(
    input_path: Path,
    output_path: Path,
    detect_scale: float = 1.0,
    detect_every_n: int = 1,
    max_fps: int = 0,
    preserve_audio: bool = False,
    transcode_h264: bool = True,
):
    """Blur faces in a video file and write the result to output_path."""
    cap = cv2.VideoCapture(str(input_path))
    if not cap.isOpened():
        raise ValueError("Could not open video file.")

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 24.0

    ret, frame = cap.read()
    if not ret or frame is None:
        cap.release()
        raise ValueError("Video contains no readable frames.")

    height, width = frame.shape[:2]
    ensure_dir(output_path.parent)
    stride = 1
    if max_fps and fps > max_fps:
        stride = max(1, round(fps / max_fps))
    output_fps = fps / stride
    temp_output = output_path.with_suffix(".video.mp4")
    writer = _open_video_writer(temp_output, output_fps, (width, height))
    detect_every_n = max(1, detect_every_n)

    logger.info(
        (
            "Video blur started path=%s fps=%.2f output_fps=%.2f stride=%s "
            "detect_every_n=%s size=%sx%s detect_scale=%.2f"
        ),
        input_path,
        fps,
        output_fps,
        stride,
        detect_every_n,
        width,
        height,
        detect_scale,
    )

    frames = 0
    start_time = time.perf_counter()
    next_log = start_time + 5.0
    try:
        frame_index = 0
        last_faces = detect_faces(frame, scale=detect_scale)
        apply_blur(frame, last_faces)
        writer.write(frame)
        frames += 1

        while True:
            if stride > 1:
                grab_ok = True
                for _ in range(stride - 1):
                    if not cap.grab():
                        grab_ok = False
                        break
                if not grab_ok:
                    break
            ret, frame = cap.read()
            if not ret:
                break
            frame_index += 1
            if frame_index % detect_every_n == 0:
                last_faces = detect_faces(frame, scale=detect_scale)
            apply_blur(frame, last_faces)
            writer.write(frame)
            frames += 1
            now = time.perf_counter()
            if now >= next_log:
                logger.info(
                    "Video blur progress path=%s frames=%s elapsed=%.2fs",
                    input_path,
                    frames,
                    now - start_time,
                )
                next_log = now + 5.0
    except Exception:
        logger.exception("Video processing failed for %s", input_path)
        raise
    finally:
        cap.release()
        writer.release()

    if preserve_audio:
        if _mux_audio(
            temp_output,
            input_path,
            output_path,
            transcode_video=transcode_h264,
        ):
            temp_output.unlink(missing_ok=True)
        else:
            temp_output.replace(output_path)
    else:
        if transcode_h264:
            if _transcode_video(temp_output, output_path):
                temp_output.unlink(missing_ok=True)
            else:
                temp_output.replace(output_path)
        else:
            temp_output.replace(output_path)

    duration_seconds = frames / output_fps if output_fps else 0
    total_time = time.perf_counter() - start_time
    logger.info(
        "Video blur finished path=%s frames=%s duration=%.2fs elapsed=%.2fs",
        input_path,
        frames,
        duration_seconds,
        total_time,
    )
    return {
        "frames": frames,
        "fps": output_fps,
        "duration_seconds": duration_seconds,
    }
