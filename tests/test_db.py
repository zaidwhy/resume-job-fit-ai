"""The tracker runs on one shared SQLite file behind a public URL: rows must be per owner."""

from __future__ import annotations

import sqlite3

import pytest

import db


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "tracker.db")


def test_rows_are_invisible_to_other_owners():
    a = db.save_application("owner-a", "Backend Engineer", 82, company="Acme")
    db.save_application("owner-b", "ML Engineer", 71)
    assert [r["id"] for r in db.get_all_applications("owner-a")] == [a]
    assert db.get_stats("owner-a")["total"] == 1
    assert db.get_stats("owner-b")["total"] == 1
    assert db.get_stats("nobody")["total"] == 0
    assert "Backend Engineer" in db.export_csv("owner-a")
    assert "ML Engineer" not in db.export_csv("owner-a")


def test_updates_and_deletes_cannot_cross_owners():
    a = db.save_application("owner-a", "Backend Engineer", 82)
    db.update_status("owner-b", a, "Applied")
    db.update_notes("owner-b", a, "hijacked")
    db.delete_application("owner-b", a)
    (row,) = db.get_all_applications("owner-a")
    assert row["status"] == "Saved" and row["notes"] == ""
    db.update_status("owner-a", a, "Applied")
    assert db.get_all_applications("owner-a")[0]["status"] == "Applied"
    db.delete_application("owner-a", a)
    assert db.get_all_applications("owner-a") == []


def test_invalid_status_is_rejected():
    a = db.save_application("owner-a", "x", 50)
    with pytest.raises(ValueError):
        db.update_status("owner-a", a, "Ghosted")


def test_legacy_database_gets_the_owner_column(tmp_path, monkeypatch):
    legacy = tmp_path / "legacy.db"
    con = sqlite3.connect(legacy)
    con.execute(
        "CREATE TABLE applications (id INTEGER PRIMARY KEY AUTOINCREMENT, job_title TEXT NOT NULL, "
        "company TEXT NOT NULL DEFAULT '', score INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'Saved', "
        "notes TEXT NOT NULL DEFAULT '', saved_on TEXT NOT NULL)"
    )
    con.execute("INSERT INTO applications (job_title, score, saved_on) VALUES ('old', 60, '2026-01-01')")
    con.commit()
    con.close()
    monkeypatch.setattr(db, "DB_PATH", legacy)
    db.init_db()
    # pre-scoping rows keep the empty owner: still in the file, shown to no real session
    legacy_rows = db.get_all_applications("")
    assert len(legacy_rows) == 1 and legacy_rows[0]["job_title"] == "old"
    assert db.get_all_applications("someone") == []
    assert db.get_stats("someone")["total"] == 0
