"""Event API routes."""
from typing import Optional
from fastapi import APIRouter, Query
from app.database import fetch_all, fetch_one

router = APIRouter(prefix="/api/events", tags=["events"])


@router.get("")
def list_events(
    severity: Optional[str] = Query(None, description="Filter by severity"),
    camera_id: Optional[str] = Query(None, description="Filter by camera"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    object_class: Optional[str] = Query(None, description="Filter by object class"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Return events with optional filters, newest first."""
    conditions = []
    params = []

    if severity:
        conditions.append("e.severity = %s")
        params.append(severity)
    if camera_id:
        conditions.append("e.camera_id = %s")
        params.append(camera_id)
    if event_type:
        conditions.append("e.event_type = %s")
        params.append(event_type)
    if object_class:
        conditions.append("e.object_class = %s")
        params.append(object_class)

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    params.extend([limit, offset])

    rows = fetch_all(f"""
        SELECT e.*, c.name AS camera_name
        FROM events e
        LEFT JOIN cameras c ON c.id = e.camera_id
        {where_clause}
        ORDER BY e.timestamp DESC
        LIMIT %s OFFSET %s
    """, params)

    # Get total count for pagination
    count_row = fetch_one(f"""
        SELECT COUNT(*) AS total FROM events e {where_clause}
    """, params[:-2] if params[:-2] else None)

    return {
        "events": rows,
        "total": count_row["total"] if count_row else 0,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{event_id}")
def get_event(event_id: str):
    """Return full event detail including camera info."""
    event = fetch_one("""
        SELECT e.*, c.name AS camera_name, c.location AS camera_location,
               c.latitude, c.longitude, c.zone_type
        FROM events e
        LEFT JOIN cameras c ON c.id = e.camera_id
        WHERE e.id = %s
    """, (event_id,))
    if not event:
        return {"error": "Event not found"}
    return event
