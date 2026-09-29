import json

import pytest

from calliope.agent.llm import LLMClient, ModelOutputError


def start_session(client, project):
    response = client.post("/api/agent/sessions", json={"project_id": project})
    assert response.status_code == 200
    return f"/api/agent/sessions/{response.json()['id']}"


def test_agent_reads_actual_ids_before_rename_and_pairs_tool_results(client, project):
    first_story = client.post(f"/api/projects/{project}/generate-story", json={}).json()
    other = client.post("/api/projects", json={"title": "Other", "idea": "New exit"}).json()["id"]
    session = start_session(client, other)
    for content in ("draft story", "rename opening beat to A fresh opening"):
        result = client.post(session + "/messages", json={"content": content})
        assert result.status_code == 200 and result.json()["status"] == "completed"
    story = client.get(f"/api/projects/{other}/story").json()
    beat = story["beats"][0]
    assert other > 1 and beat["id"] > 1 and beat["title"] == "A fresh opening"
    events = client.get(session).json()["events"]
    messages = [event["data"]["message"] for event in events if event["type"] == "message"]
    calls = [call for message in messages for call in message.get("tool_calls", [])]
    assert [call["function"]["name"] for call in calls] == [
        "get_story",
        "generate_story",
        "get_story",
        "update_beat",
    ]
    assert json.loads(calls[-1]["function"]["arguments"])["beat_id"] == beat["id"]
    results = {
        event["data"]["call_id"]: event["data"]["result"]
        for event in events
        if event["type"] == "tool_result"
    }
    observations = {
        message["tool_call_id"]: json.loads(message["content"])
        for message in messages
        if message["role"] == "tool"
    }
    assert set(results) == {call["id"] for call in calls} and results == observations
    assert all(result["ok"] for result in results.values())
    response = client.patch(f"/api/projects/{project}/beats/{beat['id']}", json={"title": "Wrong"})
    assert response.status_code == 404
    assert client.get(f"/api/projects/{project}/story").json() == first_story
    assert client.get(f"/api/projects/{other}/story").json() == story


@pytest.mark.parametrize(
    ("scenario", "content", "error"),
    [
        ("unknown-tool", "draft story", "Unknown or unavailable tool"),
        ("bad-arguments", "draft story", "ValidationError"),
        ("normal", "queue videos", "allow_render=true"),
    ],
)
def test_agent_tool_errors_and_unapproved_render_do_not_write(
    client, project, scenario, content, error
):
    session = start_session(client, project)
    result = client.post(session + "/messages", json={"content": content, "scenario": scenario})
    assert result.status_code == 200 and result.json()["status"] == "error"
    state = client.get(session).json()
    assert state["status"] == "error"
    errors = [e["data"]["result"] for e in state["events"] if e["type"] == "tool_result"]
    assert len(errors) == 1 and not errors[0]["ok"] and error in errors[0]["error"]
    assert client.get(f"/api/projects/{project}/story").json()["beats"] == []
    assert client.get("/api/jobs", params={"project_id": project}).json() == []


def test_agent_repeated_reads_stop_at_step_budget(client, project):
    session = start_session(client, project)
    response = client.post(
        session + "/messages",
        json={
            "content": "show story",
            "scenario": "loop",
            "max_steps": 3,
        },
    )
    assert response.json()["status"] == "step_limit" and response.json()["steps"] == 3
    state = client.get(session).json()
    assert state["status"] == "step_limit"
    assert len([e for e in state["events"] if e["type"] == "tool_result"]) == 3


def test_model_failure_releases_running_session(client, project, monkeypatch):
    async def fail(*args, **kwargs):
        raise ModelOutputError("broken model")

    monkeypatch.setattr(LLMClient, "chat", fail)
    session = start_session(client, project)
    assert client.post(session + "/messages", json={"content": "show story"}).status_code == 502
    state = client.get(session).json()
    assert state["status"] == "error"
    assert state["events"][-1]["type"] == "turn_end"
