from datetime import datetime, timezone

from alert_engine import RISK_WEIGHTS, severity_band

# The report's own worked example uses exactly this weight for a correlated
# cross-camera event ("...+17 multi-event correlation"), so it's added here
# rather than invented fresh — keeps Day 3 and Day 4 consistent.
RISK_WEIGHTS["multi_camera_correlation"] = 17

CORRELATION_WINDOW_SECONDS = 90  # tune this after testing on real footage


def _parse_ts(timestamp_str):
    return datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def correlate(event_a, event_b, window_seconds=CORRELATION_WINDOW_SECONDS):
    """Time-window heuristic: two events from DIFFERENT cameras, close enough
    in time, are treated as plausibly the same person/vehicle moving between
    cameras. This is intentionally simple — no re-identification, no visual
    matching — just the correlation heuristic the schedule asked for."""
    if event_a["camera_id"] == event_b["camera_id"]:
        return False  # correlation is specifically about cross-camera links
    if event_a["object_class"] != event_b["object_class"]:
        return False  # a person event shouldn't correlate with a vehicle event

    delta = abs((_parse_ts(event_b["timestamp"]) - _parse_ts(event_a["timestamp"])).total_seconds())
    return delta <= window_seconds


def correlate_and_boost(new_event, recent_events, window_seconds=CORRELATION_WINDOW_SECONDS):
    """Checks new_event against a list of recent events (e.g. alert_engine.alert_queue).
    For every correlated match found, links both events' correlated_camera_ids
    and adds the multi_camera_correlation factor to new_event's score —
    recomputing its severity band if the boost pushes it into a new tier.
    Mutates new_event and any matched events in-place; returns new_event."""
    matched_any = False

    for existing in recent_events:
        if existing["id"] == new_event["id"]:
            continue
        if correlate(new_event, existing, window_seconds):
            matched_any = True
            if existing["camera_id"] not in new_event["correlated_camera_ids"]:
                new_event["correlated_camera_ids"].append(existing["camera_id"])
            if new_event["camera_id"] not in existing["correlated_camera_ids"]:
                existing["correlated_camera_ids"].append(new_event["camera_id"])

    if matched_any:
        points = RISK_WEIGHTS["multi_camera_correlation"]
        already_scored = any(b["factor"] == "multi_camera_correlation" for b in new_event["breakdown"])
        if not already_scored:
            new_event["breakdown"].append({"factor": "multi_camera_correlation", "points": points})
            new_event["risk_score"] = min(new_event["risk_score"] + points, 100)
            new_event["severity"] = severity_band(new_event["risk_score"])
            new_event["escalated"] = True  # a correlated event always escalates,
            # since "seen at two cameras close in time" is significant regardless
            # of what its standalone score was

    return new_event


# ---------------------------------------------------------------------------
# Test harness — fake cross-camera timestamp pairs
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    from alert_engine import generate_alert, alert_queue

    # Event 1: person seen at Camera A, moderate risk on its own
    event_1 = generate_alert(
        camera_id="cam_A", track_id="trk_001", object_class="person",
        event_type="zone_intrusion",
        factors={"person_detected": True, "restricted_zone_entry": True},
    )
    print("Event 1 (Camera A):", event_1["risk_score"], event_1["severity"])

    # Event 2: same class, DIFFERENT camera, 45 seconds later -> should correlate
    event_2 = generate_alert(
        camera_id="cam_B", track_id="trk_002", object_class="person",
        event_type="zone_intrusion",
        factors={"person_detected": True},
    )
    print("Event 2 (Camera B) before correlation:", event_2["risk_score"], event_2["severity"])

    event_2 = correlate_and_boost(event_2, [event_1])
    print("Event 2 (Camera B) after correlation:", event_2["risk_score"], event_2["severity"])
    print("Event 2 breakdown:", event_2["breakdown"])
    print("Event 2 correlated_camera_ids:", event_2["correlated_camera_ids"])
    print("Event 1 correlated_camera_ids (should now include cam_B):", event_1["correlated_camera_ids"])

    print()

    # Event 3: same camera as event 1 -> should NOT correlate (same-camera rule)
    event_3 = generate_alert(
        camera_id="cam_A", track_id="trk_003", object_class="person",
        event_type="zone_intrusion", factors={"person_detected": True},
    )
    event_3 = correlate_and_boost(event_3, [event_1])
    print("Event 3 (same camera as Event 1) correlated_camera_ids (should be empty):",
          event_3["correlated_camera_ids"])
