import json
from typing import Annotated, Literal
from urllib.parse import quote

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from calliope.comfyui.patcher import (
    SECRET_KEYS,
    load_workflow,
    validate_workflow,
    workflow_path,
)
from calliope.config import Settings, get_settings

router = APIRouter()
Config = Annotated[Settings, Depends(get_settings)]


class WorkflowRegistration(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    kind: Literal["image", "video"]
    prompt_node: str
    prompt_input: str = "text"
    reference_node: str | None = None
    reference_input: str | None = None
    workflow: dict[str, dict] = Field(min_length=1)


@router.get("")
def list_workflows(settings: Config):
    names = {
        path.stem
        for directory in (settings.workflow_dir, settings.data_dir / "workflows")
        if directory.is_dir()
        for path in directory.glob("*.json")
    }
    entries = []
    for name in sorted(names):
        try:
            definition = load_workflow(settings, name)
            entries.append({"name": name, "kind": definition["kind"], "valid": True})
        except (OSError, ValueError) as exc:
            entries.append({"name": name, "valid": False, "error": str(exc)})
    return entries


@router.get("/nodes/{class_type}")
async def inspect_node(class_type: str, settings: Config):
    """Read node/model choices only; never submits a render."""
    if settings.offline:
        raise HTTPException(400, "Node discovery needs live mode")
    try:
        async with httpx.AsyncClient(
            base_url=settings.comfyui_base_url,
            timeout=settings.request_timeout_sec,
            trust_env=False,
        ) as client:
            response = await client.get(f"/object_info/{quote(class_type, safe='')}")
            response.raise_for_status()
            info = response.json().get(class_type)
        if not isinstance(info, dict):
            raise HTTPException(404, "ComfyUI node not found")
        inputs = {}
        for section in ("required", "optional"):
            inputs[section] = {
                name: specification[0]
                for name, specification in info.get("input", {}).get(section, {}).items()
                if not SECRET_KEYS.search(name)
                and isinstance(specification, list)
                and specification
            }
        return {
            "class_type": class_type,
            "input_types_or_choices": inputs,
            "outputs": info.get("output", []),
            "external_api": bool(info.get("api_node")),
        }
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(502, f"ComfyUI node discovery failed: {exc}") from exc


@router.get("/{name}")
def get_workflow(name: str, settings: Config):
    try:
        return load_workflow(settings, name)
    except (ValueError, OSError) as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/{name}")
def register_workflow(name: str, payload: WorkflowRegistration, settings: Config):
    try:
        definition = validate_workflow(payload.model_dump(exclude_none=True))
        path = workflow_path(settings.data_dir / "workflows", name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(definition, indent=2), encoding="utf-8")
    except (ValueError, OSError) as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"name": name, "kind": definition["kind"], "path": str(path), "render_submitted": False}
