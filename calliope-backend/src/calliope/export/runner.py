import json
from pathlib import Path
from uuid import uuid4

from calliope.comfyui.client import VIDEO_SUFFIXES
from calliope.comfyui.patcher import asset_path
from calliope.config import Settings
from calliope.db import get_db


def export_project(
    settings: Settings,
    project_id: int,
    output_dir: Path | None = None,
) -> str:
    with get_db(settings.db_path) as conn:
        project = conn.execute("SELECT id FROM projects WHERE id = ?", (project_id,)).fetchone()
        if project is None:
            raise ValueError("Project not found")
        clips = [
            dict(row)
            for row in conn.execute(
                "SELECT c.*, s.order_index AS scene_order FROM clips c "
                "JOIN scenes s ON s.id = c.scene_id "
                "WHERE c.project_id = ? AND s.project_id = ? "
                "ORDER BY s.order_index, c.order_index, c.id",
                (project_id, project_id),
            )
        ]
    outputs, skipped = [], []
    for clip in clips:
        entry = {"clip_id": clip["id"], "scene_id": clip["scene_id"]}
        if not clip["clip_path"]:
            skipped.append({**entry, "reason": "Clip has not been rendered"})
            continue
        try:
            path = asset_path(settings, clip["clip_path"])
        except ValueError:
            skipped.append({**entry, "reason": "Clip path is outside mini assets"})
            continue
        if not path.is_file():
            skipped.append({**entry, "reason": "Clip file is missing"})
            continue
        if path.suffix.lower() == ".json":
            try:
                storyboard = json.loads(path.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                skipped.append({**entry, "reason": "Storyboard JSON could not be read"})
                continue
            if not isinstance(storyboard, dict) or storyboard.get("mode") != "simulated":
                skipped.append({**entry, "reason": "JSON is not a simulated storyboard"})
                continue
            mode = "simulated"
        elif path.suffix.lower() in VIDEO_SUFFIXES:
            mode = "live"
        else:
            skipped.append({**entry, "reason": "File is not video or a simulated storyboard"})
            continue
        outputs.append(
            {
                **entry,
                "path": str(path),
                "mode": mode,
                "duration_sec": clip["duration_sec"],
                "scene_order": clip["scene_order"],
                "clip_order": clip["order_index"],
            }
        )
    modes = {output["mode"] for output in outputs}
    mode = (
        next(iter(modes))
        if len(modes) == 1
        else ("mixed" if modes else ("simulated" if settings.offline else "live"))
    )
    directory = asset_path(
        settings, output_dir or (settings.assets_dir / str(project_id) / "exports" / uuid4().hex)
    )
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "export-manifest.json"
    path.write_text(
        json.dumps(
            {
                "format": "calliope-export-manifest",
                "project_id": project_id,
                "mode": mode,
                "notice": (
                    "This JSON manifest is not a movie. "
                    "Production uses FFmpeg to join real clips."
                ),
                "outputs": outputs,
                "skipped_clips": skipped,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return str(path)
