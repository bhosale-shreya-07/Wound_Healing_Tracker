"""Core image-processing pipeline for SmartHeal.

Steps: resize -> lighting normalisation -> Gaussian blur -> HSV conversion
       -> K-Means clustering -> morphology cleanup -> contour detection -> metrics.
"""
import cv2
import numpy as np

MAX_W = 800


def load_and_resize(path):
    img = cv2.imread(path)
    if img is None:
        raise ValueError("Unreadable image")
    h, w = img.shape[:2]
    scale = min(1.0, MAX_W / w)
    if scale < 1:
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    return img, scale


def normalize_lighting(img):
    """Gray-world white balance, then CLAHE on the HSV V channel."""
    ch = [img[:, :, i].astype(np.float32) for i in range(3)]
    target = np.mean([c.mean() for c in ch])
    balanced = cv2.merge(
        [np.clip(c * (target / max(c.mean(), 1e-6)), 0, 255) for c in ch]
    ).astype(np.uint8)
    hsv = cv2.cvtColor(balanced, cv2.COLOR_BGR2HSV)
    hsv[:, :, 2] = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(hsv[:, :, 2])
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)


def segment_wound(bgr, roi=None, k=3):
    """Gaussian blur -> HSV -> K-Means inside ROI. Returns binary mask (0/255) and the ROI used."""
    h, w = bgr.shape[:2]
    # Reject obvious non-skin / non-wound photos before clustering. The old
    # pipeline always picked a cluster, even for landscapes and documents.
    hsv_full = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    skin = cv2.inRange(hsv_full, np.array([0, 18, 35]), np.array([25, 210, 255]))
    skin |= cv2.inRange(hsv_full, np.array([160, 18, 35]), np.array([180, 210, 255]))
    skin_fraction = float(np.count_nonzero(skin)) / float(h * w)
    if skin_fraction < 0.08:
        raise ValueError("This image does not appear to show skin. Upload a clear, close-up wound photo.")

    blur = cv2.GaussianBlur(bgr, (7, 7), 0)
    hsv = cv2.cvtColor(blur, cv2.COLOR_BGR2HSV)

    if roi is None:  # default: central 80 % of the image
        roi = (int(.1 * w), int(.1 * h), int(.8 * w), int(.8 * h))
    x, y, rw, rh = [int(v) for v in roi]
    roi_mask = np.zeros((h, w), np.uint8)
    roi_mask[max(y, 0):y + rh, max(x, 0):x + rw] = 255

    # Hue is an angle (OpenCV stores 0-179), so map it onto a circle to avoid the red wraparound.
    hue = hsv[:, :, 0].astype(np.float32) * 2 * np.pi / 180
    S = hsv[:, :, 1] / 255.0
    V = hsv[:, :, 2] / 255.0
    feats = np.dstack([S * np.cos(hue), S * np.sin(hue), V]).reshape(-1, 3).astype(np.float32)

    idx = roi_mask.reshape(-1) > 0
    data = feats[idx]
    if len(data) < k * 50:
        raise ValueError("Region of interest too small")
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 50, 0.5)
    _, labels, centers = cv2.kmeans(data, k, None, crit, 5, cv2.KMEANS_PP_CENTERS)

    # A wound candidate should be redder than the skin background. Do not
    # silently treat the most-red cluster as a wound when all clusters look
    # alike (for example, a healthy arm or an unrelated image).
    redness = centers[:, 0]
    wound_cluster = int(np.argmax(redness))
    other_redness = np.delete(redness, wound_cluster)
    if not len(other_redness) or float(redness[wound_cluster] - other_redness.max()) < 0.12:
        raise ValueError("No clear wound-like region was found. Use a focused, well-lit wound photo.")
    selected_fraction = float(np.mean(labels.ravel() == wound_cluster))
    if selected_fraction < 0.005 or selected_fraction > 0.60:
        raise ValueError("Could not isolate a plausible wound area. Try a closer photo with the wound centered.")

    full = np.zeros(h * w, np.uint8)
    full[idx] = (labels.ravel() == wound_cluster).astype(np.uint8) * 255
    mask = full.reshape(h, w)

    ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, ker)                  # remove specks
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, ker, iterations=2)   # fill small holes
    return mask, (x, y, rw, rh)


def measure(mask, roi=None, px_per_cm=None):
    """Contour detection -> cleaned mask, largest contour and metrics."""
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    clean = np.zeros_like(mask)
    if not cnts:
        return clean, None, dict(area_px=0.0, perimeter_px=0.0, area_cm2=None,
                                 perimeter_cm=None, low_confidence=True)
    c = max(cnts, key=cv2.contourArea)
    cv2.drawContours(clean, [c], -1, 255, -1)
    area, per = float(cv2.contourArea(c)), float(cv2.arcLength(c, True))

    low = False
    if roi:
        x, y, rw, rh = roi
        bx, by, bw, bh = cv2.boundingRect(c)
        touches = bx <= x + 2 or by <= y + 2 or bx + bw >= x + rw - 2 or by + bh >= y + rh - 2
        frac = area / float(rw * rh)
        low = touches or frac < 0.005 or frac > 0.6
    return clean, c, dict(
        area_px=area, perimeter_px=per,
        area_cm2=area / px_per_cm ** 2 if px_per_cm else None,
        perimeter_cm=per / px_per_cm if px_per_cm else None,
        low_confidence=low)


def draw_overlay(bgr, contour):
    out = bgr.copy()
    if contour is not None:
        cv2.drawContours(out, [contour], -1, (0, 255, 0), 2)
    return out


def analyze(path, roi=None, calib=None):
    """Full pipeline. roi / calib arrive in ORIGINAL-image pixel coordinates."""
    img, scale = load_and_resize(path)
    norm = normalize_lighting(img)
    roi_s = tuple(v * scale for v in roi) if roi else None
    px_per_cm = None
    if calib:
        d = np.hypot(calib["x2"] - calib["x1"], calib["y2"] - calib["y1"]) * scale
        if d > 0 and float(calib["known_cm"]) > 0:
            px_per_cm = d / float(calib["known_cm"])
    mask, roi_used = segment_wound(norm, roi_s)
    clean, cnt, metrics = measure(mask, roi_used, px_per_cm)
    if cnt is None or metrics["area_px"] < max(100.0, img.shape[0] * img.shape[1] * 0.001):
        raise ValueError("No wound-like area was detected. Upload a close, clear photo showing the wound.")
    return dict(norm=norm, mask=clean, overlay=draw_overlay(norm, cnt),
                scale=scale, px_per_cm=px_per_cm, **metrics)


def apply_manual_polygon(norm, polygon, scale, px_per_cm):
    """User-drawn polygon (original coordinates) replaces the automatic mask."""
    mask = np.zeros(norm.shape[:2], np.uint8)
    pts = (np.array(polygon, np.float32) * scale).astype(np.int32)
    cv2.fillPoly(mask, [pts], 255)
    clean, cnt, m = measure(mask, None, px_per_cm)
    m["low_confidence"] = False
    return dict(mask=clean, overlay=draw_overlay(norm, cnt), **m)
