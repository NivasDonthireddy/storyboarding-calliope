from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from calliope.agent.harness.log import read_events
from calliope.agent.harness.runner import AgentRunner
from calliope.config import Settings, get_settings
from calliope.db import get_db
from calliope.models.schemas import MessageCreate, SessionCreate
from calliope.routers.projects import read_project

router = APIRouter()
Config = Annotated[Settings, Depends(get_settings)]


@router.post("/sessions")
def create_session(payload: SessionCreate, settings: Config):
    read_project(settings, payload.project_id)
    with get_db(settings.db_path) as conn:
        cur = conn.execute(
            "INSERT INTO agent_sessions (project_id) VALUES (?)",
            (payload.project_id,),
        )
        return {"id": cur.lastrowid, "project_id": payload.project_id, "status": "idle"}


@router.get("/sessions/{session_id}")
def get_session(session_id: int, settings: Config):
    with get_db(settings.db_path) as conn:
        row = conn.execute(
            "SELECT * FROM agent_sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(404, "Session not found")
    return {**dict(row), "events": read_events(settings, session_id)}


@router.post("/sessions/{session_id}/messages")
async def post_message(session_id: int, payload: MessageCreate, settings: Config):
    return await AgentRunner(settings).start_turn(session_id, payload)
