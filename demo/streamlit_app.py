import httpx
import streamlit as st

from face_blur.core.config import settings

BACKEND_URL = settings.backend_url


def _check_health():
    """Call the backend health endpoint to confirm availability."""
    try:
        response = httpx.get(f"{BACKEND_URL}/health", timeout=5)
        response.raise_for_status()
        payload = response.json()
        return payload.get("status") == "ok", None
    except Exception as exc:
        return False, str(exc)


st.set_page_config(page_title="Face Blur Tester", page_icon="FB", layout="centered")
st.title("Face Blur Tester")

healthy, error_message = _check_health()
if not healthy:
    st.error("Backend is unavailable. Start the API before uploading images.")
    if error_message:
        st.caption(error_message)
    st.stop()

st.success("Backend is healthy. Upload images to begin.")

uploads = st.file_uploader(
    "Choose one or more images",
    type=sorted(settings.allowed_extensions_set()),
    accept_multiple_files=True,
)

if uploads and st.button("Submit for blurring"):
    files_payload = [
        (
            "files",
            (upload.name, upload.getvalue(), upload.type or "application/octet-stream"),
        )
        for upload in uploads
    ]
    response = httpx.post(f"{BACKEND_URL}/blur", files=files_payload, timeout=30)
    if response.status_code != 200:
        st.error(f"Upload failed: {response.text}")
    else:
        data = response.json()
        task_id = (data.get("data") or {}).get("task_id")
        if not task_id:
            st.error("Backend response did not include a task id.")
        else:
            st.session_state["task_id"] = task_id
        st.info(data.get("message", "Queued for processing."))

task_id = st.session_state.get("task_id")
if task_id:
    st.caption(f"Task ID: {task_id}")
    if st.button("Check status"):
        result_response = httpx.get(f"{BACKEND_URL}/results/{task_id}", timeout=30)
        if result_response.status_code == 202:
            st.info("Still processing. Try again shortly.")
        elif result_response.status_code >= 400:
            st.error(f"Task failed: {result_response.text}")
        else:
            content_type = result_response.headers.get("content-type", "")
            if content_type.startswith("image/"):
                st.image(result_response.content)
                st.download_button(
                    "Download blurred image",
                    data=result_response.content,
                    file_name="blurred_image.jpg",
                    mime=content_type,
                )
            elif content_type == "application/zip":
                st.download_button(
                    "Download blurred images (zip)",
                    data=result_response.content,
                    file_name="blurred_images.zip",
                    mime=content_type,
                )
            else:
                st.warning("Unexpected response from backend.")
