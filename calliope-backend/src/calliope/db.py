import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from calliope.config import Settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL, idea TEXT NOT NULL,
    genre TEXT NOT NULL, tone TEXT NOT NULL, target_duration TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS story_beats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id),
    order_index INTEGER NOT NULL, title TEXT NOT NULL, description TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS characters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id),
    name TEXT NOT NULL, appearance TEXT NOT NULL, sheet_path TEXT
);
CREATE TABLE IF NOT EXISTS locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id),
    name TEXT NOT NULL, description TEXT NOT NULL, reference_image_path TEXT
);
CREATE TABLE IF NOT EXISTS scenes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id),
    order_index INTEGER NOT NULL, heading TEXT NOT NULL,
    action TEXT NOT NULL, dialog TEXT NOT NULL, duration_sec INTEGER NOT NULL,
    location_id INTEGER NOT NULL REFERENCES locations(id)
);
CREATE TABLE IF NOT EXISTS scene_characters (
    scene_id INTEGER NOT NULL REFERENCES scenes(id),
    character_id INTEGER NOT NULL REFERENCES characters(id),
    PRIMARY KEY (scene_id, character_id)
);
CREATE TABLE IF NOT EXISTS clips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id),
    scene_id INTEGER NOT NULL REFERENCES scenes(id),
    order_index INTEGER NOT NULL, description TEXT NOT NULL,
    dialog_lines_covered TEXT NOT NULL, duration_sec INTEGER NOT NULL,
    clip_path TEXT
);
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id),
    clip_id INTEGER REFERENCES clips(id),
    kind TEXT NOT NULL CHECK (kind IN ('image', 'video', 'export')),
    status TEXT NOT NULL DEFAULT 'pending',
    payload_json TEXT NOT NULL, output_paths_json TEXT NOT NULL DEFAULT '[]',
    error TEXT
);
CREATE TABLE IF NOT EXISTS agent_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id),
    status TEXT NOT NULL DEFAULT 'idle'
);
CREATE TABLE IF NOT EXISTS agent_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES agent_sessions(id),
    type TEXT NOT NULL, data_json TEXT NOT NULL
);
"""


@contextmanager
def get_db(db_path: Path):
    conn = sqlite3.connect(db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        with conn:  # Commit on success; roll back on an exception.
            yield conn
    finally:
        conn.close()


def migrate_db(settings: Settings) -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.assets_dir.mkdir(parents=True, exist_ok=True)
    with get_db(settings.db_path) as conn:
        conn.executescript(SCHEMA)


def ensure_default_clip(conn, scene_id: int, project_id: int) -> None:
    scene = conn.execute("SELECT * FROM scenes WHERE id = ?", (scene_id,)).fetchone()
    lines = [line for line in scene["dialog"].splitlines() if line.strip()]
    conn.execute(
        """INSERT INTO clips
           (project_id, scene_id, order_index, description, dialog_lines_covered, duration_sec)
           VALUES (?, ?, 1, ?, ?, ?)""",
        (
            project_id,
            scene_id,
            scene["action"],
            json.dumps(list(range(1, len(lines) + 1))),
            scene["duration_sec"],
        ),
    )
