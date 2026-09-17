"""SQLite-Zugriffsschicht fuer die Eventwochen-Daten."""

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
"""


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.executescript(SCHEMA)
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
