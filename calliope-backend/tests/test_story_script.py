import json

import pytest
from fastapi.testclient import TestClient

from calliope.agent import script_agent
from calliope.db import get_db
from calliope.main import create_app


@pytest.mark.parametrize("title", ["", "   "])
def test_blank_title_is_rejected(client, title):
    assert client.post("/api/projects", json={"title": title, "idea": "Exit"}).status_code == 422


@pytest.mark.parametrize("suffix", ["", "/story", "/scenes"])
def test_missing_project_is_404(client, suffix):
    assert client.get(f"/api/projects/999{suffix}").status_code == 404


def test_projects_survive_app_recreation(client, settings, project):
    saved = client.get(f"/api/projects/{project}").json()
    assert settings.db_path.is_file()
    with TestClient(create_app(settings)) as reopened:
        assert reopened.get("/api/projects").json() == [saved]
        assert reopened.get("/api/health").json()["database"] == str(settings.db_path)


def test_story_is_persisted_once(client, project):
    url = f"/api/projects/{project}"
    story = client.post(url + "/generate-story", json={}).json()
    assert [beat["order_index"] for beat in story["beats"]] == [1, 2, 3, 4]
    assert story["characters"] and story["locations"]
    assert client.get(url + "/story").json() == story
    assert client.post(url + "/generate-story", json={}).status_code == 409


@pytest.mark.parametrize("scenario", ["invalid-json", "invalid-data"])
@pytest.mark.parametrize("operation", ["generate-story", "generate-script", "expand-clips"])
def test_bad_model_output_is_502_without_writes(client, settings, project, scenario, operation):
    url = f"/api/projects/{project}"
    if operation != "generate-story":
        assert client.post(url + "/generate-story", json={}).status_code == 200
    if operation == "expand-clips":
        assert client.post(url + "/generate-script", json={"with_clips": False}).status_code == 200
    with get_db(settings.db_path) as db:
        before = list(db.iterdump())
    response = client.post(url + "/" + operation, json={"scenario": scenario})
    assert response.status_code == 502
    assert "Generated output rejected" in response.json()["detail"]
    with get_db(settings.db_path) as db:
        assert list(db.iterdump()) == before


@pytest.mark.parametrize("with_clips", [False, True])
def test_script_chunks_links_coverage_and_read_order(
    client, settings, project, monkeypatch, with_clips
):
    url = f"/api/projects/{project}"
    assert client.post(url + "/generate-script", json={}).status_code == 409
    story = client.post(url + "/generate-story", json={}).json()
    generate, chunks = script_agent.generate_structured, []

    async def observe_chunks(*args):
        request = json.loads(args[1][-1]["content"])
        with get_db(settings.db_path) as db:
            chunks.append(
                (
                    request["start"],
                    len(request["previous_tail"]),
                    db.execute("SELECT COUNT(*) FROM scenes").fetchone()[0],
                )
            )
        return await generate(*args)

    monkeypatch.setattr(script_agent, "generate_structured", observe_chunks)
    result = client.post(url + "/generate-script", json={"with_clips": with_clips}).json()
    assert result["scene_count"] == 4 and chunks == [(1, 0, 0), (3, 2, 2)]
    scenes = client.get(url + "/scenes").json()["scenes"]
    assert [scene["id"] for scene in scenes] == result["scene_ids"]
    for scene in scenes:
        assert scene["location_id"] in {location["id"] for location in story["locations"]}
        assert set(scene["character_ids"]) == {character["id"] for character in story["characters"]}
        assert len(scene["clips"]) == (2 if with_clips else 1)
        assert all(
            clip["clip_path"] is None
            and clip["scene_id"] == scene["id"]
            and clip["project_id"] == project
            for clip in scene["clips"]
        )
    assert client.post(url + "/generate-script", json={}).status_code == 409
    coverage = client.post(url + "/expand-clips", json={}).json()
    assert coverage == {"scene_count": 4, "clip_count": 8}
    for scene in client.get(url + "/scenes").json()["scenes"]:
        covered = [line for clip in scene["clips"] for line in clip["dialog_lines_covered"]]
        assert sorted(covered) == list(range(1, len(scene["dialog"].splitlines()) + 1))
    with get_db(settings.db_path) as db:
        db.execute("UPDATE scenes SET order_index = 5 - order_index")
    assert [s["id"] for s in client.get(url + "/scenes").json()["scenes"]] == result["scene_ids"][
        ::-1
    ]
