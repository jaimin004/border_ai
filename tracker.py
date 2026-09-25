from ultralytics import YOLO

# Generic pretrained COCO weights — auto-downloads on first run.
# Classes of interest: 0=person, 2=car, 3=motorcycle, 5=bus, 7=truck
# 24=backpack, 26=handbag, 28=suitcase — added for abandoned-object detection
DETECT_MODEL_PATH = "yolov8n.pt"
TRACKED_CLASSES = [0, 2, 3, 5, 7, 24, 26, 28]

CLASS_NAMES = {
    0: "person", 2: "car", 3: "motorcycle", 5: "bus", 7: "truck",
    24: "backpack", 26: "handbag", 28: "suitcase",
}

_model = None


def get_model():
    global _model
    if _model is None:
        _model = YOLO(DETECT_MODEL_PATH)
    return _model


def track_frame(frame, conf=0.4):
    """Runs detection + ByteTrack (built into ultralytics via .track())
    on a single frame. Returns a list of dicts:
      { "track_id": int, "class_name": str, "bbox": (x1, y1, x2, y2), "confidence": float }
    track_id is None for a detection that hasn't been assigned a stable
    track yet (can happen on the first couple of frames) — callers should
    handle that case rather than assume every detection has an ID.
    """
    model = get_model()
    results = model.track(
        frame, persist=True, classes=TRACKED_CLASSES, conf=conf, verbose=False
    )[0]

    tracks = []
    if results.boxes is None:
        return tracks

    for box in results.boxes:
        cls_id = int(box.cls[0])
        track_id = int(box.id[0]) if box.id is not None else None
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        confidence = float(box.conf[0])

        tracks.append({
            "track_id": track_id,
            "class_name": CLASS_NAMES.get(cls_id, "unknown"),
            "bbox": (x1, y1, x2, y2),
            "confidence": confidence,
        })

    return tracks


def reset_tracker():
    """Ultralytics keeps tracker state tied to the model instance — call
    this if you start processing a new, unrelated video in the same
    process, so old track IDs don't bleed into the new video."""
    global _model
    _model = None


# ---------------------------------------------------------------------------
# Quick test — run detection+tracking on a couple of frames from a video
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import cv2

    VIDEO_PATH = "sample.mp4"
    cap = cv2.VideoCapture(VIDEO_PATH)
    if not cap.isOpened():
        print(f"Could not open {VIDEO_PATH} — put a test video in this folder.")
        exit()

    frame_count = 0
    while frame_count < 5:
        ret, frame = cap.read()
        if not ret:
            break
        tracks = track_frame(frame)
        print(f"Frame {frame_count}: {len(tracks)} tracked object(s)")
        for t in tracks:
            print(f"  id={t['track_id']} class={t['class_name']} bbox={t['bbox']} conf={t['confidence']:.2f}")
        frame_count += 1

    cap.release()
