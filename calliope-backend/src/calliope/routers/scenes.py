import json
from typing import Annotated

from fastapi import APIRouter, Depends

from calliope.agent.coverage_agent import expand_scene_coverage
from calliope.agent.script_agent import generate_script
from calliope.config import Settings, get_settings
from calliope.db import get_db
from calliope.models.schemas import GenerationOptions, ScriptOptions
from calliope.routers.projects import read_project

router = APIRouter()
Config = Annotated[Settings, Depends(get_settings)]


def list_scenes(settings: Settings, project_id: int) -> dict:
    read_project(settings, project_id)
    with get_db(settings.db_path) as conn:
        scenes = [
            dict(row)
            for row in conn.execute(
                "SELECT * FROM scenes WHERE project_id = ? ORDER BY order_index",
                (project_id,),
            )
        ]
        for scene in scenes:
            scene["character_ids"] = [
                row["character_id"]
                for row in conn.execute(
                    "SELECT character_id FROM scene_characters WHERE scene_id = ?",
                    (scene["id"],),
                )
            ]
            scene["clips"] = []
            for row in conn.execute(
                "SELECT * FROM clips WHERE scene_id = ? ORDER BY order_index",
                (scene["id"],),
            ):
                clip = dict(row)
                clip["dialog_lines_covered"] = json.loads(clip["dialog_lines_covered"])
                scene["clips"].append(clip)
    return {"scenes": scenes}


@router.get("/{project_id}/scenes")
def read_scenes(project_id: int, settings: Config):
    return list_scenes(settings, project_id)


@router.post("/{project_id}/generate-script")
async def write_script(project_id: int, payload: ScriptOptions, settings: Config):
    return await generate_script(
        settings,
        project_id,
        with_clips=payload.with_clips,
        scenario=payload.scenario,
    )


@router.post("/{project_id}/expand-clips")
async def expand_clips(project_id: int, payload: GenerationOptions, settings: Config):
    return await expand_scene_coverage(settings, project_id, payload.scenario)
