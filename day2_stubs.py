import os
import cv2
from deepface import DeepFace

FACE_CASCADE = cv2.CascadeClassifier("haarcascade_frontalface_default.xml")

if FACE_CASCADE.empty():
    raise FileNotFoundError(
        "haarcascade_frontalface_default.xml not found or failed to load. "
        "Download it into this folder with:\n"
        "curl -L -o haarcascade_frontalface_default.xml "
        "https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_default.xml"
    )

WATCHLIST_DIR = "watchlist_cropped"  # run prepare_watchlist.py once to generate this from watchlist/
MODEL_NAME = "Facenet"  # pretrained deep embedding model — far stronger than LBPH


# ---------------------------------------------------------------------------
# Face detection (used by both functions below)
# ---------------------------------------------------------------------------
def detect_faces(frame):
    """Returns a list of (x, y, w, h) face boxes using OpenCV's built-in
    Haar cascade — no extra model download needed."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = FACE_CASCADE.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40))
    return [tuple(f) for f in faces]


# ---------------------------------------------------------------------------
# check_watchlist — DeepFace with a pretrained Facenet embedding model.
# The model itself is already trained on large public face datasets by its
# original authors (weights auto-download on first run) — you only ever
# provide a handful of photos per authorized person, in watchlist/<name>/,
# exactly the same folder structure as before. Nothing about your workflow
# for building the watchlist changes, only the matching engine underneath.
# ---------------------------------------------------------------------------
def check_watchlist(face_crop_bgr, watchlist_dir=WATCHLIST_DIR, model_name=MODEL_NAME):
    """face_crop_bgr: a cropped face image in BGR (straight from a cv2 frame slice).
    Returns a dict matching the event_schema.json 'face_match' field:
      { "matched": bool, "confidence": float (0-1), "name": str | None }
    """
    if not os.path.isdir(watchlist_dir) or not os.listdir(watchlist_dir):
        return {"matched": False, "confidence": 0.0, "name": None}

    try:
        results = DeepFace.find(
            img_path=face_crop_bgr,
            db_path=watchlist_dir,
            model_name=model_name,
            detector_backend="skip",  # we already detected/cropped the face ourselves
            enforce_detection=False,
            silent=True,
        )
    except Exception as e:
        print(f"Watchlist check failed: {e}")
        return {"matched": False, "confidence": 0.0, "name": None}

    df = results[0]  # one DataFrame, since detector_backend="skip" treats the crop as one face
    if df.empty:
        # DeepFace already filters out anything beyond its pretuned distance
        # threshold, so an empty result here genuinely means "no match."
        return {"matched": False, "confidence": 0.0, "name": None}

    best = df.iloc[0]  # sorted by distance ascending, already threshold-filtered
    name = os.path.basename(os.path.dirname(best["identity"]))
    return {"matched": True, "confidence": round(float(best["confidence"]), 2), "name": name}


# ---------------------------------------------------------------------------
# mask_privacy — blur given regions (faces and/or plates) before a frame
# is saved as evidence, per Section 12 (privacy-by-design) of the report.
# ---------------------------------------------------------------------------
def mask_privacy(frame, boxes):
    """boxes: list of (x, y, w, h) OR (x1, y1, x2, y2) — both accepted.
    Returns a copy of frame with each region heavily blurred."""
    output = frame.copy()
    h_frame, w_frame = frame.shape[:2]

    for box in boxes:
        if len(box) != 4:
            continue
        a, b, c, d = box
        if c > a and d > b and c <= w_frame and d <= h_frame:
            x1, y1, x2, y2 = a, b, c, d
        else:
            x1, y1, x2, y2 = a, b, a + c, b + d

        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w_frame, x2), min(h_frame, y2)
        if x2 <= x1 or y2 <= y1:
            continue

        region = output[y1:y2, x1:x2]
        blurred = cv2.GaussianBlur(region, (51, 51), 30)
        output[y1:y2, x1:x2] = blurred

    return output


# ---------------------------------------------------------------------------
# Quick test — run this file directly on a photo to check both functions
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    TEST_IMAGE = "test_face.jpeg"  # any photo with a visible face (works with multiple faces too)

    frame = cv2.imread(TEST_IMAGE)
    if frame is None:
        print(f"Could not read {TEST_IMAGE} — put a test photo in this folder.")
        exit()

    faces = detect_faces(frame)
    print(f"Detected {len(faces)} face(s).")

    identified = frame.copy()  # a labeled, unblurred view — for the operator dashboard, not stored evidence

    for i, (x, y, w, h) in enumerate(faces):
        face_crop = frame[y:y + h, x:x + w]
        result = check_watchlist(face_crop)
        print(f"Face #{i}: {result}")

        color = (0, 255, 0) if result["matched"] else (0, 0, 255)
        label = f"{result['name']} ({result['confidence']:.0%})" if result["matched"] else "Unknown"

        cv2.rectangle(identified, (x, y), (x + w, y + h), color, 2)
        cv2.putText(identified, label, (x, max(y - 10, 20)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

    cv2.imwrite("test_face_identified.jpg", identified)
    print("Saved test_face_identified.jpg — labeled, for internal/operator view only.")

    masked = mask_privacy(frame, faces)
    cv2.imwrite("test_face_masked.jpg", masked)
    print("Saved test_face_masked.jpg — blurred, for stored evidence.")