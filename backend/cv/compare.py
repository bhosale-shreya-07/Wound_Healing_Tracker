"""Alignment (ORB + RANSAC) and image subtraction between two dated images."""
import cv2
import numpy as np


def align(prev_gray, curr_gray):
    orb = cv2.ORB_create(1500)
    k1, d1 = orb.detectAndCompute(prev_gray, None)
    k2, d2 = orb.detectAndCompute(curr_gray, None)
    if d1 is None or d2 is None:
        return None
    matches = sorted(cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True).match(d1, d2),
                     key=lambda m: m.distance)[:100]
    if len(matches) < 10:
        return None
    src = np.float32([k1[m.queryIdx].pt for m in matches])
    dst = np.float32([k2[m.trainIdx].pt for m in matches])
    M, inl = cv2.estimateAffinePartial2D(src, dst, method=cv2.RANSAC, ransacReprojThreshold=3)
    return M if M is not None and inl.sum() >= 8 else None


def centroid(mask):
    m = cv2.moments(mask, True)
    return (m["m10"] / m["m00"], m["m01"] / m["m00"]) if m["m00"] else (0, 0)


def compare_images(prev, curr):
    """prev / curr: dict(norm, mask, area_cm2). Returns metrics + visualisation."""
    h, w = curr["mask"].shape
    pg = cv2.cvtColor(prev["norm"], cv2.COLOR_BGR2GRAY)
    cg = cv2.cvtColor(curr["norm"], cv2.COLOR_BGR2GRAY)
    M = align(pg, cg)
    aligned = M is not None
    if not aligned:  # fallback: align wound centroids only
        (px, py), (cx, cy) = centroid(prev["mask"]), centroid(curr["mask"])
        M = np.float32([[1, 0, cx - px], [0, 1, cy - py]])

    prev_mask = cv2.warpAffine(prev["mask"], M, (w, h), flags=cv2.INTER_NEAREST)
    prev_img = cv2.warpAffine(prev["norm"], M, (w, h))

    # --- IMAGE SUBTRACTION ---
    healed = cv2.subtract(prev_mask, curr["mask"])   # wound before, skin now
    grown = cv2.subtract(curr["mask"], prev_mask)    # skin before, wound now
    diff = cv2.absdiff(cv2.GaussianBlur(prev_img, (9, 9), 0),
                       cv2.GaussianBlur(curr["norm"], (9, 9), 0))
    diff_gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
    heat = cv2.applyColorMap(cv2.normalize(diff_gray, None, 0, 255, cv2.NORM_MINMAX),
                             cv2.COLORMAP_JET)

    vis = curr["norm"].copy()
    vis[healed > 0] = (0.5 * vis[healed > 0] + 0.5 * np.array([0, 200, 0])).astype(np.uint8)  # green
    vis[grown > 0] = (0.5 * vis[grown > 0] + 0.5 * np.array([0, 0, 220])).astype(np.uint8)    # red
    vis = cv2.addWeighted(vis, 0.75, heat, 0.25, 0)

    # --- % change (positive = smaller) ---
    prev_px = float(np.count_nonzero(prev_mask))
    curr_px = float(np.count_nonzero(curr["mask"]))
    if prev["area_cm2"] and curr["area_cm2"]:
        a0, a1 = prev["area_cm2"], curr["area_cm2"]
    else:
        a0, a1 = prev_px, curr_px
    pct = (a0 - a1) / a0 * 100 if a0 > 0 else None
    return dict(pct_change=pct, healed_px=int(np.count_nonzero(healed)),
                grown_px=int(np.count_nonzero(grown)), aligned=aligned, vis=vis)
