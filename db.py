"""SQLite persistence for solo dining recommendation history."""

import json
import sqlite3
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DB_DIR = Path(__file__).resolve().parent / "data"
DB_PATH = DB_DIR / "solo_dining.db"

# Schema matches ARCHITECTURE.md (recommendations table).
INIT_SQL = """
CREATE TABLE IF NOT EXISTS recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TIMESTAMP NOT NULL DEFAULT (datetime('now')),
    budget TEXT,
    mood TEXT,
    portion_pref TEXT,
    location TEXT,
    results TEXT
);
"""


def get_db_path() -> Path:
    return DB_PATH


def _migrate_db(conn: sqlite3.Connection) -> None:
    """Add columns introduced after initial schema without dropping existing data."""
    existing = {row[1] for row in conn.execute("PRAGMA table_info(recommendations)")}
    if "dietary_restrictions" not in existing:
        conn.execute(
            "ALTER TABLE recommendations ADD COLUMN dietary_restrictions TEXT DEFAULT '[]'"
        )
    if "rating" not in existing:
        conn.execute(
            "ALTER TABLE recommendations ADD COLUMN rating INTEGER DEFAULT NULL"
        )
    conn.commit()


def init_db() -> None:
    """Create data directory and recommendations table if missing."""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(INIT_SQL)
        _migrate_db(conn)
        conn.commit()


def get_connection() -> sqlite3.Connection:
    """Return a new connection (caller should use as context manager or close)."""
    init_db()
    return sqlite3.connect(DB_PATH)


def save_recommendation(
    *,
    budget: str,
    mood: str,
    portion_pref: str,
    location: str | None,
    results: list[Any],
    dietary_restrictions: tuple[str, ...] | list[str] = (),
) -> int:
    """Insert one query/response record and return inserted row id."""
    init_db()
    normalized: list[Any] = []
    for item in results:
        if is_dataclass(item):
            normalized.append(asdict(item))
        else:
            normalized.append(item)

    created_at = datetime.now(timezone.utc).isoformat()
    results_json = json.dumps(normalized, ensure_ascii=False)
    dr_json = json.dumps(list(dietary_restrictions), ensure_ascii=False)

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            """
            INSERT INTO recommendations
            (created_at, budget, mood, portion_pref, location, results, dietary_restrictions)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (created_at, budget, mood, portion_pref, location, results_json, dr_json),
        )
        conn.commit()
        return int(cursor.lastrowid)


def update_rating(row_id: int, rating: int) -> None:
    """Persist a thumbs-up (1) or thumbs-down (-1) for a saved search."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "UPDATE recommendations SET rating = ? WHERE id = ?", (rating, row_id)
        )
        conn.commit()


def fetch_recommendation_history() -> list[dict[str, Any]]:
    """Return all history rows in reverse chronological order."""
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT id, created_at, budget, mood, portion_pref, location, results,
                   dietary_restrictions, rating
            FROM recommendations
            ORDER BY datetime(created_at) DESC, id DESC
            """
        ).fetchall()

    history: list[dict[str, Any]] = []
    for row in rows:
        raw_results = row["results"] or "[]"
        try:
            parsed_results = json.loads(raw_results)
        except json.JSONDecodeError:
            parsed_results = []

        try:
            parsed_dr = json.loads(row["dietary_restrictions"] or "[]")
        except json.JSONDecodeError:
            parsed_dr = []

        history.append(
            {
                "id": row["id"],
                "created_at": row["created_at"],
                "budget": row["budget"],
                "mood": row["mood"],
                "portion_pref": row["portion_pref"],
                "location": row["location"],
                "results": parsed_results,
                "dietary_restrictions": parsed_dr,
                "rating": row["rating"],
            }
        )
    return history
