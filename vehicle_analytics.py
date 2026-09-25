import time

# A virtual checkpoint line across the road, as two (x, y) points.
# Redraw to match wherever the actual checkpoint sits in your camera frame.
CHECKPOINT_LINE = [(0, 400), (1280, 400)]

AREA_CHANGE_THRESHOLD = 0.03  # min relative bbox-area change per step to call it approaching/departing

_vehicle_state = {}  # track_id -> {last_bbox, last_time, last_area, last_side}


def _bbox_area(bbox):
    x1, y1, x2, y2 = bbox
    return max(0, x2 - x1) * max(0, y2 - y1)


def _center(bbox):
    x1, y1, x2, y2 = bbox
    return ((x1 + x2) / 2, (y1 + y2) / 2)


def _line_side(point, line=CHECKPOINT_LINE):
    """Which side of the checkpoint line a point is on, via cross-product sign.
    Returns +1, -1, or 0 (exactly on the line)."""
    (x1, y1), (x2, y2) = line
    px, py = point
    cross = (x2 - x1) * (py - y1) - (y2 - y1) * (px - x1)
    if cross > 0:
        return 1
    elif cross < 0:
        return -1
    return 0


def track_vehicle_motion(track_id, bbox, line=CHECKPOINT_LINE):
    """Call once per frame per tracked vehicle.

    Returns:
      {
        "direction": "approaching" | "departing" | "steady" | "unknown",
        "speed_px_per_sec": float,   # UNCALIBRATED — relative pixels/sec, not km/h.
                                      # Only meaningful on live, real-time video;
                                      # see caveat in module docstring below.
        "crossed_checkpoint": None | "inbound" | "outbound",  # only set on the
                                      # exact frame the vehicle crosses the line
      }
    """
    now = time.time()
    center = _center(bbox)
    area = _bbox_area(bbox)
    side = _line_side(center, line)

    state = _vehicle_state.get(track_id)
    if state is None:
        _vehicle_state[track_id] = {
            "last_center": center, "last_time": now, "last_area": area, "last_side": side,
        }
        return {"direction": "unknown", "speed_px_per_sec": 0.0, "crossed_checkpoint": None}

    dt = max(now - state["last_time"], 1e-6)

    # Direction from bbox-area trend: a fixed forward-facing checkpoint camera
    # sees a vehicle's box grow as it approaches, shrink as it departs.
    area_change = (area - state["last_area"]) / max(state["last_area"], 1e-6)
    if area_change > AREA_CHANGE_THRESHOLD:
        direction = "approaching"
    elif area_change < -AREA_CHANGE_THRESHOLD:
        direction = "departing"
    else:
        direction = "steady"

    # Speed: relative pixel displacement per second. NOT a real-world speed
    # unless calibrated (pixels-per-meter for this specific camera/distance).
    dx = center[0] - state["last_center"][0]
    dy = center[1] - state["last_center"][1]
    speed_px_per_sec = ((dx ** 2 + dy ** 2) ** 0.5) / dt

    # Checkpoint crossing: only fires on the frame the side actually flips
    crossed = None
    if state["last_side"] != 0 and side != 0 and state["last_side"] != side:
        crossed = "inbound" if side > 0 else "outbound"

    _vehicle_state[track_id] = {
        "last_center": center, "last_time": now, "last_area": area, "last_side": side,
    }

    return {
        "direction": direction,
        "speed_px_per_sec": round(speed_px_per_sec, 1),
        "crossed_checkpoint": crossed,
    }


def reset_vehicle(track_id):
    _vehicle_state.pop(track_id, None)


# ---------------------------------------------------------------------------
# Test harness — a vehicle approaches, crosses the checkpoint, then departs
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import time as _t

    line = [(0, 400), (800, 400)]  # horizontal checkpoint line at y=400
    print("Checkpoint line:", line)
    print()

    # Vehicle starts above the line (side -1), growing bbox = approaching,
    # then crosses below the line (side +1), then shrinks = departing.
    frames = [
        (200, 100, 260, 150),   # far, above line, small box
        (190, 160, 270, 230),   # closer, still above, bigger box
        (180, 250, 280, 340),   # closer still, just above line
        (170, 380, 290, 460),   # now straddling / crossed below the line
        (160, 420, 300, 520),   # clearly below the line, moving away, shrinking next
        (165, 430, 290, 505),   # bbox shrinking = departing
    ]

    for i, bbox in enumerate(frames):
        result = track_vehicle_motion("veh_1", bbox, line=line)
        print(f"Frame {i}: bbox={bbox} -> {result}")
        _t.sleep(0.3)
