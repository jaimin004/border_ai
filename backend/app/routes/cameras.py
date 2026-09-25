"""Camera API routes."""
from fastapi import APIRouter
from app.database import fetch_all, fetch_one

router = APIRouter(prefix="/api/cameras", tags=["cameras"])


@router.get("")
def list_cameras():
    """Return all cameras with their status."""
    rows = fetch_all("""
        SELECT c.*,
               COUNT(e.id) FILTER (WHERE e.escalated = TRUE AND e.acknowledged = FALSE) AS active_alerts,
               MAX(e.timestamp) AS last_event_at
        FROM cameras c
        LEFT JOIN events e ON e.camera_id = c.id
        GROUP BY c.id
        ORDER BY c.id
    """)
    return rows


@router.get("/{camera_id}")
def get_camera(camera_id: str):
    """Return a single camera with recent events."""
    camera = fetch_one("SELECT * FROM cameras WHERE id = %s", (camera_id,))
    if not camera:
        return {"error": "Camera not found"}
    recent_events = fetch_all("""
        SELECT id, event_type, severity, risk_score, timestamp, description
        FROM events
        WHERE camera_id = %s
        ORDER BY timestamp DESC
        LIMIT 10
    """, (camera_id,))
    camera["recent_events"] = recent_events
    return camera
