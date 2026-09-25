"""
Database connection pool for the BORDER-AI backend.
Uses psycopg2 with a simple connection-per-request pattern.
"""
import os
import psycopg2
import psycopg2.extras

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "postgres"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "dbname": os.getenv("DB_NAME", "borderai"),
    "user": os.getenv("DB_USER", "borderai"),
    "password": os.getenv("DB_PASSWORD", "borderai_secret"),
}


def get_connection():
    """Return a new database connection."""
    return psycopg2.connect(**DB_CONFIG)


def fetch_all(query, params=None):
    """Execute a SELECT and return all rows as dicts."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
            return [dict(row) for row in rows]
    finally:
        conn.close()


def fetch_one(query, params=None):
    """Execute a SELECT and return a single row as dict."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params)
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        conn.close()


def execute(query, params=None):
    """Execute an INSERT/UPDATE/DELETE and commit."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
        conn.commit()
    finally:
        conn.close()
