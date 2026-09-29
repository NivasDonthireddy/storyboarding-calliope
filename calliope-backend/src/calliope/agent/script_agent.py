import logging

from fastapi import HTTPException

from calliope.agent.llm import ModelOutputError, generate_structured
from calliope.agent.prompts import build_script_chunk_messages
from calliope.config import Settings
from calliope.db import ensure_default_clip, get_db
from calliope.models.schemas import SceneDraft, ScriptDraft
from calliope.routers.story import get_story

SCRIPT_CHUNK = 2
logger = logging.getLogger("mini.script")


def _persist_scenes(conn, project_id: int, scenes: list[SceneDraft]) -> list[int]:
    scene_ids = []
    for scene in scenes:
        cur = conn.execute(
            """INSERT INTO scenes
               (project_id, order_index, heading, action, dialog, duration_sec, location_id)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                project_id,
                scene.order_index,
                scene.heading,
                scene.action,
                scene.dialog,
                scene.duration_sec,
                scene.location_id,
            ),
        )
        scene_id = cur.lastrowid
        for character_id in set(scene.character_ids):
            conn.execute("INSERT INTO scene_characters VALUES (?, ?)", (scene_id, character_id))
        ensure_default_clip(conn, scene_id, project_id)
        scene_ids.append(scene_id)
    return scene_ids


async def generate_script(
    settings: Settings,
    project_id: int,
    *,
    with_clips: bool = True,
    scenario: str = "normal",
) -> dict:
    story = get_story(settings, project_id)
    if not story["beats"]:
        raise HTTPException(409, "Generate the story first.")
    with get_db(settings.db_path) as conn:
        if conn.execute("SELECT 1 FROM scenes WHERE project_id = ?", (project_id,)).fetchone():
            raise HTTPException(409, "Script already exists. Create a new learning project.")
    character_ids = {character["id"] for character in story["characters"]}
    location_ids = {location["id"] for location in story["locations"]}
    written = []
    created_ids = []
    required_count = len(story["beats"])
    for start in range(1, required_count + 1, SCRIPT_CHUNK):
        count = min(SCRIPT_CHUNK, required_count - start + 1)
        messages = build_script_chunk_messages(story, start, count, written)
        draft = await generate_structured(settings, messages, ScriptDraft, scenario)
        if len(draft.scenes) != count:
            raise ModelOutputError(
                f"Expected {count} scenes in this chunk, got {len(draft.scenes)}"
            )
        for offset, scene in enumerate(draft.scenes):
            if (
                not set(scene.character_ids) <= character_ids
                or scene.location_id not in location_ids
            ):
                raise ModelOutputError("Scene references an unknown character or location ID.")
            scene.order_index = start + offset
        with get_db(settings.db_path) as conn:
            created_ids.extend(_persist_scenes(conn, project_id, draft.scenes))
        written.extend(scene.model_dump() for scene in draft.scenes)
        logger.info("SAVED scene chunk %s..%s (committed)", start, start + count - 1)
    coverage = None
    if with_clips:
        from calliope.agent.coverage_agent import expand_scene_coverage

        coverage = await expand_scene_coverage(settings, project_id)
    return {"scene_ids": created_ids, "scene_count": len(created_ids), "coverage": coverage}
