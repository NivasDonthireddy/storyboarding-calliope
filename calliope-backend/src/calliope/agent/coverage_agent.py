import json

from fastapi import HTTPException

from calliope.agent.llm import ModelOutputError, generate_structured
from calliope.agent.prompts import build_coverage_messages
from calliope.config import Settings
from calliope.db import get_db
from calliope.models.schemas import CoverageDraft
from calliope.routers.projects import read_project


async def expand_scene_coverage(
    settings: Settings,
    project_id: int,
    scenario: str = "normal",
) -> dict:
    read_project(settings, project_id)
    with get_db(settings.db_path) as conn:
        scenes = [
            dict(row)
            for row in conn.execute(
                "SELECT * FROM scenes WHERE project_id = ? ORDER BY order_index",
                (project_id,),
            )
        ]
        if conn.execute("SELECT 1 FROM jobs WHERE project_id = ?", (project_id,)).fetchone():
            raise HTTPException(409, "Expand coverage before creating jobs; preserve render links.")
    if not scenes:
        raise HTTPException(409, "Generate the script first.")
    clip_count = 0
    for scene in scenes:
        draft = await generate_structured(
            settings,
            build_coverage_messages(scene),
            CoverageDraft,
            scenario,
        )
        lines = [line for line in scene["dialog"].splitlines() if line.strip()]
        covered = [index for clip in draft.clips for index in clip.dialog_lines_covered]
        if sorted(covered) != list(range(1, len(lines) + 1)):
            raise ModelOutputError("Coverage must assign every dialogue line exactly once.")
        with get_db(settings.db_path) as conn:
            conn.execute("DELETE FROM clips WHERE scene_id = ?", (scene["id"],))
            for index, clip in enumerate(draft.clips, 1):
                conn.execute(
                    """INSERT INTO clips
                       (project_id, scene_id, order_index, description,
                        dialog_lines_covered, duration_sec) VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        project_id,
                        scene["id"],
                        index,
                        clip.description,
                        json.dumps(clip.dialog_lines_covered),
                        clip.duration_sec,
                    ),
                )
        clip_count += len(draft.clips)
    return {"scene_count": len(scenes), "clip_count": clip_count}
