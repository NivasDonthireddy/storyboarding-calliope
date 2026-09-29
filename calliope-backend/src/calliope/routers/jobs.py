from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from calliope.agent.video_agent import enqueue_video_jobs
from calliope.comfyui.patcher import render_payload
from calliope.config import Settings, get_settings
from calliope.queue.manager import QueueManager
from calliope.queue.worker import QueueWorker
from calliope.routers.projects import read_project

router = APIRouter()
Config = Annotated[Settings, Depends(get_settings)]


class VideoOptions(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    workflow_name: str = "video"
    clip_ids: list[int] | None = None


class RenderOptions(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    kind: Literal["image", "video"]
    prompt: str = Field(min_length=1)
    workflow_name: str | None = None
    reference_paths: list[str] = Field(default_factory=list)


@router.post("/projects/{project_id}/generate-videos")
async def generate_videos(project_id: int, settings: Config, payload: VideoOptions | None = None):
    payload = payload or VideoOptions()
    try:
        return await enqueue_video_jobs(
            settings,
            project_id,
            payload.workflow_name,
            payload.clip_ids,
        )
    except (ValueError, OSError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/projects/{project_id}/render")
def render(project_id: int, payload: RenderOptions, settings: Config):
    read_project(settings, project_id)
    try:
        snapshot = render_payload(
            settings,
            payload.kind,
            payload.prompt,
            payload.workflow_name or payload.kind,
            payload.reference_paths,
        )
        return QueueManager(settings).enqueue(project_id, payload.kind, snapshot)
    except (ValueError, OSError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/projects/{project_id}/export")
def enqueue_export(project_id: int, settings: Config):
    read_project(settings, project_id)
    return QueueManager(settings).enqueue(
        project_id,
        "export",
        {
            "mode": "simulated" if settings.offline else "live",
            "format": "manifest",
        },
    )


@router.get("")
def list_jobs(settings: Config, project_id: int | None = None):
    if project_id is not None:
        read_project(settings, project_id)
    return QueueManager(settings).list_jobs(project_id)


@router.post("/run-next")
async def run_next(settings: Config):
    return await QueueWorker(settings).run_next()


@router.get("/{job_id}")
def get_job(job_id: int, settings: Config):
    job = QueueManager(settings).get_job(job_id)
    if job is None:
        raise HTTPException(404, "Job not found")
    return job
