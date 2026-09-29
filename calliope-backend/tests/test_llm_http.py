import asyncio
import json
from dataclasses import replace

import httpx
import pytest
from pydantic import ValidationError

from calliope.agent.harness import build_harness
from calliope.agent.llm import LLMClient, ModelOutputError, generate_structured
from calliope.models.schemas import CoverageDraft, ScriptDraft, StoryDraft


def test_health_reports_configured_model_and_server(client, settings):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["model"] == settings.llm_model
    assert response.json()["llm_url"] == settings.llm_base_url


@pytest.mark.parametrize("model", [None, "custom-model"])
@pytest.mark.parametrize("base_url", [None, "http://mock.invalid/v1/"])
def test_live_chat_posts_tool_schema_and_saves_raw_trace(settings, mock_http, model, base_url):
    settings = replace(settings, offline=False)
    if base_url is not None:
        settings = replace(settings, llm_base_url=base_url)
    if model is not None:
        settings = replace(settings, llm_model=model)
    harness = build_harness()
    tools = harness.openai_payload({"get_story", "update_beat"})
    messages = [{"role": "user", "content": "Read the saved story"}]
    reply = {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": "real-call-id",
                "type": "function",
                "function": {"name": "get_story", "arguments": "{}"},
            }
        ],
        "reasoning_content": "Raw reasoning stays in the trace.",
    }
    raw = {"choices": [{"message": reply}], "usage": {"total_tokens": 12}}
    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(200, json=raw)

    mock_http(respond)
    result = asyncio.run(LLMClient(settings).chat(messages, tools))
    expected_url = settings.llm_base_url.rstrip("/") + "/chat/completions"
    assert len(requests) == 1 and str(requests[0].url) == expected_url
    payload = json.loads(requests[0].content)
    assert payload["messages"] == messages
    assert payload["model"] == settings.llm_model
    assert payload["tools"] == tools and payload["tool_choice"] == "auto"
    assert "response_format" not in payload
    assert not payload["stream"] and tools[1]["function"]["parameters"]["required"] == [
        "beat_id",
        "title",
    ]
    assert result == {key: reply[key] for key in ("role", "content", "tool_calls")}
    (trace,) = (settings.data_dir / "traces").glob("llm-*.json")
    saved = json.loads(trace.read_text())
    assert saved["request"] == payload and saved["response"] == raw
    assert saved["status_code"] == 200 and json.loads(saved["response_text"]) == raw


def test_live_generation_posts_each_schema_and_saves_response_format(
    client, settings, project, mock_http
):
    client.app.state.settings = replace(settings, offline=False, llm_base_url="http://mock.invalid/v1")
    offline_model = LLMClient(settings)
    schemas = {"story": StoryDraft, "script": ScriptDraft, "coverage": CoverageDraft}
    tasks = []

    def respond(request):
        payload = json.loads(request.content)
        task_input = json.loads(payload["messages"][-1]["content"])
        task = task_input["task"]
        schema = schemas[task]
        assert payload["response_format"] == {
            "type": "json_schema",
            "json_schema": {
                "name": schema.__name__,
                "strict": True,
                "schema": schema.model_json_schema(),
            },
        }
        assert payload["temperature"] == 0.3 and "seed" not in payload
        assert "tools" not in payload and "tool_choice" not in payload
        tasks.append(task)
        content = json.dumps(offline_model._draft(task_input))
        return httpx.Response(
            200, json={"choices": [{"message": {"role": "assistant", "content": content}}]}
        )

    mock_http(respond)
    url = f"/api/projects/{project}"
    for operation, body in [
        ("generate-story", {}),
        ("generate-script", {"with_clips": False}),
        ("expand-clips", {}),
    ]:
        response = client.post(url + "/" + operation, json=body)
        assert response.status_code == 200, response.text
    assert tasks == ["story", "script", "script", *(["coverage"] * 4)]
    traces = list((settings.data_dir / "traces").glob("llm-*.json"))
    assert len(traces) == len(tasks)
    for trace in traces:
        saved = json.loads(trace.read_text())
        task = json.loads(saved["request"]["messages"][-1]["content"])["task"]
        assert saved["request"]["response_format"]["json_schema"]["schema"] == (
            schemas[task].model_json_schema()
        )


@pytest.mark.parametrize("schema", [StoryDraft, ScriptDraft, CoverageDraft])
@pytest.mark.parametrize(
    ("content", "cause"),
    [
        ("not JSON", json.JSONDecodeError),
        ("```json\n{}\n```", json.JSONDecodeError),
        ('{"unexpected": true}', ValidationError),
    ],
)
def test_structured_generation_still_rejects_invalid_output(
    settings, mock_http, schema, content, cause
):
    settings = replace(settings, offline=False, llm_base_url="http://mock.invalid/v1")
    mock_http(
        lambda request: httpx.Response(
            200, json={"choices": [{"message": {"role": "assistant", "content": content}}]}
        )
    )
    with pytest.raises(ModelOutputError, match="Generated output rejected") as error:
        asyncio.run(
            generate_structured(settings, [{"role": "system", "content": "Draft a story."}], schema)
        )
    assert isinstance(error.value.__cause__, cause)


@pytest.mark.parametrize(
    ("status", "body", "error"),
    [
        (503, '{"error":"unavailable"}', "Model request failed"),
        (200, "not JSON", "Model request failed"),
        (200, '{"choices":[]}', "Missing choices"),
        (200, '{"choices":[{}]}', "Missing assistant message"),
        (200, '{"choices":[{"message":{"role":"assistant","content":""}}]}', "Empty model answer"),
    ],
)
def test_live_errors_are_explicit_and_never_use_offline_fallback(
    settings, mock_http, monkeypatch, status, body, error
):
    settings = replace(settings, offline=False, llm_base_url="http://mock.invalid/v1")
    mock_http(lambda request: httpx.Response(status, text=body))
    monkeypatch.setattr(LLMClient, "_draft", lambda *args: pytest.fail("Offline fallback was used"))
    with pytest.raises(ModelOutputError, match=error):
        asyncio.run(LLMClient(settings).chat([{"role": "user", "content": "{}"}]))
    (trace,) = (settings.data_dir / "traces").glob("llm-*.json")
    assert json.loads(trace.read_text())["response_text"] == body
