import json

from calliope.comfyui.patcher import render_payload
from calliope.config import Settings
from calliope.db import get_db
from calliope.queue.manager import QueueManager
from calliope.routers.projects import read_project


def _clip_dialog(clip: dict, scene: dict) -> str:
    covered = clip["dialog_lines_covered"]
    if isinstance(covered, str):
        covered = json.loads(covered)
    lines = [line for line in scene["dialog"].splitlines() if line.strip()]
    if not isinstance(covered, list) or any(
        type(number) is not int or number < 1 or number > len(lines) for number in covered
    ):
        raise ValueError(f"Clip {clip['id']} has invalid 1-based dialog_lines_covered")
    if len(set(covered)) != len(covered):
        raise ValueError(f"Clip {clip['id']} repeats a dialog line")
    return "\n".join(lines[number - 1] for number in covered)


async def enqueue_video_jobs(
    settings: Settings,
    project_id: int,
    workflow_name: str = "video",
    clip_ids: list[int] | None = None,
) -> list[dict]:
    project = read_project(settings, project_id)
    with get_db(settings.db_path) as conn:
        clips = [
            dict(row)
            for row in conn.execute(
                "SELECT c.* FROM clips c JOIN scenes s ON s.id = c.scene_id "
                "WHERE c.project_id = ? AND s.project_id = ? "
                "ORDER BY s.order_index, c.order_index, c.id",
                (project_id, project_id),
            )
        ]
        if any(type(item) is not int for item in clip_ids or []):
            raise ValueError("Clip IDs must be integers")
        selected_ids = {clip["id"] for clip in clips} if clip_ids is None else set(clip_ids)
        if selected_ids - {clip["id"] for clip in clips}:
            raise ValueError(f"Every selected clip must belong to project {project_id}")
        prepared = []
        for clip in clips:
            if clip["id"] not in selected_ids:
                continue
            scene = dict(
                conn.execute("SELECT * FROM scenes WHERE id = ?", (clip["scene_id"],)).fetchone()
            )
            location = conn.execute(
                "SELECT * FROM locations WHERE id = ? AND project_id = ?",
                (scene["location_id"], project_id),
            ).fetchone()
            if location is None:
                raise ValueError("The clip's scene location must belong to the same project")
            characters = [
                dict(row)
                for row in conn.execute(
                    "SELECT c.* FROM characters c "
                    "JOIN scene_characters sc ON sc.character_id = c.id "
                    "WHERE sc.scene_id = ? ORDER BY c.id",
                    (scene["id"],),
                )
            ]
            if any(character["project_id"] != project_id for character in characters):
                raise ValueError("The scene's characters must belong to the same project")
            dialog = _clip_dialog(clip, scene)
            prompt = (
                f"{clip['description']}\nDuration: {clip['duration_sec']} seconds.\n"
                f"Location: {location['name']}. {location['description']}\n"
                "Characters: "
                + "; ".join(
                    f"{character['name']}: {character['appearance']}" for character in characters
                )
                + f"\nSpoken dialogue for this clip only:\n{dialog or '(none)'}\n"
                f"Genre: {project['genre']}. Tone: {project['tone']}."
            )
            references = [
                character["sheet_path"] for character in characters if character["sheet_path"]
            ]
            if location["reference_image_path"]:
                references.append(location["reference_image_path"])
            payload = render_payload(settings, "video", prompt, workflow_name, references)
            payload.update(
                {
                    "scene_id": scene["id"],
                    "dialog": dialog,
                    "duration_sec": clip["duration_sec"],
                    "dialog_lines_covered": json.loads(clip["dialog_lines_covered"]),
                }
            )
            prepared.append((clip["id"], payload))
    if not prepared:
        raise ValueError("No clips selected; generate coverage or select existing clip IDs")
    manager = QueueManager(settings)
    return [
        manager.enqueue(project_id, "video", payload, clip_id=clip_id)
        for clip_id, payload in prepared
    ]
