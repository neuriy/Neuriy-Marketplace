from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
ICON_DIR = BASE_DIR / "static" / "icons"
LOCAL_DB_PATH = BASE_DIR / "data" / "neuriy.db"

# Provided Turso database (libSQL remote)
DEFAULT_TURSO_URL = "libsql://neuriymp-ericksonholding.aws-eu-west-1.turso.io"

TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL", DEFAULT_TURSO_URL).strip()
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN", "").strip()
JWT_SECRET = os.getenv("JWT_SECRET", "neuriy-dev-secret-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "72"))

# System AI moderation threshold (0-100). Below this → blacklisted.
AI_QUALITY_THRESHOLD = float(os.getenv("AI_QUALITY_THRESHOLD", "55"))

ROLES = ("user", "admin", "administrator")
APP_STATUSES = ("pending", "approved", "blacklisted")

CATEGORIES = [
    "All Categories",
    "Assistants",
    "Productivity",
    "Creative",
    "Developer Tools",
    "Research",
    "Education",
    "Utilities",
]


def using_turso() -> bool:
    return bool(TURSO_AUTH_TOKEN) and TURSO_DATABASE_URL.startswith(("libsql://", "https://"))


def get_connection():
    """Return a DB-API connection to Turso (preferred) or local SQLite fallback."""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    ICON_DIR.mkdir(parents=True, exist_ok=True)
    LOCAL_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    if using_turso():
        import libsql

        return libsql.connect(database=TURSO_DATABASE_URL, auth_token=TURSO_AUTH_TOKEN)

    import sqlite3

    conn = sqlite3.connect(str(LOCAL_DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def rows_as_dicts(cursor) -> list[dict[str, Any]]:
    rows = cursor.fetchall()
    if not rows:
        return []
    if isinstance(rows[0], dict):
        return list(rows)
    # sqlite3.Row or tuple
    try:
        return [dict(row) for row in rows]
    except Exception:
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in rows]


def execute(conn, sql: str, params: Optional[tuple | list] = None):
    if params is None:
        return conn.execute(sql)
    return conn.execute(sql, params)
