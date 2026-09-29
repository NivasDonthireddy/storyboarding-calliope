import sqlite3
from pathlib import Path

import pytest

from calliope.db import SCHEMA

CLEAR_DATA_SQL = Path(__file__).resolve().parents[2] / "clear_data.sql"


@pytest.fixture
def database():
    db = sqlite3.connect(":memory:")
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript(SCHEMA)
    db.executescript("""
        INSERT INTO projects (title, idea, genre, tone, target_duration)
        VALUES ('Project', 'Idea', 'Drama', 'Calm', '60 seconds');
        INSERT INTO story_beats (project_id, order_index, title, description)
        VALUES (1, 1, 'Beat', 'Description');
        INSERT INTO characters (project_id, name, appearance)
        VALUES (1, 'Character', 'Appearance');
        INSERT INTO locations (project_id, name, description)
        VALUES (1, 'Location', 'Description');
        INSERT INTO scenes
            (project_id, order_index, heading, action, dialog, duration_sec, location_id)
        VALUES (1, 1, 'Heading', 'Action', 'Dialog', 10, 1);
        INSERT INTO scene_characters (scene_id, character_id) VALUES (1, 1);
        INSERT INTO clips
            (project_id, scene_id, order_index, description, dialog_lines_covered, duration_sec)
        VALUES (1, 1, 1, 'Clip', '[1]', 10);
        INSERT INTO jobs (project_id, clip_id, kind, payload_json)
        VALUES (1, 1, 'video', '{}');
        INSERT INTO agent_sessions (project_id) VALUES (1);
        INSERT INTO agent_events (session_id, type, data_json) VALUES (1, 'message', '{}');
    """)
    try:
        yield db
    finally:
        db.close()


def table_counts(db):
    tables = db.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    return {
        name: db.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0] for (name,) in tables
    }


def test_clear_data_preserves_schema_and_counters_and_can_run_again(database):
    script = CLEAR_DATA_SQL.read_text(encoding="utf-8")
    schema = database.execute("SELECT * FROM sqlite_master ORDER BY name").fetchall()
    counters = database.execute("SELECT * FROM sqlite_sequence ORDER BY name").fetchall()
    assert set(table_counts(database).values()) == {1}

    for _ in range(2):
        database.executescript(script)

        assert set(table_counts(database).values()) == {0}
        assert database.execute("SELECT * FROM sqlite_master ORDER BY name").fetchall() == schema
        assert database.execute("SELECT * FROM sqlite_sequence ORDER BY name").fetchall() == counters
        assert database.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert database.execute("PRAGMA foreign_key_check").fetchall() == []
        assert not database.in_transaction


def test_clear_data_failure_can_roll_back_all_deletions(database):
    database.execute("""
        CREATE TRIGGER block_project_delete BEFORE DELETE ON projects
        BEGIN
            SELECT RAISE(ABORT, 'Deletion blocked');
        END;
    """)
    before = table_counts(database)

    with pytest.raises(sqlite3.IntegrityError, match="Deletion blocked"):
        database.executescript(CLEAR_DATA_SQL.read_text(encoding="utf-8"))

    assert database.in_transaction
    database.rollback()
    assert table_counts(database) == before
