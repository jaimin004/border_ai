import time
import math

OBJECT_CLASSES = {"backpack", "handbag", "suitcase"}

STATIONARY_MOVE_THRESHOLD_PX = 25   # object center must move less than this to count as "not moved"
PROXIMITY_THRESHOLD_PX = 150        # a person within this distance counts as a possible owner nearby
STATIONARY_SECONDS = 5              # object must be still this long before the unattended clock starts
UNATTENDED_SECONDS = 15             # then unattended (no nearby person) this long -> abandoned
# NOTE: like loitering, these are wall-clock seconds. On live video this is
# correct. On a fast-processing offline file, real seconds can elapse faster
# than the seconds shown in the footage — see zone_logic.py's same caveat.

# Per-object-track state, keyed by track_id
_object_state = {}


def _center(bbox):
    x1, y1, x2, y2 = bbox
    return ((x1 + x2) / 2, (y1 + y2) / 2)


def _distance(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def check_abandoned(track_id, object_bbox, person_bboxes,
                     stationary_seconds=STATIONARY_SECONDS,
                     unattended_seconds=UNATTENDED_SECONDS):
    """Call once per frame per tracked object (backpack/handbag/suitcase).

    object_bbox: (x1, y1, x2, y2) of the object track this frame
    person_bboxes: list of (x1, y1, x2, y2) for every currently tracked person

    Returns: {"abandoned": bool, "stationary_seconds": float, "unattended_seconds": float}
    """
    now = time.time()
    center = _center(object_bbox)

    state = _object_state.setdefault(track_id, {
        "last_position": center,
        "became_stationary_at": now,   # optimistic start; reset below if it moves
        "last_person_nearby_at": now,  # optimistic start; a person may have just placed it
    })

    # Did the object move since last frame? If so, it's not stationary — reset the clock.
    moved = _distance(center, state["last_position"]) > STATIONARY_MOVE_THRESHOLD_PX
    if moved:
        state["became_stationary_at"] = now
    state["last_position"] = center

    stationary_duration = now - state["became_stationary_at"]

    # Is any tracked person currently near this object?
    person_nearby = any(_distance(center, _center(p)) <= PROXIMITY_THRESHOLD_PX for p in person_bboxes)
    if person_nearby:
        state["last_person_nearby_at"] = now

    unattended_duration = now - state["last_person_nearby_at"]

    abandoned = (stationary_duration >= stationary_seconds) and (unattended_duration >= unattended_seconds)

    return {
        "abandoned": abandoned,
        "stationary_seconds": round(stationary_duration, 1),
        "unattended_seconds": round(unattended_duration, 1),
    }


def reset_track(track_id):
    """Call when an object track is lost, to avoid unbounded memory growth."""
    _object_state.pop(track_id, None)


# ---------------------------------------------------------------------------
# Test harness — two scenarios: genuinely abandoned vs. owner stays nearby
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import time as _t

    print("=== Scenario 1: bag placed, owner walks away and stays away ===")
    _object_state.clear()
    bag_bbox = (300, 300, 340, 340)  # stays perfectly still the whole time

    # Frame 0: owner is right next to the bag (just placed it)
    result = check_abandoned("bag_1", bag_bbox, person_bboxes=[(280, 280, 330, 400)])
    print(f"  t+0s (owner present):   {result}")

    _t.sleep(6)
    # Owner has now walked far away
    result = check_abandoned("bag_1", bag_bbox, person_bboxes=[(900, 900, 950, 1000)])
    print(f"  t+6s (owner far away):  {result}")

    _t.sleep(16)
    result = check_abandoned("bag_1", bag_bbox, person_bboxes=[(900, 900, 950, 1000)])
    print(f"  t+22s (still far away): {result}   <-- expect abandoned=True")

    print("\n=== Scenario 2: bag stationary, but owner never leaves ===")
    _object_state.clear()
    bag_bbox = (300, 300, 340, 340)

    result = check_abandoned("bag_2", bag_bbox, person_bboxes=[(280, 280, 330, 400)])
    print(f"  t+0s:  {result}")

    _t.sleep(6)
    # Owner stayed right next to the bag the whole time
    result = check_abandoned("bag_2", bag_bbox, person_bboxes=[(285, 285, 335, 405)])
    print(f"  t+6s:  {result}")

    _t.sleep(16)
    result = check_abandoned("bag_2", bag_bbox, person_bboxes=[(285, 285, 335, 405)])
    print(f"  t+22s: {result}   <-- expect abandoned=False (owner still nearby)")
