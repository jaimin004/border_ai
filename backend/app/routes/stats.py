"""Dashboard stats / KPI endpoint."""
from fastapi import APIRouter
from app.database import fetch_one

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("")
def get_stats():
    """Return aggregate KPI stats for the dashboard."""
    row = fetch_one("""
        SELECT
            COUNT(*)::int AS total_events,
            COUNT(*) FILTER (WHERE escalated = TRUE AND acknowledged = FALSE)::int AS active_alerts,
            COUNT(*) FILTER (WHERE severity = 'critical')::int AS critical_count,
            COUNT(*) FILTER (WHERE severity = 'high')::int AS high_count,
            COUNT(*) FILTER (WHERE severity = 'medium')::int AS medium_count,
            COUNT(*) FILTER (WHERE severity = 'low')::int AS low_count,
            COALESCE(ROUND(AVG(risk_score)::numeric, 1), 0)::float AS avg_risk_score
        FROM events
    """)

    cameras = fetch_one("""
        SELECT
            COUNT(*)::int AS cameras_total,
            COUNT(*) FILTER (WHERE status = 'online')::int AS cameras_online
        FROM cameras
    """)

    return {**row, **cameras}
