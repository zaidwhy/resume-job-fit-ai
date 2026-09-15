"""SQLite persistence layer for the job application tracker.

Stores one row per saved analysis. UI-agnostic - no Streamlit imports.
Database file: job_tracker.db in the project root (git-ignored).
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Generator, Optional

DB_PATH = Path(__file__).parent / "job_tracker.db"

STATUSES = ["Saved", "Applied", "Interviewing", "Offer", "Rejected"]


@contextmanager
def _conn() -> Generator[sqlite3.Connection, None, None]:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db() -> None:
    """Create the applications table if it doesn't exist, and add the owner column to
    databases created before rows were scoped per visitor."""
    with _conn() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                owner     TEXT    NOT NULL DEFAULT '',
                job_title TEXT    NOT NULL,
                company   TEXT    NOT NULL DEFAULT '',
                score     INTEGER NOT NULL,
                status    TEXT    NOT NULL DEFAULT 'Saved',
                notes     TEXT    NOT NULL DEFAULT '',
                saved_on  TEXT    NOT NULL
            )
        """)
        columns = {row["name"] for row in con.execute("PRAGMA table_info(applications)")}
        if "owner" not in columns:
            con.execute("ALTER TABLE applications ADD COLUMN owner TEXT NOT NULL DEFAULT ''")
        con.execute("CREATE INDEX IF NOT EXISTS idx_applications_owner ON applications(owner)")


def save_application(
    owner: str,
    job_title: str,
    score: int,
    company: str = "",
    notes: str = "",
) -> int:
    """Insert a new application row for `owner` (the visitor's session id). Returns the new row id."""
    init_db()
    with _conn() as con:
        cur = con.execute(
            "INSERT INTO applications (owner, job_title, company, score, status, notes, saved_on) "
            "VALUES (?, ?, ?, ?, 'Saved', ?, ?)",
            (owner, job_title.strip(), company.strip(), score, notes.strip(), date.today().isoformat()),
        )
        return cur.lastrowid  # type: ignore[return-value]


def update_status(owner: str, row_id: int, status: str) -> None:
    """Update the status of one of `owner`'s applications. Other owners' rows are untouched."""
    init_db()
    if status not in STATUSES:
        raise ValueError(f"status must be one of {STATUSES}")
    with _conn() as con:
        con.execute(
            "UPDATE applications SET status = ? WHERE id = ? AND owner = ?", (status, row_id, owner)
        )


def update_notes(owner: str, row_id: int, notes: str) -> None:
    """Update the notes field of one of `owner`'s applications."""
    init_db()
    with _conn() as con:
        con.execute(
            "UPDATE applications SET notes = ? WHERE id = ? AND owner = ?", (notes.strip(), row_id, owner)
        )


def delete_application(owner: str, row_id: int) -> None:
    """Delete one of `owner`'s applications by id."""
    init_db()
    with _conn() as con:
        con.execute("DELETE FROM applications WHERE id = ? AND owner = ?", (row_id, owner))


def get_all_applications(owner: str) -> list[dict]:
    """Return `owner`'s applications newest-first as a list of dicts."""
    init_db()
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM applications WHERE owner = ? ORDER BY id DESC", (owner,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_stats(owner: str) -> dict:
    """Return summary stats for `owner`: total, avg_score, status_counts."""
    init_db()
    with _conn() as con:
        total = con.execute("SELECT COUNT(*) FROM applications WHERE owner = ?", (owner,)).fetchone()[0]
        avg = con.execute("SELECT AVG(score) FROM applications WHERE owner = ?", (owner,)).fetchone()[0]
        rows = con.execute(
            "SELECT status, COUNT(*) as cnt FROM applications WHERE owner = ? GROUP BY status", (owner,)
        ).fetchall()
    return {
        "total": total,
        "avg_score": round(avg, 1) if avg else 0,
        "by_status": {r["status"]: r["cnt"] for r in rows},
    }


def get_score_history(owner: str) -> list[dict]:
    """Return `owner`'s saved_on/score/job_title ordered oldest-first for the trend chart."""
    init_db()
    with _conn() as con:
        rows = con.execute(
            "SELECT saved_on, score, job_title FROM applications WHERE owner = ? ORDER BY id ASC",
            (owner,),
        ).fetchall()
    return [dict(r) for r in rows]


def export_csv(owner: str) -> str:
    """Return `owner`'s applications as a CSV string."""
    apps = get_all_applications(owner)
    if not apps:
        return "id,job_title,company,score,status,notes,saved_on\n"
    header = ",".join(apps[0].keys())
    lines = [header]
    for app in apps:
        lines.append(",".join(
            f'"{str(v).replace(chr(34), chr(39))}"' for v in app.values()
        ))
    return "\n".join(lines)
