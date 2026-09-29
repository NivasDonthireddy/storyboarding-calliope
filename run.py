"""Run from the IDE or terminal; always import this mini project, never production."""

import argparse
import json
import logging
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent / "calliope-backend"
SOURCE = BACKEND / "src"
sys.path.insert(0, str(SOURCE))

import calliope  # noqa: E402

if not Path(calliope.__file__).resolve().is_relative_to(SOURCE):
    raise RuntimeError("Wrong calliope package loaded. Start run.py in a fresh Python process.")


def show(stage: str, value) -> None:
    print(f"\n=== {stage} ===\n{json.dumps(value, indent=2)}", flush=True)


def request(client, method: str, path: str, body: dict | None = None):
    response = client.request(method, path, json=body)
    if response.is_error:
        raise RuntimeError(f"{method} {path}: {response.status_code}\n{response.text}")
    return response.json()


def run_worker(client) -> None:
    result = request(client, "POST", "/api/jobs/run-next", {})
    show("Worker result", result)
    if result["status"] == "failed":
        raise RuntimeError(f"Render job {result['id']} failed: {result['error']}")


def run_demo(settings, args) -> None:
    from fastapi.testclient import TestClient

    from calliope.main import create_app

    with TestClient(create_app(settings)) as client:
        project = request(
            client,
            "POST",
            "/api/projects",
            {
                "title": "The Last Lantern",
                "idea": (
                    "Mira guides a stranger through a flooded station before her lantern goes out."
                ),
                "tone": "Tense, then hopeful",
            },
        )
        pid = project["id"]
        show("1. Saved project (no model call)", project)
        if args.command == "agent":
            session = request(client, "POST", "/api/agent/sessions", {"project_id": pid})
            show("Session", session)
            result = request(
                client,
                "POST",
                f"/api/agent/sessions/{session['id']}/messages",
                {
                    "content": args.goal,
                    "scenario": args.scenario,
                    "allow_render": args.allow_render,
                    "max_steps": args.max_steps,
                },
            )
            show("Agent result", result)
            show(
                "Saved event trace",
                request(
                    client,
                    "GET",
                    f"/api/agent/sessions/{session['id']}",
                ),
            )
            return
        if args.until == "project":
            return
        story = request(
            client,
            "POST",
            f"/api/projects/{pid}/generate-story",
            {
                "scenario": args.scenario,
            },
        )
        show("2. Saved story (model -> schema -> SQLite)", story)
        if args.until == "story":
            return
        request(client, "POST", f"/api/projects/{pid}/generate-script", {"with_clips": False})
        show("3. Scenes with default clips", request(client, "GET", f"/api/projects/{pid}/scenes"))
        if args.until == "script":
            return
        request(client, "POST", f"/api/projects/{pid}/expand-clips", {})
        board = request(client, "GET", f"/api/projects/{pid}/scenes")
        show("4. Shot coverage (not rendered)", board)
        if args.until == "coverage":
            return
        jobs = request(
            client,
            "POST",
            f"/api/projects/{pid}/generate-assets",
            {
                "character_ids": [story["characters"][0]["id"]],
                "location_ids": [],
                "workflow_name": "image",
            },
        )
        show("5. Image jobs (queued only)", jobs)
        run_worker(client)
        if args.until == "assets":
            return
        clip_id = board["scenes"][0]["clips"][0]["id"]
        show(
            "6. One video job",
            request(
                client,
                "POST",
                f"/api/jobs/projects/{pid}/generate-videos",
                {"clip_ids": [clip_id], "workflow_name": "video"},
            ),
        )
        run_worker(client)
        if args.until == "video":
            return
        show(
            "7. Export manifest job",
            request(client, "POST", f"/api/jobs/projects/{pid}/export", {}),
        )
        run_worker(client)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["serve", "demo", "agent"])
    parser.add_argument("--offline", action="store_true", help="Use fake model and sample media.")
    parser.add_argument("--data-dir", type=Path, help="Separate playground storage directory.")
    parser.add_argument("--port", type=int, default=8010)
    parser.add_argument("--model", help="Override the llama model alias.")
    parser.add_argument(
        "--until",
        default="coverage",
        choices=[
            "project",
            "story",
            "script",
            "coverage",
            "assets",
            "video",
            "export",
        ],
    )
    parser.add_argument("--goal", default="build story and script")
    parser.add_argument(
        "--scenario",
        default="normal",
        choices=[
            "normal",
            "invalid-json",
            "invalid-data",
            "unknown-tool",
            "bad-arguments",
            "loop",
        ],
    )
    parser.add_argument("--allow-render", action="store_true")
    parser.add_argument("--max-steps", type=int, default=6)
    args = parser.parse_args()
    if args.scenario != "normal" and not args.offline:
        parser.error("--scenario requires --offline")
    if args.command == "agent" and args.scenario in ("invalid-json", "invalid-data"):
        parser.error("Use demo for generation-output failure scenarios.")
    if args.command == "demo" and args.scenario in ("unknown-tool", "bad-arguments", "loop"):
        parser.error("Use agent for tool-loop failure scenarios.")
    if not 1 <= args.max_steps <= 20:
        parser.error("--max-steps must be between 1 and 20")
    from calliope.config import Settings

    storage = args.data_dir or BACKEND / "data" / ("offline" if args.offline else "live")
    options = {"data_dir": storage.resolve(), "offline": args.offline}
    if args.model:
        options["llm_model"] = args.model
    settings = Settings(**options)
    logging.basicConfig(level=logging.INFO, format="%(name)s | %(message)s")
    show("Mode", {"offline": settings.offline, "database": str(settings.db_path)})
    if args.command == "serve":
        import uvicorn

        from calliope.main import create_app

        uvicorn.run(create_app(settings), host="127.0.0.1", port=args.port)
    else:
        run_demo(settings, args)


if __name__ == "__main__":
    main()
