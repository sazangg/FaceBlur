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

    # Draw an ellipse mask to create rounded edges.
    mask = np.zeros((h, w), dtype=np.uint8)
    center = (w // 2, h // 2)
    axes = (max(1, int(w * 0.48)), max(1, int(h * 0.58)))
    cv2.ellipse(mask, center, axes, 0, 0, 360, (255,), -1)

    # Composite pixelated face into the original ROI using the mask.
    masked = cv2.bitwise_and(pixelated, pixelated, mask=mask)
    inv_mask = cv2.bitwise_not(mask)
    bg = cv2.bitwise_and(roi, roi, mask=inv_mask)
    img[y : y + h, x : x + w] = cv2.add(bg, masked)


def process_image_blur(image_bytes: bytes):
    """Decode bytes, detect faces, and return a blurred JPEG payload."""
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)  # Decode bytes into a BGR image.
    if img is None:
        raise ValueError("Could not decode image bytes")

    cascade_path = cv_data.haarcascades + "haarcascade_frontalface_default.xml"
    face_cascade = cv2.CascadeClassifier(cascade_path)  # Load frontal face cascade.
    if face_cascade.empty():
        raise FileNotFoundError(f"Missing cascade: {cascade_path}")
    alt_cascade_path = cv_data.haarcascades + "haarcascade_frontalface_alt2.xml"
    alt_face_cascade = cv2.CascadeClassifier(alt_cascade_path)
    if alt_face_cascade.empty():
        raise FileNotFoundError(f"Missing cascade: {alt_cascade_path}")
    profile_cascade = cv2.CascadeClassifier(
        cv_data.haarcascades + "haarcascade_profileface.xml"
    )
    if profile_cascade.empty():
        raise FileNotFoundError(
            f"Missing cascade: {cv_data.haarcascades}haarcascade_profileface.xml"
        )

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)  # Haar cascades expect grayscale.
    equalized = cv2.equalizeHist(gray)  # Boost contrast for tougher side angles.
    params = [
        {"scaleFactor": 1.1, "minNeighbors": 5, "minSize": (30, 30)},
        {"scaleFactor": 1.05, "minNeighbors": 3, "minSize": (24, 24)},
    ]
    faces = _detect_faces(
        [gray, equalized],
        [face_cascade, alt_face_cascade, profile_cascade],
        params,
    )

    # Flip image to detect both left/right profiles with a single cascade.
    flipped_gray = cv2.flip(gray, 1)
    flipped_equalized = cv2.flip(equalized, 1)
    flipped_faces = _detect_faces(
        [flipped_gray, flipped_equalized],
        [profile_cascade],
        [{"scaleFactor": 1.05, "minNeighbors": 3, "minSize": (24, 24)}],
    )
    width = gray.shape[1]
    for x, y, w, h in flipped_faces:
        faces.append((width - x - w, y, w, h))

    faces = _merge_overlaps(faces)

    for x, y, w, h in faces:
        _apply_pixelated_ellipse(img, x, y, w, h, block=12)

    _, buffer = cv2.imencode(".jpg", img)  # Encode result to JPEG bytes.
    return buffer.tobytes()
