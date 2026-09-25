"""Alert API routes — active (escalated, unacknowledged) alerts."""
from fastapi import APIRouter
from app.database import fetch_all, execute
from app.models import AcknowledgeRequest

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("")
def list_alerts():
    """Return all escalated, unacknowledged alerts (Medium+ severity)."""
    rows = fetch_all("""
        SELECT e.*, c.name AS camera_name
        FROM events e
        LEFT JOIN cameras c ON c.id = e.camera_id
        WHERE e.escalated = TRUE AND e.acknowledged = FALSE
        ORDER BY e.risk_score DESC, e.timestamp DESC
    """)
    return rows


@router.get("/all")
def list_all_alerts():
    """Return ALL escalated alerts, including acknowledged ones."""
    rows = fetch_all("""
        SELECT e.*, c.name AS camera_name
        FROM events e
        LEFT JOIN cameras c ON c.id = e.camera_id
        WHERE e.escalated = TRUE
        ORDER BY e.timestamp DESC
    """)
    return rows


@router.post("/{event_id}/acknowledge")
def acknowledge_alert(event_id: str, body: AcknowledgeRequest):
    """Mark an alert as acknowledged by an operator."""
    execute("""
        UPDATE events
        SET acknowledged = TRUE,
            acknowledged_by = %s,
            acknowledged_at = NOW()
        WHERE id = %s
    """, (body.acknowledged_by, event_id))
    return {"status": "acknowledged", "event_id": event_id}
