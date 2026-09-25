"""
BORDER-AI — FastAPI Backend
Edge-Intelligent Video Analytics & Event Intelligence Platform API.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import cameras, events, alerts, stats, analytics

app = FastAPI(
    title="BORDER-AI API",
    description="REST API for the BORDER-AI surveillance intelligence platform",
    version="1.0.0",
)

# Allow the React frontend (Vite dev server) to talk to this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register route modules
app.include_router(cameras.router)
app.include_router(events.router)
app.include_router(alerts.router)
app.include_router(stats.router)
app.include_router(analytics.router)


@app.get("/")
def root():
    return {
        "name": "BORDER-AI API",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    """Health check for Docker / orchestration."""
    from app.database import fetch_one
    try:
        row = fetch_one("SELECT 1 AS ok")
        db_ok = row is not None
    except Exception:
        db_ok = False

    return {
        "api": True,
        "database": db_ok,
    }
