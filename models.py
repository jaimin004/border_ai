"""
Pydantic models / schemas for the BORDER-AI API responses.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class CameraOut(BaseModel):
    id: str
    name: str
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    status: str = "online"
    stream_url: Optional[str] = None
    zone_type: Optional[str] = None
    created_at: Optional[datetime] = None


class BreakdownItem(BaseModel):
    factor: str
    points: int


class FaceMatch(BaseModel):
    matched: bool = False
    confidence: float = 0.0
    name: Optional[str] = None


class EventOut(BaseModel):
    id: str
    camera_id: str
    camera_name: Optional[str] = None
    track_id: Optional[str] = None
    object_class: Optional[str] = None
    event_type: Optional[str] = None
    timestamp: Optional[datetime] = None
    risk_score: int = 0
    severity: Optional[str] = None
    breakdown: Any = []
    snapshot_path: Optional[str] = None
    face_match: Any = None
    plate_text: Optional[str] = None
    plate_confidence: Optional[float] = None
    correlated_camera_ids: Optional[list] = []
    synced: bool = True
    escalated: bool = False
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    description: Optional[str] = None
    created_at: Optional[datetime] = None


class StatsOut(BaseModel):
    total_events: int = 0
    active_alerts: int = 0
    cameras_online: int = 0
    cameras_total: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    avg_risk_score: float = 0.0


class AcknowledgeRequest(BaseModel):
    acknowledged_by: str = "operator"


class EventCreate(BaseModel):
    """Request body for POST /api/events — what the live AI pipeline sends."""
    id: str
    camera_id: str
    track_id: Optional[str] = None
    object_class: Optional[str] = None
    event_type: Optional[str] = None
    timestamp: datetime
    risk_score: int = 0
    severity: Optional[str] = None
    breakdown: list = []
    snapshot_path: Optional[str] = None
    face_match: Optional[dict] = None
    plate_text: Optional[str] = None
    plate_confidence: Optional[float] = None
    correlated_camera_ids: Optional[list] = []
    synced: bool = True
    escalated: bool = False
    description: Optional[str] = None


class TimeSeriesPoint(BaseModel):
    period: str
    count: int
    severity: Optional[str] = None
