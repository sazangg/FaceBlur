import httpx
import streamlit as st

from face_blur.core.config import settings

BACKEND_URL = settings.backend_url
ALLOWED_VIDEO_EXTENSIONS = sorted(settings.allowed_video_extensions_set())
MAX_VIDEO_MB = settings.max_video_mb
MAX_VIDEO_SECONDS = settings.max_video_seconds


def _check_health():
    """Call the backend health endpoint to confirm availability."""
    try:
        response = httpx.get(f"{BACKEND_URL}/health", timeout=5)
        response.raise_for_status()
        payload = response.json()
        return payload.get("status") == "ok", None
    except Exception as exc:
        return False, str(exc)


st.set_page_config(
    page_title="Video Face Blur Tester", page_icon="FB", layout="centered"
)
st.title("Video Face Blur Tester")
st.caption("CPU-only demo. Audio is not preserved in this version.")

healthy, error_message = _check_health()
if not healthy:
    st.error("Backend is unavailable. Start the API before uploading videos.")
    if error_message:
        st.caption(error_message)
    st.stop()

st.success("Backend is healthy. Upload a short video to begin.")
st.caption(
    f"Limits: {MAX_VIDEO_MB} MB max, {MAX_VIDEO_SECONDS}s max. "
    f"Accepted: {', '.join(ALLOWED_VIDEO_EXTENSIONS)}."
)

upload = st.file_uploader(
    "Choose a video",
    type=ALLOWED_VIDEO_EXTENSIONS,
    accept_multiple_files=False,
)

video_bytes = None
upload_name: str | None = None
upload_type = "video/mp4"
if upload:
    video_bytes = upload.getvalue()
    size_mb = len(video_bytes) / (1024 * 1024)
    upload_name = upload.name
    upload_type = upload.type or "video/mp4"
    st.caption(f"Selected: {upload_name} ({size_mb:.1f} MB)")

    if size_mb > MAX_VIDEO_MB:
        st.error(
            f"Selected video is {size_mb:.1f} MB. Max allowed is {MAX_VIDEO_MB} MB."
        )
        video_bytes = None

if video_bytes and st.button("Submit for blurring"):
    if upload_name is None:
        st.error("No video selected.")
        st.stop()
    files_payload = {
        "file": (
            upload_name,
            video_bytes,
            upload_type,
        )
    }
    response = httpx.post(f"{BACKEND_URL}/blur/video", files=files_payload, timeout=60)
    if response.status_code != 200:
        st.error(f"Upload failed: {response.text}")
    else:
        data = response.json()
        task_id = (data.get("data") or {}).get("task_id")
        if not task_id:
            st.error("Backend response did not include a task id.")
        else:
            st.session_state["video_task_id"] = task_id
        st.info(data.get("message", "Queued for processing."))

task_id = st.session_state.get("video_task_id")
if task_id:
    st.caption(f"Task ID: {task_id}")
    if st.button("Check status"):
        result_response = httpx.get(f"{BACKEND_URL}/results/{task_id}", timeout=60)
        if result_response.status_code == 202:
            st.info("Still processing. Try again shortly.")
        elif result_response.status_code >= 400:
            st.error(f"Task failed: {result_response.text}")
        else:
            content_type = result_response.headers.get("content-type", "")
            if content_type.startswith("video/"):
                st.video(result_response.content)
                st.download_button(
                    "Download blurred video",
                    data=result_response.content,
                    file_name="blurred_video.mp4",
                    mime=content_type,
                )
            else:
                st.warning("Unexpected response from backend.")
