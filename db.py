"""SQLite-Zugriffsschicht fuer die Eventwochen-Daten."""

import json
import sqlite3
from datetime import datetime

from config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    week_number  INTEGER NOT NULL,
    event_order  INTEGER NOT NULL,
    name         TEXT NOT NULL,
    feedback     TEXT NOT NULL DEFAULT '',
    updated_at   TEXT,
    PRIMARY KEY (week_number, event_order)
);

CREATE TABLE IF NOT EXISTS feedback_history (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    week_number  INTEGER NOT NULL,
    event_order  INTEGER NOT NULL,
    feedback     TEXT NOT NULL,
    run_date     TEXT NOT NULL,
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    week_number  INTEGER NOT NULL,
    week_start   TEXT NOT NULL,
    week_end     TEXT NOT NULL,
    docx_path    TEXT NOT NULL,
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS forum_snapshots (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    week_number  INTEGER NOT NULL,
    week_start   TEXT NOT NULL,
    source_url   TEXT,
    body_text    TEXT NOT NULL DEFAULT '',
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS forum_snapshot_images (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id  INTEGER NOT NULL,
    sort_order   INTEGER NOT NULL,
    filename     TEXT NOT NULL,
    phash        TEXT NOT NULL,
    orig_url     TEXT
);
"""


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.executescript(SCHEMA)
    cols = [row[1] for row in conn.execute("PRAGMA table_info(forum_snapshots)")]
    if "events_json" not in cols:
        conn.execute("ALTER TABLE forum_snapshots ADD COLUMN events_json TEXT NOT NULL DEFAULT '[]'")
    conn.commit()
    conn.close()


def seed_events(seed_data, overwrite=False):
    """
    seed_data: dict { week_number: [ (event_order, name, feedback), ... ] }
    Fuegt Events nur ein, wenn sie noch nicht existieren (es sei denn
    overwrite=True).
    """
    conn = get_connection()
    cur = conn.cursor()
    for week_number, events in seed_data.items():
        for event_order, name, feedback in events:
            if overwrite:
                cur.execute(
                    """INSERT INTO events (week_number, event_order, name, feedback, updated_at)
                       VALUES (?, ?, ?, ?, ?)
                       ON CONFLICT(week_number, event_order) DO UPDATE SET
                         name=excluded.name, feedback=excluded.feedback, updated_at=excluded.updated_at""",
                    (week_number, event_order, name, feedback, datetime.now().isoformat()),
                )
            else:
                cur.execute(
                    """INSERT OR IGNORE INTO events (week_number, event_order, name, feedback, updated_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    (week_number, event_order, name, feedback, datetime.now().isoformat()),
                )
    conn.commit()
    conn.close()


def get_events(week_number):
    conn = get_connection()
    cur = conn.execute(
        "SELECT event_order, name, feedback FROM events WHERE week_number = ? ORDER BY event_order",
        (week_number,),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def update_feedback(week_number, event_order, feedback, run_date):
    conn = get_connection()
    now = datetime.now().isoformat()
    conn.execute(
        """INSERT INTO events (week_number, event_order, name, feedback, updated_at)
           VALUES (?, ?, '', ?, ?)
           ON CONFLICT(week_number, event_order) DO UPDATE SET
             feedback=excluded.feedback, updated_at=excluded.updated_at""",
        (week_number, event_order, feedback, now),
    )
    conn.execute(
        """INSERT INTO feedback_history (week_number, event_order, feedback, run_date, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (week_number, event_order, feedback, run_date, now),
    )
    conn.commit()
    conn.close()


def get_last_run(week_number):
    conn = get_connection()
    cur = conn.execute(
        """SELECT week_start, week_end, docx_path, created_at FROM runs
           WHERE week_number = ? ORDER BY id DESC LIMIT 1""",
        (week_number,),
    )
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def log_run(week_number, week_start, week_end, docx_path):
    conn = get_connection()
    conn.execute(
        """INSERT INTO runs (week_number, week_start, week_end, docx_path, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (week_number, week_start.isoformat(), week_end.isoformat(), docx_path, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def get_snapshot_for_week(week_number, week_start_iso):
    conn = get_connection()
    cur = conn.execute(
        """SELECT id, week_number, week_start, source_url, body_text, created_at, events_json
           FROM forum_snapshots
           WHERE week_number = ? AND week_start = ?
           ORDER BY id DESC LIMIT 1""",
        (week_number, week_start_iso),
    )
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_previous_snapshot(week_number, week_start_iso):
    conn = get_connection()
    cur = conn.execute(
        """SELECT id, week_number, week_start, source_url, body_text, created_at, events_json
           FROM forum_snapshots
           WHERE week_number = ? AND week_start < ?
           ORDER BY week_start DESC, id DESC LIMIT 1""",
        (week_number, week_start_iso),
    )
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_snapshot_images(snapshot_id):
    conn = get_connection()
    cur = conn.execute(
        """SELECT id, sort_order, filename, phash, orig_url
           FROM forum_snapshot_images
           WHERE snapshot_id = ?
           ORDER BY sort_order""",
        (snapshot_id,),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def delete_snapshot(snapshot_id):
    conn = get_connection()
    cur = conn.execute(
        "SELECT filename FROM forum_snapshot_images WHERE snapshot_id = ?",
        (snapshot_id,),
    )
    files = [r["filename"] for r in cur.fetchall()]
    conn.execute("DELETE FROM forum_snapshot_images WHERE snapshot_id = ?", (snapshot_id,))
    conn.execute("DELETE FROM forum_snapshots WHERE id = ?", (snapshot_id,))
    conn.commit()
    conn.close()
    return files


def save_snapshot(week_number, week_start_iso, source_url, body_text, images, events=None):
    """
    images: list of dicts {filename, phash, orig_url}
    Ersetzt einen vorhandenen Snapshot derselben Woche/desselben Starts.
    """
    existing = get_snapshot_for_week(week_number, week_start_iso)
    old_files = delete_snapshot(existing["id"]) if existing else []

    conn = get_connection()
    cur = conn.execute(
        """INSERT INTO forum_snapshots (week_number, week_start, source_url, body_text, created_at, events_json)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            week_number,
            week_start_iso,
            source_url or "",
            body_text or "",
            datetime.now().isoformat(),
            json.dumps(events or [], ensure_ascii=False),
        ),
    )
    snapshot_id = cur.lastrowid
    for order, img in enumerate(images):
        conn.execute(
            """INSERT INTO forum_snapshot_images
               (snapshot_id, sort_order, filename, phash, orig_url)
               VALUES (?, ?, ?, ?, ?)""",
            (snapshot_id, order, img["filename"], img["phash"], img.get("orig_url") or ""),
        )
    conn.commit()
    conn.close()
    return snapshot_id, old_files
