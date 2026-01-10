import cv2
import numpy as np
from cv2 import data as cv_data


def _detect_faces(images, cascades, params):
    """Run Haar cascades across image variants and parameter sets."""
    faces = []
    for image in images:
        for cascade in cascades:
            for param in params:
                faces.extend(cascade.detectMultiScale(image, **param))
    return faces


def _merge_overlaps(boxes, overlap_thresh=0.2):
    """Merge overlapping boxes to reduce duplicate detections."""
    if not boxes:
        return []

    boxes = np.array(boxes, dtype=np.float32)
    x1 = boxes[:, 0]
    y1 = boxes[:, 1]
    x2 = x1 + boxes[:, 2]
    y2 = y1 + boxes[:, 3]
    areas = (x2 - x1 + 1) * (y2 - y1 + 1)
    order = areas.argsort()[::-1]
    picked = []

    while order.size > 0:
        i = order[0]
        picked.append(i)

        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])

        w = np.maximum(0.0, xx2 - xx1 + 1)
        h = np.maximum(0.0, yy2 - yy1 + 1)
        overlap = (w * h) / areas[order[1:]]

        order = order[1:][overlap <= overlap_thresh]

    return boxes[picked].astype(int).tolist()


def _apply_pixelated_ellipse(img, x, y, w, h, block=10):
    """Pixelate a face region and mask it with a rounded ellipse."""
    roi = img[y : y + h, x : x + w]
    if roi.size == 0:
        return

    # Pixelate by shrinking then expanding the ROI.
    small_w = max(1, w // block)
    small_h = max(1, h // block)
    small = cv2.resize(roi, (small_w, small_h), interpolation=cv2.INTER_LINEAR)
    pixelated = cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)
    sigma = max(2.0, min(w, h) / 30.0)
    softened = cv2.GaussianBlur(pixelated, (0, 0), sigmaX=sigma, sigmaY=sigma)
    pixelated = cv2.addWeighted(pixelated, 0.6, softened, 0.4, 0)

    # Draw an ellipse mask to create rounded edges.
    mask = np.zeros((h, w), dtype=np.uint8)
    center = (w // 2, h // 2)
    axes = (max(1, int(w * 0.52)), max(1, int(h * 0.62)))
    cv2.ellipse(mask, center, axes, 0, 0, 360, (255,), -1)

    # Composite pixelated face into the original ROI using the mask.
    masked = cv2.bitwise_and(pixelated, pixelated, mask=mask)
    inv_mask = cv2.bitwise_not(mask)
    bg = cv2.bitwise_and(roi, roi, mask=inv_mask)
    img[y : y + h, x : x + w] = cv2.add(bg, masked)


class FaceDetector:
    """Load and reuse Haar cascades across multiple frames."""

    def __init__(self):
        cascade_path = cv_data.haarcascades + "haarcascade_frontalface_default.xml"
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        if self.face_cascade.empty():
            raise FileNotFoundError(f"Missing cascade: {cascade_path}")
        alt_cascade_path = cv_data.haarcascades + "haarcascade_frontalface_alt2.xml"
        self.alt_face_cascade = cv2.CascadeClassifier(alt_cascade_path)
        if self.alt_face_cascade.empty():
            raise FileNotFoundError(f"Missing cascade: {alt_cascade_path}")
        profile_path = cv_data.haarcascades + "haarcascade_profileface.xml"
        self.profile_cascade = cv2.CascadeClassifier(profile_path)
        if self.profile_cascade.empty():
            raise FileNotFoundError(f"Missing cascade: {profile_path}")

    def detect(self, gray, equalized):
        params = [
            {"scaleFactor": 1.1, "minNeighbors": 5, "minSize": (30, 30)},
            {"scaleFactor": 1.05, "minNeighbors": 3, "minSize": (24, 24)},
        ]
        faces = _detect_faces(
            [gray, equalized],
            [self.face_cascade, self.alt_face_cascade, self.profile_cascade],
            params,
        )

        flipped_gray = cv2.flip(gray, 1)
        flipped_equalized = cv2.flip(equalized, 1)
        flipped_faces = _detect_faces(
            [flipped_gray, flipped_equalized],
            [self.profile_cascade],
            [{"scaleFactor": 1.05, "minNeighbors": 3, "minSize": (24, 24)}],
        )
        width = gray.shape[1]
        for x, y, w, h in flipped_faces:
            faces.append((width - x - w, y, w, h))

        return _merge_overlaps(faces)


_DETECTOR: FaceDetector | None = None


def _get_detector():
    global _DETECTOR
    if _DETECTOR is None:
        _DETECTOR = FaceDetector()
    return _DETECTOR


def _detect_faces_in_frame(img: np.ndarray, scale: float = 1.0):
    """Detect faces on a possibly downscaled frame and return boxes in original scale."""
    if img is None:
        raise ValueError("Could not decode image bytes")
    detector = _get_detector()
    if scale < 1.0:
        height, width = img.shape[:2]
        resized = cv2.resize(
            img,
            (max(1, int(width * scale)), max(1, int(height * scale))),
            interpolation=cv2.INTER_AREA,
        )
    else:
        resized = img

    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    equalized = cv2.equalizeHist(gray)
    faces = detector.detect(gray, equalized)
    if scale < 1.0:
        inv_scale = 1.0 / scale
        faces = [
            (
                int(x * inv_scale),
                int(y * inv_scale),
                int(w * inv_scale),
                int(h * inv_scale),
            )
            for (x, y, w, h) in faces
        ]
    return faces


def detect_faces(img: np.ndarray, scale: float = 1.0):
    """Detect faces on a frame and return bounding boxes."""
    return _detect_faces_in_frame(img, scale=scale)


def apply_blur(img: np.ndarray, faces):
    """Apply blur to a frame using precomputed face boxes."""
    if not faces:
        return img
    for x, y, w, h in faces:
        pad_x = int(w * 0.2)
        pad_y = int(h * 0.2)
        x0 = max(0, x - pad_x)
        y0 = max(0, y - pad_y)
        x1 = min(img.shape[1], x + w + pad_x)
        y1 = min(img.shape[0], y + h + pad_y)
        adjusted_w = max(1, x1 - x0)
        adjusted_h = max(1, y1 - y0)
        block = max(12, min(adjusted_w, adjusted_h) // 8)
        _apply_pixelated_ellipse(img, x0, y0, adjusted_w, adjusted_h, block=block)

    return img


def blur_frame(img: np.ndarray, detect_scale: float = 1.0):
    """Blur detected faces on a BGR frame in-place and return it."""
    faces = _detect_faces_in_frame(img, scale=detect_scale)
    return apply_blur(img, faces)


def process_image_blur(image_bytes: bytes):
    """Decode bytes, detect faces, and return a blurred JPEG payload."""
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)  # Decode bytes into a BGR image.
    if img is None:
        raise ValueError("Could not decode image bytes")

    blurred = blur_frame(img)
    _, buffer = cv2.imencode(".jpg", blurred)  # Encode result to JPEG bytes.
    return buffer.tobytes()
