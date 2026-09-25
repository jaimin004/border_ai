import time

# Operator-defined restricted zone(s) as pixel-coordinate polygons.
# Redraw these to match your actual camera frame / demo footage.
ZONES = {
    "restricted_1": [(419, 90), (636, 163), (637, 257), (419, 160)],
}

LOITER_SECONDS = 2  # dwell time inside a zone before it counts as loitering
BOUNDARY_APPROACH_HISTORY = 5  # frames of recent distance to judge "moving toward"

# Per-track state, keyed by track_id. Kept in memory — fine for a single
# demo run; would move to Redis/DB for a real multi-camera deployment.
_track_state = {}


def _point_in_polygon(point, polygon):
    """Standard ray-casting point-in-polygon test."""
    x, y = point
    n = len(polygon)
    inside = False
    px1, py1 = polygon[0]
    for i in range(1, n + 1):
        px2, py2 = polygon[i % n]
        if y > min(py1, py2) and y <= max(py1, py2) and x <= max(px1, px2):
            if py1 != py2:
                x_intersect = (y - py1) * (px2 - px1) / (py2 - py1) + px1
            else:
                x_intersect = px1
            if px1 == px2 or x <= x_intersect:
                inside = not inside
        px1, py1 = px2, py2
    return inside


def _center(bbox):
    x1, y1, x2, y2 = bbox
    return ((x1 + x2) / 2, (y1 + y2) / 2)


def _distance_to_polygon_edge(point, polygon):
    """Rough min distance from point to any polygon edge — used only to
    judge whether a track is trending closer to the boundary over time,
    not for precise geometry."""
    px, py = point
    min_dist = float("inf")
    n = len(polygon)
    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]
        edge_len_sq = (x2 - x1) ** 2 + (y2 - y1) ** 2
        if edge_len_sq == 0:
            dist = ((px - x1) ** 2 + (py - y1) ** 2) ** 0.5
        else:
            t = max(0, min(1, ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / edge_len_sq))
            proj_x, proj_y = x1 + t * (x2 - x1), y1 + t * (y2 - y1)
            dist = ((px - proj_x) ** 2 + (py - proj_y) ** 2) ** 0.5
        min_dist = min(min_dist, dist)
    return min_dist


def check_zone_and_loiter(track_id, bbox, zones=ZONES, loiter_seconds=LOITER_SECONDS):
    """Call once per frame per tracked person. Returns a factors dict
    matching alert_engine's expected keys:
      restricted_zone_entry, loitering, movement_toward_boundary
    Maintains dwell-time and recent-position history per track_id internally."""
    center = _center(bbox)
    now = time.time()

    state = _track_state.setdefault(track_id, {
        "zone_entered_at": None,
        "in_zone": False,
        "distance_history": [],
    })

    in_any_zone = False
    nearest_zone_distance = float("inf")

    for zone_name, polygon in zones.items():
        if _point_in_polygon(center, polygon):
            in_any_zone = True
        nearest_zone_distance = min(nearest_zone_distance, _distance_to_polygon_edge(center, polygon))

    # Loitering: track dwell time continuously inside a zone
    if in_any_zone:
        if not state["in_zone"]:
            state["zone_entered_at"] = now
        state["in_zone"] = True
    else:
        state["in_zone"] = False
        state["zone_entered_at"] = None

    dwell_time = (now - state["zone_entered_at"]) if state["zone_entered_at"] else 0
    loitering = dwell_time >= loiter_seconds

    # Movement toward boundary: is distance-to-nearest-zone-edge trending
    # DOWN over recent frames? Simple heuristic, not true velocity/heading.
    state["distance_history"].append(nearest_zone_distance)
    state["distance_history"] = state["distance_history"][-BOUNDARY_APPROACH_HISTORY:]
    movement_toward_boundary = False
    if len(state["distance_history"]) >= 3 and not in_any_zone:
        movement_toward_boundary = state["distance_history"][-1] < state["distance_history"][0]

    return {
        "restricted_zone_entry": in_any_zone,
        "loitering": loitering,
        "movement_toward_boundary": movement_toward_boundary,
    }


def reset_track(track_id):
    """Call when a track is lost/expired, to avoid unbounded memory growth
    over a long-running video feed."""
    _track_state.pop(track_id, None)


# ---------------------------------------------------------------------------
# Test harness — simulate a track walking toward and into the zone
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("Zone:", ZONES["restricted_1"])
    print()

    # Simulate a person walking from outside, toward, then into the zone
    positions = [
        (50, 250, 90, 350),    # far outside
        (80, 250, 120, 350),   # getting closer
        (120, 250, 160, 350),  # closer still
        (170, 250, 210, 350),  # now inside the zone
    ]

    for i, bbox in enumerate(positions):
        factors = check_zone_and_loiter("trk_test", bbox)
        print(f"Frame {i}: bbox={bbox} -> {factors}")

    print("\nSimulating loitering (same in-zone position held over time)...")
    import time as _t
    _track_state.clear()
    bbox = (170, 250, 210, 350)
    for i in range(3):
        factors = check_zone_and_loiter("trk_loiter", bbox)
        print(f"  t+{i*4}s: {factors}")
        _t.sleep(4)
