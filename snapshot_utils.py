import os
import time
import cv2

EVIDENCE_DIR = "evidence"


def ensure_evidence_dir():
    os.makedirs(EVIDENCE_DIR, exist_ok=True)


def draw_box(frame, bbox, label, color=(0, 200, 0), thickness=2):
    """Draws one labeled bounding box directly onto frame (in place)."""
    x1, y1, x2, y2 = bbox
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
    label_y = max(y1 - 8, th + 4)
    cv2.rectangle(frame, (x1, label_y - th - 6), (x1 + tw + 6, label_y + 2), color, -1)
    cv2.putText(frame, label, (x1 + 3, label_y - 3),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    return frame


def save_snapshot(frame, prefix, track_id=None, boxes=None, mask_fn=None, mask_regions=None):
    """Saves the frame as an evidence image WITH bounding boxes drawn on it.

    frame: the source frame (not modified — a copy is made and saved)
    prefix: short tag for the filename, e.g. "cam_01_person" or "cam_01_vehicle"
    track_id: appended to the filename for traceability back to the track
    boxes: list of (bbox, label, color) tuples to draw on the saved copy
    mask_fn / mask_regions: optional privacy-mask function + regions (e.g.
        day2_stubs.mask_privacy + detected face boxes) applied BEFORE the
        bounding boxes are drawn, so the box/label stay clearly visible
        while faces underneath them stay blurred.

    Returns the saved file path.
    """
    ensure_evidence_dir()
    snapshot = frame.copy()

    if mask_fn and mask_regions:
        snapshot = mask_fn(snapshot, mask_regions)

    for bbox, label, color in (boxes or []):
        draw_box(snapshot, bbox, label, color)

    ts_ms = int(time.time() * 1000)  # millisecond precision avoids filename
    # collisions when multiple detections are saved within the same second
    tid_part = f"_{track_id}" if track_id is not None else ""
    path = os.path.join(EVIDENCE_DIR, f"{prefix}{tid_part}_{ts_ms}.jpg")
    cv2.imwrite(path, snapshot)
    return path


def compute_frame_skip(source_fps, target_fps):
    """How many source frames to advance between processed samples, so
    detection runs at roughly target_fps regardless of the source video's
    native frame rate. Always returns at least 1 (never upsamples)."""
    if not source_fps or source_fps <= 0:
        source_fps = 30
    return max(1, round(source_fps / target_fps))


# ---------------------------------------------------------------------------
# Quick test — draw + save on a synthetic frame, no ML stack needed
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import numpy as np

    frame = np.full((480, 640, 3), (230, 230, 230), dtype=np.uint8)

    path = save_snapshot(
        frame,
        prefix="test_person",
        track_id="7",
        boxes=[((100, 100, 220, 380), "Person #7", (0, 200, 0))],
    )
    print("Saved:", path)
    saved = cv2.imread(path)
    print("Readable back, shape:", saved.shape)

    print("compute_frame_skip(30, 5) =", compute_frame_skip(30, 5), "(expect 6)")
    print("compute_frame_skip(24, 5) =", compute_frame_skip(24, 5), "(expect 5)")
    print("compute_frame_skip(0, 5)  =", compute_frame_skip(0, 5), "(expect 6, falls back to 30fps assumption)")
