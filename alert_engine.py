import uuid
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Risk scoring — exact factor weights from the report's Section 7.11 table.
# Additive and explainable: every point is traceable to a named cause,
# never a single opaque number.
# ---------------------------------------------------------------------------
RISK_WEIGHTS = {
    "person_detected": 5,
    "restricted_zone_entry": 30,
    "loitering": 20,
    "movement_toward_boundary": 20,
    "multi_person_coordination": 15,
    "abandoned_object": 30,
}

# Only escalate to an actual alert at Medium or above — avoids spamming the
# dashboard with every single "person detected" (+5) non-event.
ESCALATION_MIN_SEVERITY = "medium"
SEVERITY_ORDER = ["low", "medium", "high", "critical"]


def compute_risk_score(factors):
    """factors: dict of {factor_name: bool}, e.g. {"restricted_zone_entry": True, "loitering": True}
    Returns (score, breakdown) where breakdown is a list of {"factor", "points"} —
    only the factors that actually fired, for the explainable-alert display."""
    breakdown = []
    score = 0
    for factor, active in factors.items():
        if not active:
            continue
        points = RISK_WEIGHTS.get(factor)
        if points is None:
            continue  # unknown factor name — ignore rather than silently miscount
        score += points
        breakdown.append({"factor": factor, "points": points})

    score = min(score, 100)  # cap at 100 to match the report's severity bands
    return score, breakdown


def severity_band(score):
    if score <= 30:
        return "low"
    elif score <= 60:
        return "medium"
    elif score <= 80:
        return "high"
    else:
        return "critical"


def should_escalate(severity):
    return SEVERITY_ORDER.index(severity) >= SEVERITY_ORDER.index(ESCALATION_MIN_SEVERITY)


# ---------------------------------------------------------------------------
# Alert generation — builds a full event matching event_schema.json.
# Stands in for the real POST /events call until Day 5 wires up the backend;
# for now, escalated alerts just get appended to an in-memory list.
# ---------------------------------------------------------------------------
alert_queue = []  # in-memory stand-in for the FastAPI /events endpoint


def generate_alert(camera_id, track_id, object_class, event_type, factors,
                    snapshot_path=None, face_match=None, plate_confidence=None):
    """Computes risk, decides whether to escalate, and if so appends a full
    event dict (matching event_schema.json) to alert_queue.
    Returns the event dict either way, with an extra 'escalated' flag,
    so callers can log/inspect low-severity events without them hitting
    the dashboard."""
    score, breakdown = compute_risk_score(factors)
    severity = severity_band(score)
    escalated = should_escalate(severity)

    event = {
        "id": f"evt_{uuid.uuid4().hex[:8]}",
        "camera_id": camera_id,
        "track_id": track_id,
        "object_class": object_class,
        "event_type": event_type,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "risk_score": score,
        "severity": severity,
        "breakdown": breakdown,
        "snapshot_path": snapshot_path,
        "face_match": face_match or {"matched": False, "confidence": 0.0},
        "plate_confidence": plate_confidence,
        "correlated_camera_ids": [],  # filled in once Day 4's correlation module exists
        "synced": True,  # flipped to False once Day 6's offline mode exists
        "escalated": escalated,
    }

    if escalated:
        alert_queue.append(event)

    return event


# ---------------------------------------------------------------------------
# Test harness — fake scenarios covering every severity band, to prove the
# Medium+ threshold actually works before this touches real pipeline data.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    scenarios = [
        # (label, factors)
        ("Person just walking by", {"person_detected": True}),
        ("Zone entry only", {"person_detected": True, "restricted_zone_entry": True}),
        ("Zone entry + loitering", {
            "person_detected": True, "restricted_zone_entry": True, "loitering": True,
        }),
        ("Full high-risk sequence", {
            "person_detected": True, "restricted_zone_entry": True, "loitering": True,
            "movement_toward_boundary": True, "multi_person_coordination": True,
        }),
        ("Abandoned object alone", {"abandoned_object": True}),
    ]

    for label, factors in scenarios:
        event = generate_alert(
            camera_id="cam_01",
            track_id=f"trk_{uuid.uuid4().hex[:4]}",
            object_class="person",
            event_type="zone_intrusion",
            factors=factors,
            snapshot_path="/evidence/test.jpg",
        )
        status = "ESCALATED -> alert_queue" if event["escalated"] else "logged only, not escalated"
        print(f"[{label}]")
        print(f"  Score: {event['risk_score']}  Severity: {event['severity']}  ({status})")
        print(f"  Breakdown: {event['breakdown']}")
        print()

    print(f"Total events in alert_queue (Medium+): {len(alert_queue)}")
