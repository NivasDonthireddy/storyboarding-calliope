import asyncio
import json
from pathlib import Path

from calliope.queue.manager import QueueManager
from calliope.queue.worker import QueueWorker


def test_offline_assets_videos_and_manifest_through_manual_queue(
    client, settings, project, monkeypatch
):
    url = f"/api/projects/{project}"
    assert client.post(url + "/generate-story", json={}).status_code == 200
    assert client.post(url + "/generate-script", json={}).status_code == 200
    finish = QueueManager.mark_done

    def check_transition(self, job_id, paths):
        assert self.get_job(job_id)["status"] == "running"
        return finish(self, job_id, paths)

    monkeypatch.setattr(QueueManager, "mark_done", check_transition)
    export_url = f"/api/jobs/projects/{project}/export"
    assert client.post(export_url).json()["status"] == "pending"
    initial = asyncio.run(QueueWorker(settings).run_next())
    manifest = json.loads(Path(initial["output_paths"][0]).read_text())
    assert manifest["mode"] == "simulated" and manifest["outputs"] == []
    assert len(manifest["skipped_clips"]) == 8
    for kind, endpoint, count in (
        ("image", url + "/generate-assets", 3),
        ("video", f"/api/jobs/projects/{project}/generate-videos", 8),
    ):
        response = client.post(endpoint, json={})
        assert response.status_code == 200
        jobs = response.json()
        assert len(jobs) == count
        for job in jobs:
            assert job["status"] == "pending" and job["payload"]["mode"] == "simulated"
            done = client.post("/api/jobs/run-next").json()
            assert done["id"] == job["id"] and done["status"] == "done"
            output = Path(done["output_paths"][0])
            assert output.is_file() and output.is_relative_to(settings.data_dir)
            if kind == "image":
                assert output.suffix == ".svg" and "SIMULATED IMAGE" in output.read_text()
            else:
                assert json.loads(output.read_text())["mode"] == "simulated"
    assets = client.get(url + "/assets").json()
    assert all(Path(row["sheet_path"]).is_file() for row in assets["characters"])
    assert all(Path(row["reference_image_path"]).is_file() for row in assets["locations"])
    assert all(Path(row["clip_path"]).is_file() for row in assets["clips"])
    assert client.post(export_url).json()["status"] == "pending"
    exported = client.post("/api/jobs/run-next").json()
    manifest = json.loads(Path(exported["output_paths"][0]).read_text())
    assert manifest["mode"] == "simulated" and manifest["skipped_clips"] == []
    assert [entry["clip_id"] for entry in manifest["outputs"]] == [c["id"] for c in assets["clips"]]
    assert all(entry["mode"] == "simulated" for entry in manifest["outputs"])
    assert all(
        j["status"] == "done"
        for j in client.get("/api/jobs", params={"project_id": project}).json()
    )
    assert client.post("/api/jobs/run-next").json()["status"] == "idle"


def test_invalid_job_becomes_failed_not_running(client, settings, project):
    job = QueueManager(settings).enqueue(project, "image", {"mode": "invalid"})
    result = client.post("/api/jobs/run-next").json()
    assert result["id"] == job["id"] and result["status"] == "failed"
    assert result["error"] and result["output_paths"] == []
    assert QueueManager(settings).get_job(job["id"])["status"] == "failed"
