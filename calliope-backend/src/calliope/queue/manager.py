import json

from calliope.config import Settings
from calliope.db import get_db


def public_job(row) -> dict:
    job = dict(row)
    job["payload"] = json.loads(job["payload_json"])
    job["output_paths"] = json.loads(job["output_paths_json"])
    return job


class QueueManager:
    def __init__(self, settings: Settings):
        self.settings = settings

    def enqueue(
        self,
        project_id: int,
        kind: str,
        payload: dict,
        clip_id: int | None = None,
    ) -> dict:
        if kind not in ("image", "video", "export"):
            raise ValueError("Job kind must be image, video, or export")
        if not isinstance(payload, dict):
            raise ValueError("Job payload must be an object")
        payload = dict(payload)
        payload.setdefault("mode", "simulated" if self.settings.offline else "live")
        with get_db(self.settings.db_path) as conn:
            if not conn.execute("SELECT id FROM projects WHERE id = ?", (project_id,)).fetchone():
                raise ValueError("Project not found")
            if (
                clip_id is not None
                and not conn.execute(
                    "SELECT id FROM clips WHERE id = ? AND project_id = ?", (clip_id, project_id)
                ).fetchone()
            ):
                raise ValueError("Clip does not belong to this project")
            cursor = conn.execute(
                "INSERT INTO jobs (project_id, clip_id, kind, payload_json) VALUES (?, ?, ?, ?)",
                (project_id, clip_id, kind, json.dumps(payload)),
            )
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return public_job(row)

    def get_job(self, job_id: int) -> dict | None:
        with get_db(self.settings.db_path) as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return public_job(row) if row else None

    def list_jobs(self, project_id: int | None = None) -> list[dict]:
        with get_db(self.settings.db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM jobs WHERE (? IS NULL OR project_id = ?) ORDER BY id",
                (project_id, project_id),
            ).fetchall()
        return [public_job(row) for row in rows]

    def claim_next(self) -> dict | None:
        with get_db(self.settings.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT * FROM jobs WHERE status = 'pending' ORDER BY id LIMIT 1"
            ).fetchone()
            if row is None:
                return None
            changed = conn.execute(
                "UPDATE jobs SET status = 'running', error = NULL "
                "WHERE id = ? AND status = 'pending'",
                (row["id"],),
            ).rowcount
            if not changed:
                return None
            job = public_job(row)
            job["status"] = "running"
        return job

    def mark_done(self, job_id: int, output_paths: list[str]) -> dict:
        return self._finish(job_id, "done", output_paths, None)

    def mark_failed(self, job_id: int, error: str) -> dict:
        return self._finish(job_id, "failed", [], error)

    def _finish(self, job_id: int, status: str, output_paths: list[str], error: str | None):
        with get_db(self.settings.db_path) as conn:
            changed = conn.execute(
                "UPDATE jobs SET status = ?, output_paths_json = ?, error = ? "
                "WHERE id = ? AND status = 'running'",
                (status, json.dumps(output_paths), error, job_id),
            ).rowcount
            if not changed:
                raise ValueError("Only a running job can be completed or failed")
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return public_job(row)
