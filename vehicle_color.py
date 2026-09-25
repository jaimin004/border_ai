import cv2
import numpy as np

# Reference colors in BGR (OpenCV order), for nearest-match naming.
# Tuned toward common vehicle paint colors rather than the full color wheel.
NAMED_COLORS = {
    "white":  (255, 255, 255),
    "black":  (20, 20, 20),
    "gray":   (128, 128, 128),
    "silver": (192, 192, 192),
    "red":    (40, 40, 200),
    "blue":   (200, 80, 40),
    "green":  (60, 130, 60),
    "yellow": (40, 210, 230),
    "orange": (30, 120, 230),
    "brown":  (40, 70, 110),
}


def _nearest_color_name(bgr):
    best_name, best_dist = None, float("inf")
    for name, ref in NAMED_COLORS.items():
        dist = sum((int(a) - int(b)) ** 2 for a, b in zip(bgr, ref))
        if dist < best_dist:
            best_dist, best_name = dist, name
    return best_name


def detect_vehicle_color(vehicle_crop, k=3, center_fraction=0.6):
    """Extracts the dominant body-paint color from a cropped vehicle image.

    Approach: crop to the central region (avoids background, wheels/tires,
    and windshield glare at the edges), then run k-means clustering on the
    pixels and pick the largest cluster as the dominant color. This is
    classical CV, not a trained model \u2014 fully deterministic and easy to
    explain to judges, and needs no new heavy dependency.

    Returns: {"color_name": str, "bgr": (b, g, r)}
    """
    h, w = vehicle_crop.shape[:2]
    if h == 0 or w == 0:
        return {"color_name": "unknown", "bgr": None}

    # Crop to the central portion of the vehicle box to reduce background/edge noise
    cy0, cy1 = int(h * (1 - center_fraction) / 2), int(h * (1 + center_fraction) / 2)
    cx0, cx1 = int(w * (1 - center_fraction) / 2), int(w * (1 + center_fraction) / 2)
    central = vehicle_crop[cy0:cy1, cx0:cx1]
    if central.size == 0:
        central = vehicle_crop

    pixels = central.reshape(-1, 3).astype(np.float32)

    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 0.5)
    k = min(k, len(pixels))
    _compactness, labels, centers = cv2.kmeans(
        pixels, k, None, criteria, attempts=3, flags=cv2.KMEANS_PP_CENTERS
    )

    # Pick the largest cluster as the dominant color
    counts = np.bincount(labels.flatten())
    dominant_bgr = tuple(int(v) for v in centers[np.argmax(counts)])

    return {"color_name": _nearest_color_name(dominant_bgr), "bgr": dominant_bgr}


# ---------------------------------------------------------------------------
# Quick test on a real vehicle photo
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    TEST_IMAGE = "vehicle.jpg"
    img = cv2.imread(TEST_IMAGE)
    if img is None:
        print(f"Could not read {TEST_IMAGE}")
        exit()

    # For this quick test, treat the whole image as the "vehicle crop"
    # (in the real pipeline, this would be the YOLO-cropped vehicle box)
    result = detect_vehicle_color(img)
    print("Detected color:", result)
