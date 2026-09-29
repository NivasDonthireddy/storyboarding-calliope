import asyncio
import json
from dataclasses import replace
from pathlib import Path

import httpx
import pytest

from calliope.comfyui import dry_run
from calliope.comfyui.client import ComfyUIClient, ComfyUIError
from calliope.queue.manager import QueueManager
from calliope.queue.worker import QueueWorker


@pytest.fixture
def workflow():
    return {
        "kind": "image",
        "prompt_node": "7",
        "prompt_input": "text",
        "workflow": {
            "7": {
                "class_type": "TestImageNode",
                "inputs": {
                    "text": "original prompt",
                    "filename_prefix": "original prefix",
                },
            }
        },
    }


NODE_INFO = {
    "TestImageNode": {
        "input": {
            "required": {
                "text": ["STRING"],
                "filename_prefix": ["STRING"],
            }
        }
    }
}


@pytest.mark.parametrize(
    ("kind", "output_key", "suffix"),
    [
        ("image", "images", ".png"),
        ("video", "gifs", ".mp4"),
    ],
)
def test_live_render_posts_graph_downloads_bytes_and_saves_traces(
    settings,
    workflow,
    mock_http,
    kind,
    output_key,
    suffix,
):
    settings = replace(settings, offline=False, comfyui_base_url="http://mock.invalid")
    workflow["kind"] = kind
    descriptor = {"filename": "generated" + suffix, "subfolder": "renders", "type": "output"}
    history = {
        "render-42": {
            "status": {"completed": True},
            "outputs": {"7": {output_key: [descriptor]}},
        }
    }
    raw_bytes, requests = b"\x00\xffgenerated-media\x80", []

    def respond(request):
        requests.append(request)
        if request.url.path.startswith("/object_info/"):
            return httpx.Response(200, json=NODE_INFO)
        if request.url.path == "/prompt":
            return httpx.Response(200, json={"prompt_id": "render-42", "node_errors": {}})
        if request.url.path == "/history/render-42":
            return httpx.Response(200, json=history)
        assert request.url.path == "/view" and dict(request.url.params) == descriptor
        return httpx.Response(
            200,
            content=raw_bytes,
            headers={
                "content-type": "image/png" if kind == "image" else "video/mp4",
            },
        )

    mock_http(respond)
    renderer = ComfyUIClient(settings)
    paths = asyncio.run(
        renderer.render(workflow, "New lantern scene", settings.assets_dir, job_id=23)
    )
    (output,) = map(Path, paths)
    assert output.read_bytes() == raw_bytes and output.suffix == suffix
    assert output.is_relative_to(settings.data_dir)
    assert [(request.method, request.url.path) for request in requests] == [
        ("GET", "/object_info/TestImageNode"),
        ("POST", "/prompt"),
        ("GET", "/history/render-42"),
        ("GET", "/view"),
    ]
    payload = json.loads(requests[1].content)
    inputs = payload["prompt"]["7"]["inputs"]
    assert payload["client_id"] and inputs["text"] == "New lantern scene"
    assert inputs["filename_prefix"].startswith("calliope-learning/comfyui-job-23-")
    assert workflow["workflow"]["7"]["inputs"]["text"] == "original prompt"
    traces = [json.loads(path.read_text()) for path in sorted(renderer.trace_dir.glob("*.json"))]
    assert next(trace["json"] for trace in traces if trace.get("method") == "POST") == payload
    assert history in [json.loads(trace["body"]) for trace in traces if "body" in trace]
    downloaded = traces[-1]
    assert downloaded["status_code"] == 200 and downloaded["bytes"] == len(raw_bytes)
    assert Path(downloaded["raw_body_path"]).read_bytes() == raw_bytes


@pytest.mark.parametrize(
    ("scenario", "error"),
    [
        ("node-errors", "rejected workflow nodes"),
        ("execution-error", "execution failed"),
        ("timeout", "timed out"),
        ("empty-outputs", "without downloadable image outputs"),
        ("empty-download", "empty media file"),
    ],
)
def test_live_render_errors_are_explicit_without_simulated_fallback(
    settings,
    workflow,
    mock_http,
    monkeypatch,
    scenario,
    error,
):
    settings = replace(
        settings,
        offline=False,
        comfyui_base_url="http://mock.invalid",
        render_timeout_sec=0.02,
        poll_interval_sec=1,
    )
    requests = []

    def respond(request):
        requests.append(request.url.path)
        if request.url.path.startswith("/object_info/"):
            return httpx.Response(200, json=NODE_INFO)
        if request.url.path == "/prompt":
            node_errors = {"7": {"errors": ["Invalid input"]}} if scenario == "node-errors" else {}
            return httpx.Response(200, json={"prompt_id": "render-42", "node_errors": node_errors})
        if request.url.path == "/history/render-42":
            if scenario == "timeout":
                return httpx.Response(200, json={})
            status = {"completed": True}
            if scenario == "execution-error":
                status["messages"] = [["execution_error", {"exception_message": "Broken node"}]]
            outputs = (
                {}
                if scenario == "empty-outputs"
                else {
                    "7": {"images": [{"filename": "result.png"}]},
                }
            )
            return httpx.Response(200, json={"render-42": {"status": status, "outputs": outputs}})
        assert request.url.path == "/view" and scenario == "empty-download"
        return httpx.Response(200, content=b"")

    mock_http(respond)
    monkeypatch.setattr(dry_run, "render", lambda *args: pytest.fail("Simulated fallback was used"))
    renderer = ComfyUIClient(settings)
    with pytest.raises(ComfyUIError, match=error) as failure:
        asyncio.run(renderer.render(workflow, "Lantern scene", settings.assets_dir))
    assert "Raw ComfyUI trace:" in str(failure.value)
    assert list(renderer.trace_dir.glob("*-response.json"))
    assert list(settings.assets_dir.iterdir()) == []
    assert ("/view" in requests) == (scenario == "empty-download")
    if scenario == "node-errors":
        assert "/history/render-42" not in requests


@pytest.mark.parametrize("offline", [True, False])
@pytest.mark.parametrize("kind", ["image", "video", "export"])
def test_job_mode_mismatch_fails_before_render_or_export(
    settings, project, workflow, offline, kind
):
    settings = replace(settings, offline=offline)
    manager = QueueManager(settings)
    job = manager.enqueue(
        project,
        kind,
        {
            "mode": "live" if offline else "simulated",
            "prompt": "Do not contact a server",
            "workflow": workflow,
        },
    )
    result = asyncio.run(QueueWorker(settings).run_next())
    assert result["id"] == job["id"] and result["status"] == "failed"
    assert "cannot run in" in result["error"] and result["output_paths"] == []
    assert manager.get_job(job["id"])["status"] == "failed"
    assert not (settings.data_dir / "traces").exists()
    assert list(settings.assets_dir.iterdir()) == []
