import time

import cv2
import requests

from tracker import track_frame, reset_tracker
from zone_logic import check_zone_and_loiter, reset_track
from vehicle_analytics import track_vehicle_motion, reset_vehicle
from day2_stubs import detect_faces, check_watchlist, mask_privacy
from main import detect_plates, preprocess_plate, read_plate_text  # main.py loads its own plate model on import
from alert_engine import generate_alert, alert_queue
from correlation import correlate_and_boost
from snapshot_utils import save_snapshot, compute_frame_skip

CAMERA_ID = "cam_01"
VIDEO_PATH = "sample.mp4"
BACKEND_URL = "http://127.0.0.1:8001/api/events"  # the real Postgres-backed dashboard API
# NOTE: this assumes the Docker stack is running (docker-compose up), which
# maps the backend container's port 8000 to 8001 on the host. If you're
# running backend/app directly with uvicorn instead of Docker, change this
# to match whatever port you actually started it on.

TARGET_FPS = 5  # run detection at roughly this many frames/sec, not every
# single source frame. On a 30fps video that's 1 frame in every 6 actually
# processed. This matches the report's own "frame sampling" design (Section
# 6, step 2) and is a real, meaningful compute saving on CPU or edge
# hardware. Tracking quality can degrade a little at low sample rates since
# ByteTrack's motion model expects fairly regular updates — 5fps is a
# reasonable starting point; raise it if tracks start switching IDs.
CORRELATION_LOOKBACK = 20  # how many recent events to check new ones against

VEHICLE_CLASSES = {"car", "motorcycle", "bus", "truck"}


def send_to_backend(event):
    """POSTs to the FastAPI backend. Falls back to local-only (already in
    alert_queue) if the backend isn't running — this is exactly the kind
    of graceful-degradation behavior the offline-mode feature will later
    make official, but even without that yet, a demo shouldn't crash just
    because uvicorn isn't running in another terminal."""
    try:
        requests.post(BACKEND_URL, json=event, timeout=1)
    except requests.exceptions.RequestException:
        print(f"  (backend unreachable — {event['id']} kept in local alert_queue only)")


def process_person_track(frame, track):
    track_id = str(track["track_id"]) if track["track_id"] is not None else None
    if track_id is None:
        return  # not yet stable enough to reason about

    x1, y1, x2, y2 = track["bbox"]
    factors = check_zone_and_loiter(track_id, (x1, y1, x2, y2))

    if not any(factors.values()):
        return  # nothing worth an event yet — don't spam generate_alert for every walking person

    # Rough face region: top third of the person's bounding box
    person_crop = frame[y1:y2, x1:x2]
    face_match = None
    if person_crop.size > 0:
        top_third = person_crop[: max(1, (y2 - y1) // 3), :]
        faces = detect_faces(top_third)
        if faces:
            fx, fy, fw, fh = faces[0]
            face_crop = top_third[fy:fy + fh, fx:fx + fw]
            if face_crop.size > 0:
                face_match = check_watchlist(face_crop)

    if factors["restricted_zone_entry"]:
        event_type = "zone_intrusion"
    elif factors["loitering"]:
        event_type = "loitering"
    elif factors["movement_toward_boundary"]:
        event_type = "approaching_boundary"
    else:
        event_type = "unknown"  # shouldn't reach here given the any(factors.values()) check above

    snapshot_label = f"Person #{track_id} | {event_type.replace('_', ' ')}"
    faces_in_frame = detect_faces(frame)
    snapshot_path = save_snapshot(
        frame, prefix=f"{CAMERA_ID}_person", track_id=track_id,
        boxes=[((x1, y1, x2, y2), snapshot_label, (0, 200, 0))],
        mask_fn=mask_privacy, mask_regions=faces_in_frame,
    )

    event = generate_alert(
        camera_id=CAMERA_ID, track_id=track_id, object_class="person",
        event_type=event_type, factors=factors,
        snapshot_path=snapshot_path, face_match=face_match,
    )
    event = correlate_and_boost(event, alert_queue[-CORRELATION_LOOKBACK:])

    print(f"  [PERSON trk_{track_id}] {event['event_type']} score={event['risk_score']} "
          f"severity={event['severity']} escalated={event['escalated']} "
          f"face={event['face_match']}")

    if event["escalated"]:
        send_to_backend(event)


def process_vehicle_track(frame, track):
    track_id = str(track["track_id"]) if track["track_id"] is not None else None
    if track_id is None:
        return

    x1, y1, x2, y2 = track["bbox"]

    # Reuse the SAME zone/loiter logic used for people — it's class-agnostic.
    # A vehicle loitering in or entering a restricted zone is exactly as
    # meaningful as a person doing so, per report Section 7.6.
    factors = check_zone_and_loiter(track_id, (x1, y1, x2, y2))

    # Motion analytics: direction, relative speed, checkpoint-line crossing.
    # These are attached as informational context, not scored as risk —
    # a vehicle crossing a checkpoint is normal traffic, not a violation.
    motion = track_vehicle_motion(track_id, (x1, y1, x2, y2))

    # ANPR — always attempted; a clean plate read is useful even for a
    # vehicle with no zone violation (routine checkpoint logging).
    vehicle_crop = frame[y1:y2, x1:x2]
    plate_text, plate_confidence = None, None
    if vehicle_crop.size > 0:
        plates = detect_plates(vehicle_crop)
        if plates:
            crop, _detect_conf, _bbox = plates[0]
            processed = preprocess_plate(crop)
            text, ocr_conf = read_plate_text(processed)
            if text:
                plate_text, plate_confidence = text, round(ocr_conf / 100, 2)

    # Nothing worth recording: no zone/loiter/boundary factor fired, and no
    # readable plate — avoid generating noise events for irrelevant traffic.
    if not any(factors.values()) and plate_text is None:
        return

    event_type = ("zone_intrusion" if factors["restricted_zone_entry"]
                  else "loitering" if factors["loitering"]
                  else "approaching_boundary" if factors["movement_toward_boundary"]
                  else "vehicle_logged")

    plate_part = plate_text if plate_text else "unreadable"
    snapshot_label = f"{track['class_name']} #{track_id} | {plate_part}"
    snapshot_path = save_snapshot(
        frame, prefix=f"{CAMERA_ID}_vehicle", track_id=track_id,
        boxes=[((x1, y1, x2, y2), snapshot_label, (255, 140, 0))],
    )

    event = generate_alert(
        camera_id=CAMERA_ID, track_id=track_id, object_class=track["class_name"],
        event_type=event_type, factors=factors,
        snapshot_path=snapshot_path, plate_confidence=plate_confidence,
    )
    event["plate_text"] = plate_text  # not in the original schema, useful to carry along
    event["direction"] = motion["direction"]
    event["speed_px_per_sec"] = motion["speed_px_per_sec"]
    event["crossed_checkpoint"] = motion["crossed_checkpoint"]

    event = correlate_and_boost(event, alert_queue[-CORRELATION_LOOKBACK:])

    print(f"  [VEHICLE trk_{track_id}] {event['event_type']} plate={plate_text} "
          f"dir={motion['direction']} crossed={motion['crossed_checkpoint']} "
          f"score={event['risk_score']} escalated={event['escalated']}")

    if event["escalated"]:
        send_to_backend(event)


def main():
    reset_tracker()
    cap = cv2.VideoCapture(VIDEO_PATH)
    if not cap.isOpened():
        print(f"Could not open {VIDEO_PATH}")
        return

    source_fps = cap.get(cv2.CAP_PROP_FPS)
    frame_skip = compute_frame_skip(source_fps, TARGET_FPS)
    print(f"Source video: {source_fps:.1f} fps -> sampling every {frame_skip} frame(s) "
          f"(~{source_fps / frame_skip:.1f} fps effective detection rate)")

    frame_num = 0
    processed_count = 0
    seen_track_ids = set()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_num % frame_skip != 0:
            frame_num += 1
            continue  # skip detection on this frame — sampling, not processing every frame

        tracks = track_frame(frame)
        processed_count += 1
        print(f"\nFrame {frame_num}: {len(tracks)} tracked object(s)")

        for track in tracks:
            if track["track_id"] is not None:
                seen_track_ids.add(track["track_id"])
            if track["class_name"] == "person":
                process_person_track(frame, track)
            elif track["class_name"] in VEHICLE_CLASSES:
                process_vehicle_track(frame, track)

        frame_num += 1

    cap.release()
    print(f"\nDone. Read {frame_num} frames, ran detection on {processed_count} of them "
          f"({frame_skip}x sampling). {len(alert_queue)} events escalated across the run.")


if __name__ == "__main__":
    main()
