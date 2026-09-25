"""Analytics endpoints — time-series data for charts."""
from fastapi import APIRouter, Query
from app.database import fetch_all

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/timeline")
def events_timeline(hours: int = Query(24, ge=1, le=168)):
    """Event counts per hour for the last N hours."""
    rows = fetch_all("""
        SELECT
            TO_CHAR(date_trunc('hour', timestamp), 'HH24:00') AS period,
            COUNT(*)::int AS count
        FROM events
        WHERE timestamp >= NOW() - MAKE_INTERVAL(hours => %s)
        GROUP BY date_trunc('hour', timestamp)
        ORDER BY date_trunc('hour', timestamp)
    """, (hours,))
    return rows


@router.get("/severity-distribution")
def severity_distribution():
    """Event counts by severity."""
    rows = fetch_all("""
        SELECT severity, COUNT(*)::int AS count
        FROM events
        GROUP BY severity
        ORDER BY
            CASE severity
                WHEN 'critical' THEN 1
                WHEN 'high' THEN 2
                WHEN 'medium' THEN 3
                WHEN 'low' THEN 4
            END
    """)
    return rows


@router.get("/camera-activity")
def camera_activity():
    """Event counts per camera."""
    rows = fetch_all("""
        SELECT c.id, c.name, COUNT(e.id)::int AS event_count,
               COUNT(e.id) FILTER (WHERE e.escalated = TRUE AND e.acknowledged = FALSE)::int AS active_alerts
        FROM cameras c
        LEFT JOIN events e ON e.camera_id = c.id
        GROUP BY c.id, c.name
        ORDER BY event_count DESC
    """)
    return rows


@router.get("/event-types")
def event_type_distribution():
    """Event counts by type."""
    rows = fetch_all("""
        SELECT event_type, COUNT(*)::int AS count
        FROM events
        GROUP BY event_type
        ORDER BY count DESC
    """)
    return rows


@router.get("/risk-distribution")
def risk_distribution():
    """Risk score distribution in buckets."""
    rows = fetch_all("""
        SELECT
            CASE
                WHEN risk_score <= 20 THEN '0-20'
                WHEN risk_score <= 40 THEN '21-40'
                WHEN risk_score <= 60 THEN '41-60'
                WHEN risk_score <= 80 THEN '61-80'
                ELSE '81-100'
            END AS bucket,
            COUNT(*)::int AS count
        FROM events
        GROUP BY bucket
        ORDER BY bucket
    """)
    return rows
