from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from calliope.agent.llm import generate_structured
from calliope.agent.prompts import build_story_messages
from calliope.config import Settings, get_settings
from calliope.db import get_db
from calliope.models.schemas import BeatUpdate, GenerationOptions, StoryDraft
from calliope.routers.projects import read_project

router = APIRouter()
Config = Annotated[Settings, Depends(get_settings)]


def get_story(settings: Settings, project_id: int) -> dict:
    project = read_project(settings, project_id)
    with get_db(settings.db_path) as conn:
        result = {"project": project}
        for table, key in (
            ("story_beats", "beats"),
            ("characters", "characters"),
            ("locations", "locations"),
        ):
            order = "order_index" if table == "story_beats" else "id"
            result[key] = [
                dict(row)
                for row in conn.execute(
                    f"SELECT * FROM {table} WHERE project_id = ? ORDER BY {order}",
                    (project_id,),
                )
            ]
    return result


async def generate_story(settings: Settings, project_id: int, scenario: str = "normal") -> dict:
    project = read_project(settings, project_id)
    draft = await generate_structured(settings, build_story_messages(project), StoryDraft, scenario)
    with get_db(settings.db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        if conn.execute("SELECT 1 FROM story_beats WHERE project_id = ?", (project_id,)).fetchone():
            raise HTTPException(409, "Story already exists. Create a new learning project.")
        for beat in draft.beats:
            conn.execute(
                """INSERT INTO story_beats (project_id, order_index, title, description)
                   VALUES (?, ?, ?, ?)""",
                (project_id, beat.order_index, beat.title, beat.description),
            )
        for character in draft.characters:
            conn.execute(
                "INSERT INTO characters (project_id, name, appearance) VALUES (?, ?, ?)",
                (project_id, character.name, character.appearance),
            )
        for location in draft.locations:
            conn.execute(
                "INSERT INTO locations (project_id, name, description) VALUES (?, ?, ?)",
                (project_id, location.name, location.description),
            )
        conn.execute("UPDATE projects SET idea = ? WHERE id = ?", (draft.logline, project_id))
    return get_story(settings, project_id)


def update_beat(settings: Settings, project_id: int, beat_id: int, title: str) -> dict:
    with get_db(settings.db_path) as conn:
        cur = conn.execute(
            "UPDATE story_beats SET title = ? WHERE id = ? AND project_id = ?",
            (title, beat_id, project_id),
        )
        if cur.rowcount != 1:
            raise HTTPException(404, "Beat not found in this project")
        return dict(conn.execute("SELECT * FROM story_beats WHERE id = ?", (beat_id,)).fetchone())


@router.get("/{project_id}/story")
def read_story(project_id: int, settings: Config):
    return get_story(settings, project_id)


@router.post("/{project_id}/generate-story")
async def draft_story(project_id: int, settings: Config, payload: GenerationOptions):
    return await generate_story(settings, project_id, payload.scenario)


@router.patch("/{project_id}/beats/{beat_id}")
def edit_beat(project_id: int, beat_id: int, payload: BeatUpdate, settings: Config):
    return update_beat(settings, project_id, beat_id, payload.title)
