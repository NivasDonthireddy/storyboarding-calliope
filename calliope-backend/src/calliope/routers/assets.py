from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict

from calliope.agent.asset_agent import enqueue_asset_jobs
from calliope.comfyui.patcher import asset_path
from calliope.config import Settings, get_settings
from calliope.db import get_db
from calliope.routers.projects import read_project

router = APIRouter()
Config = Annotated[Settings, Depends(get_settings)]


class AssetOptions(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    workflow_name: str = "image"
    character_ids: list[int] | None = None
    location_ids: list[int] | None = None


@router.get("/projects/{project_id}/assets")
def list_assets(project_id: int, settings: Config):
    read_project(settings, project_id)
    with get_db(settings.db_path) as conn:
        characters = [
            dict(row)
            for row in conn.execute(
                "SELECT * FROM characters WHERE project_id = ? ORDER BY id",
                (project_id,),
            )
        ]
        locations = [
            dict(row)
            for row in conn.execute(
                "SELECT * FROM locations WHERE project_id = ? ORDER BY id",
                (project_id,),
            )
        ]
        clips = [
            dict(row)
            for row in conn.execute(
                "SELECT c.* FROM clips c JOIN scenes s ON s.id = c.scene_id "
                "WHERE c.project_id = ? AND s.project_id = ? "
                "ORDER BY s.order_index, c.order_index, c.id",
                (project_id, project_id),
            )
        ]
    return {"characters": characters, "locations": locations, "clips": clips}


@router.post("/projects/{project_id}/generate-assets")
async def generate_assets(project_id: int, settings: Config, payload: AssetOptions | None = None):
    payload = payload or AssetOptions()
    try:
        return await enqueue_asset_jobs(
            settings,
            project_id,
            payload.workflow_name,
            payload.character_ids,
            payload.location_ids,
        )
    except (ValueError, OSError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/assets/file")
def get_asset(path: str, settings: Config):
    try:
        resolved = asset_path(settings, path)
    except ValueError as exc:
        raise HTTPException(404, "Asset not found") from exc
    if not resolved.is_file():
        raise HTTPException(404, "Asset not found")
    return FileResponse(
        resolved,
        headers={
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'; sandbox",
        },
    )
