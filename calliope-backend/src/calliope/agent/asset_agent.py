from calliope.comfyui.patcher import render_payload
from calliope.config import Settings
from calliope.db import get_db
from calliope.queue.manager import QueueManager
from calliope.routers.projects import read_project


async def enqueue_asset_jobs(
    settings: Settings,
    project_id: int,
    workflow_name: str = "image",
    character_ids: list[int] | None = None,
    location_ids: list[int] | None = None,
) -> list[dict]:
    project = read_project(settings, project_id)
    all_assets = character_ids is None and location_ids is None
    with get_db(settings.db_path) as conn:
        characters = [
            dict(row)
            for row in conn.execute(
                "SELECT * FROM characters WHERE project_id = ? ORDER BY id", (project_id,)
            )
        ]
        locations = [
            dict(row)
            for row in conn.execute(
                "SELECT * FROM locations WHERE project_id = ? ORDER BY id", (project_id,)
            )
        ]
    selections = (
        ("character", characters, character_ids),
        ("location", locations, location_ids),
    )
    prepared = []
    for kind, rows, requested in selections:
        if any(type(item) is not int for item in requested or []):
            raise ValueError(f"{kind} IDs must be integers")
        selected_ids = {row["id"] for row in rows} if all_assets else set(requested or [])
        if selected_ids - {row["id"] for row in rows}:
            raise ValueError(f"Every selected {kind} must belong to project {project_id}")
        for row in rows:
            if row["id"] not in selected_ids:
                continue
            if kind == "character":
                prompt = (
                    f"Character reference sheet for {row['name']}. {row['appearance']}. "
                    "Consistent appearance, neutral background, clear full-body view."
                )
            else:
                prompt = f"Location reference image: {row['name']}. {row['description']}."
            prompt += f" Genre: {project['genre']}. Tone: {project['tone']}."
            payload = render_payload(settings, "image", prompt, workflow_name)
            payload["target"] = {"kind": kind, "id": row["id"]}
            prepared.append(payload)
    if not prepared:
        raise ValueError("No assets selected; generate a story or select existing entity IDs first")
    manager = QueueManager(settings)
    return [manager.enqueue(project_id, "image", payload) for payload in prepared]
