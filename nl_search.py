import re
from datetime import datetime, timedelta, timezone

SEVERITY_ORDER = ["low", "medium", "high", "critical"]

EVENT_TYPE_KEYWORDS = {
    "intrusion": "zone_intrusion",
    "zone intrusion": "zone_intrusion",
    "loiter": "loitering",
    "loitering": "loitering",
    "abandoned": "abandoned_object",
    "abandoned object": "abandoned_object",
    "vehicle": "vehicle_anomaly",
}

SEVERITY_KEYWORDS = {
    "critical": "critical",
    "high risk": "high",
    "high-risk": "high",
    "high": "high",
    "medium": "medium",
    "low risk": "low",
    "low": "low",
}


def parse_query(query_text):
    """Turns a natural-language question into a structured filter dict.
    This is deliberately simple keyword matching, not a full LLM call —
    per the report's own guidance (Section 25): the assistant translates
    questions into CONTROLLED queries against structured event data, it
    never has free-form access to the system. A real deployment could
    swap this parser for an LLM call that outputs the same filter shape;
    the rest of the pipeline wouldn't need to change."""
    q = query_text.lower()
    filters = {
        "camera_id": None,
        "event_type": None,
        "min_severity": None,
        "since": None,
    }

    # Camera: "camera 3", "cam 3", "cam_03" -> cam_03
    cam_match = re.search(r"cam(?:era)?[\s_]*0*(\d+)", q)
    if cam_match:
        filters["camera_id"] = f"cam_{int(cam_match.group(1)):02d}"

    # Event type
    for phrase, event_type in EVENT_TYPE_KEYWORDS.items():
        if phrase in q:
            filters["event_type"] = event_type
            break

    # Severity (checked as a MINIMUM bar, e.g. "high risk" -> high or critical)
    for phrase, severity in SEVERITY_KEYWORDS.items():
        if phrase in q:
            filters["min_severity"] = severity
            break

    # Time range — simple, common phrasings
    now = datetime.now(timezone.utc)
    if "today" in q:
        filters["since"] = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif "last hour" in q or "past hour" in q:
        filters["since"] = now - timedelta(hours=1)
    elif "last 2 hours" in q or "past 2 hours" in q or "last two hours" in q:
        filters["since"] = now - timedelta(hours=2)
    elif "yesterday" in q:
        filters["since"] = now - timedelta(days=1)

    return filters


def apply_filters(events, filters):
    def matches(event):
        if filters["camera_id"] and event["camera_id"] != filters["camera_id"]:
            return False
        if filters["event_type"] and event["event_type"] != filters["event_type"]:
            return False
        if filters["min_severity"]:
            min_idx = SEVERITY_ORDER.index(filters["min_severity"])
            event_idx = SEVERITY_ORDER.index(event["severity"])
            if event_idx < min_idx:
                return False
        if filters["since"]:
            event_time = datetime.strptime(event["timestamp"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            if event_time < filters["since"]:
                return False
        return True

    return [e for e in events if matches(e)]


def search(query_text, events):
    """One call: parse the query, apply it, return matching events plus the
    filter that was actually used — useful for showing the operator
    'here's what I searched for' rather than a black-box result list."""
    filters = parse_query(query_text)
    results = apply_filters(events, filters)
    return results, filters


# ---------------------------------------------------------------------------
# Test harness — mock event data, several queries, sanity-checked results
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    now = datetime.now(timezone.utc)

    def ts(hours_ago):
        return (now - timedelta(hours=hours_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")

    mock_events = [
        {"id": "evt_1", "camera_id": "cam_01", "event_type": "zone_intrusion", "severity": "high", "timestamp": ts(0.2)},
        {"id": "evt_2", "camera_id": "cam_03", "event_type": "zone_intrusion", "severity": "medium", "timestamp": ts(0.5)},
        {"id": "evt_3", "camera_id": "cam_02", "event_type": "loitering", "severity": "low", "timestamp": ts(3)},
        {"id": "evt_4", "camera_id": "cam_03", "event_type": "abandoned_object", "severity": "critical", "timestamp": ts(1.5)},
        {"id": "evt_5", "camera_id": "cam_01", "event_type": "zone_intrusion", "severity": "critical", "timestamp": ts(30)},  # yesterday-ish
    ]

    queries = [
        "Show all intrusion events from Camera 3 today",
        "Show high-risk events from the last two hours",
        "What happened on camera 1?",
        "Any critical events?",
    ]

    for q in queries:
        results, filters = search(q, mock_events)
        print(f'Query: "{q}"')
        print(f"  Parsed filters: {filters}")
        print(f"  Matched: {[e['id'] for e in results]}")
        print()
