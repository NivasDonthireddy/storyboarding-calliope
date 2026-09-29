import sqlite3

import httpx

from calliope.comfyui import dry_run
from calliope.comfyui.client import ComfyUIClient, ComfyUIError
from calliope.comfyui.patcher import asset_path, validate_workflow
from calliope.config import Settings
from calliope.db import get_db
from calliope.export.runner import export_project
from calliope.queue.manager import QueueManager


class QueueWorker:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.manager = QueueManager(settings)

    def _attach(self, job: dict, paths: list[str]) -> None:
        if not paths:
            raise ValueError("A successful job must produce at least one output")
        with get_db(self.settings.db_path) as conn:
            if job["kind"] == "video" and job["clip_id"] is not None:
                changed = conn.execute(
                    "UPDATE clips SET clip_path = ? WHERE id = ? AND project_id = ?",
                    (paths[0], job["clip_id"], job["project_id"]),
                ).rowcount
                if not changed:
                    raise ValueError("The clip no longer belongs to the job's project")
            target = job["payload"].get("target")
            if job["kind"] == "image" and target is not None:
                if not isinstance(target, dict):
                    raise ValueError("Image target must be an object")
                if target.get("kind") == "character":
                    sql = "UPDATE characters SET sheet_path = ? WHERE id = ? AND project_id = ?"
                elif target.get("kind") == "location":
                    sql = (
                        "UPDATE locations SET reference_image_path = ? "
                        "WHERE id = ? AND project_id = ?"
                    )
                else:
                    raise ValueError("Unknown image target kind")
                changed = conn.execute(
                    sql,
                    (paths[0], target.get("id"), job["project_id"]),
                ).rowcount
                if not changed:
                    raise ValueError("The asset no longer belongs to the job's project")

    async def run_next(self) -> dict:
        job = self.manager.claim_next()
        if job is None:
            return {"status": "idle", "message": "No pending jobs"}
        try:
            payload = job["payload"]
            expected_mode = "simulated" if self.settings.offline else "live"
            if payload.get("mode") not in ("live", "simulated"):
                raise ValueError("Job payload must explicitly select live or simulated mode")
            if payload["mode"] != expected_mode:
                current_mode = "offline" if self.settings.offline else "live"
                raise ValueError(
                    f"A queued {payload['mode']} job cannot run in {current_mode} mode; "
                    "use the matching configuration or enqueue it again"
                )
            output_dir = asset_path(
                self.settings,
                self.settings.assets_dir / str(job["project_id"]) / f"job-{job['id']}",
            )
            if job["kind"] == "export":
                paths = [export_project(self.settings, job["project_id"], output_dir)]
            elif payload.get("mode") == "simulated":
                if not isinstance(payload.get("prompt"), str) or not payload["prompt"].strip():
                    raise ValueError("Render payload is missing its prompt")
                paths = dry_run.render(job["kind"], payload, output_dir)
            elif payload.get("mode") == "live":
                if not isinstance(payload.get("prompt"), str) or not payload["prompt"].strip():
                    raise ValueError("Render payload is missing its prompt")
                definition = payload.get("workflow")
                if not definition:
                    raise ValueError(
                        "Live job has no workflow; register an API workflow and enqueue again"
                    )
                definition = validate_workflow(definition, job["kind"])
                client = ComfyUIClient(self.settings, payload.get("render_settings"))
                paths = await client.render(
                    definition,
                    payload["prompt"],
                    output_dir,
                    reference_paths=payload.get("reference_paths", []),
                    job_id=job["id"],
                )
            self._attach(job, paths)
            return self.manager.mark_done(job["id"], paths)
        except (ComfyUIError, httpx.HTTPError, OSError, ValueError, sqlite3.Error) as exc:
            return self.manager.mark_failed(job["id"], f"{type(exc).__name__}: {exc}")
        finally:
            # Unexpected programming errors still propagate to the debugger, but release this job.
            current = self.manager.get_job(job["id"])
            if current and current["status"] == "running":
                self.manager.mark_failed(
                    job["id"],
                    "Worker interrupted or unexpected error; inspect server traceback",
                )
