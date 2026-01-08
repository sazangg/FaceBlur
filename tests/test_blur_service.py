import cv2
import numpy as np

from face_blur.services.blur_service import process_image_blur


def test_process_image_blur_returns_bytes():
    image = np.zeros((64, 64, 3), dtype=np.uint8)
    ok, buffer = cv2.imencode(".jpg", image)
    assert ok is True

    result = process_image_blur(buffer.tobytes())
    assert isinstance(result, (bytes, bytearray))
    assert len(result) > 0
