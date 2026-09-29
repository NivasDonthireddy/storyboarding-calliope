from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from calliope.config import Settings, get_settings
from calliope.db import get_db
from calliope.models.schemas import ProjectCreate

router = APIRouter()
Config = Annotated[Settings, Depends(get_settings)]


def read_project(settings: Settings, project_id: int) -> dict:
    with get_db(settings.db_path) as conn:
        row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Project not found")
    return dict(row)


@router.post("")
def create_project(payload: ProjectCreate, settings: Config):
    with get_db(settings.db_path) as conn:
        cur = conn.execute(
            """INSERT INTO projects (title, idea, genre, tone, target_duration)
               VALUES (:title, :idea, :genre, :tone, :target_duration)""",
            payload.model_dump(),
        )
        project_id = cur.lastrowid
    return read_project(settings, project_id)


@router.get("")
def list_projects(settings: Config):
    with get_db(settings.db_path) as conn:
        return [dict(row) for row in conn.execute("SELECT * FROM projects ORDER BY id")]


@router.get("/{project_id}")
def get_project(project_id: int, settings: Config):
    return read_project(settings, project_id)
