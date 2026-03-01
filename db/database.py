import sqlite3
import os

_default_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fun_planner.db")
DB_PATH = os.environ.get("DB_PATH", _default_path)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS activities (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    title         TEXT    NOT NULL,
    description   TEXT    DEFAULT '',
    category      TEXT    DEFAULT 'other',
    energy_level  TEXT    DEFAULT 'medium',
    cost_estimate TEXT    DEFAULT 'cheap',
    status        TEXT    DEFAULT 'idea',
    created_at    TEXT    DEFAULT (datetime('now', 'localtime')),
    notes         TEXT    DEFAULT ''
);

CREATE TABLE IF NOT EXISTS tags (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS activity_tags (
    activity_id INTEGER NOT NULL,
    tag_id      INTEGER NOT NULL,
    PRIMARY KEY (activity_id, tag_id),
    FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id)      REFERENCES tags(id)       ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS plans (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_id    INTEGER NOT NULL,
    scheduled_date TEXT,
    notes          TEXT    DEFAULT '',
    completed_at   TEXT,
    rating         INTEGER,
    reflection     TEXT    DEFAULT '',
    FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS steps (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id     INTEGER NOT NULL,
    description TEXT    NOT NULL,
    due_date    TEXT,
    is_done     INTEGER DEFAULT 0,
    order_index INTEGER DEFAULT 0,
    FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE
);
"""


def get_db() -> sqlite3.Connection:
    """Return a new connection with Row factory and FK support enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Create all tables if they don't already exist."""
    conn = get_db()
    with conn:
        conn.executescript(_SCHEMA)
    conn.close()
