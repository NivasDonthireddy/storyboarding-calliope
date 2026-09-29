import json
import logging

from calliope.config import Settings
from calliope.db import get_db

logger = logging.getLogger("mini.agent")


def append_event(settings: Settings, session_id: int, kind: str, data: dict) -> None:
    with get_db(settings.db_path) as conn:
        conn.execute(
            "INSERT INTO agent_events (session_id, type, data_json) VALUES (?, ?, ?)",
            (session_id, kind, json.dumps(data)),
        )
    logger.info("SESSION %s %s: %s", session_id, kind, json.dumps(data))


def read_events(settings: Settings, session_id: int) -> list[dict]:
    with get_db(settings.db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM agent_events WHERE session_id = ? ORDER BY id",
            (session_id,),
        ).fetchall()
    return [
        {"id": row["id"], "type": row["type"], "data": json.loads(row["data_json"])} for row in rows
    ]


def derive_llm_history(events: list[dict]) -> list[dict]:
    return [event["data"]["message"] for event in events if event["type"] == "message"]
