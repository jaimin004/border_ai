import cv2

from tracker import track_frame, reset_tracker
from main import detect_plates, preprocess_plate, read_plate_text
from vehicle_color import detect_vehicle_color
from snapshot_utils import save_snapshot, compute_frame_skip

VIDEO_PATH = "sample.mp4"
OUTPUT_PATH = "output_vehicle_human_anpr.mp4"

PERSON_COLOR = (0, 200, 0)      # green
VEHICLE_COLOR = (255, 140, 0)   # orange
VEHICLE_CLASSES = {"car", "motorcycle", "bus", "truck"}

TARGET_FPS = 5  # run detection at roughly this many frames/sec, not every
# source frame — see pipeline.py for the full rationale. The output video
# still plays at the source frame rate; skipped frames just reuse the most
# recent detection results so playback doesn't look choppy.


def process_vehicle(frame, track):
    """Runs ANPR on a single tracked vehicle's cropped region.
    Returns a merged dict: detection info + plate info in ONE record,
    rather than two separate, disconnected outputs."""
    x1, y1, x2, y2 = track["bbox"]
    vehicle_crop = frame[y1:y2, x1:x2]

    result = {
        "track_id": track["track_id"],
        "vehicle_class": track["class_name"],
        "detection_confidence": round(track["confidence"], 2),
        "bbox": track["bbox"],
        "color": detect_vehicle_color(vehicle_crop)["color_name"] if vehicle_crop.size > 0 else "unknown",
        "plate_text": None,
        "plate_confidence": None,
    }

    if vehicle_crop.size == 0:
        return result

    plates = detect_plates(vehicle_crop)
    if not plates:
        return result

    crop, detect_conf, _bbox = max(plates, key=lambda p: p[1])
    processed = preprocess_plate(crop)
    plate_text, ocr_conf = read_plate_text(processed)

    if plate_text:
        result["plate_text"] = plate_text
        result["plate_confidence"] = round(ocr_conf / 100, 2)

    return result


def annotate_frame(frame, persons, vehicles):
    for p in persons:
        x1, y1, x2, y2 = p["bbox"]
        cv2.rectangle(frame, (x1, y1), (x2, y2), PERSON_COLOR, 2)
        label = f"Person #{p['track_id']}"
        cv2.putText(frame, label, (x1, max(y1 - 8, 20)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, PERSON_COLOR, 2)

    for v in vehicles:
        x1, y1, x2, y2 = v["bbox"]
        cv2.rectangle(frame, (x1, y1), (x2, y2), VEHICLE_COLOR, 2)
        plate_part = f"{v['plate_text']} ({v['plate_confidence']:.0%})" if v["plate_text"] else "plate: unreadable"
        label = f"{v['color']} {v['vehicle_class']} #{v['track_id']} | {plate_part}"
        cv2.putText(frame, label, (x1, max(y1 - 8, 20)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, VEHICLE_COLOR, 2)

    return frame


def save_detection_snapshots(frame, persons, vehicles):
    """Saves ONE evidence image per detected person/vehicle this frame,
    with that detection's bounding box + label burned into the image."""
    for p in persons:
        save_snapshot(
            frame, prefix="person", track_id=p["track_id"],
            boxes=[(p["bbox"], f"Person #{p['track_id']}", PERSON_COLOR)],
        )
    for v in vehicles:
        plate_part = v["plate_text"] if v["plate_text"] else "unreadable"
        label = f"{v['color']} {v['vehicle_class']} #{v['track_id']} | {plate_part}"
        save_snapshot(
            frame, prefix="vehicle", track_id=v["track_id"],
            boxes=[(v["bbox"], label, VEHICLE_COLOR)],
        )


def main():
    reset_tracker()
    cap = cv2.VideoCapture(VIDEO_PATH)
    if not cap.isOpened():
        print(f"Could not open {VIDEO_PATH}")
        return

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    frame_skip = compute_frame_skip(fps, TARGET_FPS)
    print(f"Source video: {fps:.1f} fps -> sampling every {frame_skip} frame(s) "
          f"(~{fps / frame_skip:.1f} fps effective detection rate)")

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(OUTPUT_PATH, fourcc, fps, (width, height))

    frame_num = 0
    processed_count = 0
    last_persons, last_vehicles = [], []  # reused on skipped frames so output video stays smooth

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_num % frame_skip == 0:
            tracks = track_frame(frame)
            processed_count += 1
            persons = [t for t in tracks if t["class_name"] == "person"]
            vehicles_raw = [t for t in tracks if t["class_name"] in VEHICLE_CLASSES]
            vehicles = [process_vehicle(frame, t) for t in vehicles_raw]

            for v in vehicles:
                if v["plate_text"]:
                    print(f"Frame {frame_num}: {v['vehicle_class']} #{v['track_id']} "
                          f"-> plate {v['plate_text']} ({v['plate_confidence']:.0%})")

            save_detection_snapshots(frame, persons, vehicles)

            last_persons, last_vehicles = persons, vehicles
        # else: skip detection entirely this frame, reuse last_persons/last_vehicles
        # for the output video below — no new snapshot is saved for a frame
        # nothing new was actually detected on.

        annotated = annotate_frame(frame, last_persons, last_vehicles)
        out.write(annotated)
        frame_num += 1

    cap.release()
    out.release()
    print(f"\nDone. Read {frame_num} frames, ran detection on {processed_count} of them "
          f"({frame_skip}x sampling). Saved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
