import json
import sqlite3
from typing import Any, Dict, List, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

DB_PATH = "events.db"

app = FastAPI(title="BORDER-AI Events API")

# Allow the React dashboard (running on a different port) to call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # fine for a hackathon demo; tighten for anything real
    allow_methods=["*"],
    allow_headers=["*"],
)


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, data TEXT)")
    conn.commit()
    conn.close()


init_db()


@app.post("/events")
def create_event(event: Dict[str, Any]):
    """Stores an event (upserts by id, so a correlation update to an
    already-stored event overwrites cleanly instead of duplicating)."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT OR REPLACE INTO events (id, data) VALUES (?, ?)",
        (event["id"], json.dumps(event)),
    )
    conn.commit()
    conn.close()
    return {"status": "stored", "id": event["id"]}


@app.get("/events")
def list_events(camera_id: Optional[str] = None, min_severity: Optional[str] = None) -> List[Dict[str, Any]]:
    """Basic filtering via query params, e.g. GET /events?camera_id=cam_01
    For anything more expressive, the dashboard/NL-search module applies
    nl_search.py's filters client-side on top of this raw list."""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT data FROM events").fetchall()
    conn.close()

    events = [json.loads(r[0]) for r in rows]

    if camera_id:
        events = [e for e in events if e.get("camera_id") == camera_id]
    if min_severity:
        order = ["low", "medium", "high", "critical"]
        min_idx = order.index(min_severity)
        events = [e for e in events if order.index(e.get("severity", "low")) >= min_idx]

    return events


@app.get("/health")
def health():
    return {"status": "ok"}
