"""The real model boundary, with an explicitly selected offline teaching mode."""

import json
import logging
from typing import TypeVar
from uuid import uuid4

import httpx
from pydantic import BaseModel, ValidationError

from calliope.config import Settings

Draft = TypeVar("Draft", bound=BaseModel)
logger = logging.getLogger("mini.model")


class ModelOutputError(ValueError):
    pass


class LLMClient:
    def __init__(self, settings: Settings, scenario: str = "normal"):
        self.settings = settings
        self.scenario = scenario

    async def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        *,
        response_format: dict | None = None,
    ) -> dict:
        if not self.settings.offline:
            if self.scenario != "normal":
                raise ModelOutputError("Failure scenarios require --offline; no request was sent.")
            return await self._live_chat(messages, tools, response_format=response_format)
        logger.info("MODEL input: %s", json.dumps(messages))
        if tools is not None:
            reply = self._tool_reply(messages)
        else:
            request = json.loads(messages[-1]["content"])
            content = json.dumps(self._draft(request))
            if self.scenario == "invalid-json":
                content = "This is not JSON."
            elif self.scenario == "invalid-data":
                content = '{"beats": "four"}'
            reply = {"role": "assistant", "content": content}
        logger.info("MODEL output: %s", json.dumps(reply))
        return reply

    async def _live_chat(
        self,
        messages: list[dict],
        tools: list[dict] | None,
        *,
        response_format: dict | None = None,
    ) -> dict:
        payload = {
            "model": self.settings.llm_model,
            "messages": messages,
            "temperature": 0.3,
            "stream": False,
            "max_tokens": 4096,
            "chat_template_kwargs": {"enable_thinking": False},
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        if response_format is not None:
            payload["response_format"] = response_format
        trace_dir = self.settings.data_dir / "traces"
        trace_dir.mkdir(parents=True, exist_ok=True)
        trace_path = trace_dir / f"llm-{uuid4().hex}.json"
        trace = {
            "url": self.settings.llm_base_url.rstrip("/") + "/chat/completions",
            "request": payload,
        }
        trace_path.write_text(json.dumps(trace, indent=2), encoding="utf-8")
        logger.info("LLM request/response trace: %s", trace_path)
        try:
            async with httpx.AsyncClient(
                timeout=self.settings.request_timeout_sec,
                trust_env=False,
            ) as client:
                response = await client.post(trace["url"], json=payload)
            trace["status_code"] = response.status_code
            trace["response_text"] = response.text
            response.raise_for_status()
            body = response.json()
            trace["response"] = body
            choices = body.get("choices") if isinstance(body, dict) else None
            if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
                raise ModelOutputError(f"Missing choices in model response; see {trace_path}")
            message = choices[0].get("message")
            if not isinstance(message, dict):
                raise ModelOutputError(f"Missing assistant message; see {trace_path}")
            if not message.get("content") and not message.get("tool_calls"):
                raise ModelOutputError(f"Empty model answer; see {trace_path}")
            # Keep protocol fields only; raw reasoning/usage remains in the trace.
            return {
                key: message[key] for key in ("role", "content", "tool_calls") if key in message
            }
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            trace["error"] = f"{type(exc).__name__}: {exc}"
            raise ModelOutputError(f"Model request failed; see {trace_path}: {exc}") from exc
        finally:
            trace_path.write_text(json.dumps(trace, indent=2), encoding="utf-8")

    def _draft(self, request: dict) -> dict:
        if request["task"] == "story":
            titles = ["Into the station", "A voice in the dark", "The flame fades", "The exit"]
            descriptions = [
                "Mira enters the flooded station carrying a brass lantern.",
                "A stranger calls from the far platform. Mira raises the light.",
                "Mira shields the fading flame as they cross the water.",
                "Mira and the stranger reach the exit together.",
            ]
            return {
                "logline": request["project"]["idea"],
                "beats": [
                    {"order_index": i, "title": title, "description": description}
                    for i, (title, description) in enumerate(zip(titles, descriptions), 1)
                ],
                "characters": [
                    {"name": "Mira", "appearance": "Yellow raincoat, dark braid"},
                    {"name": "Stranger", "appearance": "Gray coat"},
                ],
                "locations": [{"name": "Flooded station", "description": "Water and amber light"}],
            }
        if request["task"] == "script":
            story = request["story"]
            start = request["start"] - 1
            return {
                "scenes": [
                    {
                        "order_index": beat["order_index"],
                        "heading": "INT. FLOODED STATION - NIGHT",
                        "action": beat["description"],
                        "dialog": "STRANGER: Over here!\nMIRA: Follow the light.",
                        "duration_sec": 8,
                        "character_ids": [character["id"] for character in story["characters"]],
                        "location_id": story["locations"][0]["id"],
                    }
                    for beat in story["beats"][start : start + request["count"]]
                ]
            }
        if request["task"] == "coverage":
            scene = request["scene"]
            lines = [line for line in scene["dialog"].splitlines() if line.strip()]
            return {
                "clips": [
                    {
                        "description": "Wide shot. " + scene["action"],
                        "dialog_lines_covered": list(range(1, len(lines) + 1, 2)),
                        "duration_sec": 4,
                    },
                    {
                        "description": "Close shot of Mira holding the lantern.",
                        "dialog_lines_covered": list(range(2, len(lines) + 1, 2)),
                        "duration_sec": 4,
                    },
                ]
            }
        raise ValueError(f"Unknown fake-model task: {request['task']}")

    def _tool_reply(self, messages: list[dict]) -> dict:
        user_index = max(i for i, message in enumerate(messages) if message["role"] == "user")
        turn = messages[user_index:]
        goal = turn[0]["content"].strip()
        results = [json.loads(message["content"]) for message in turn if message["role"] == "tool"]
        call_id = f"call_{len(messages)}"

        def call(name: str, arguments: dict) -> dict:
            return {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": call_id,
                        "type": "function",
                        "function": {"name": name, "arguments": json.dumps(arguments)},
                    }
                ],
            }

        if self.scenario == "loop":
            return call("get_story", {})
        if not results:
            if self.scenario == "unknown-tool":
                return call("invented_tool", {})
            if self.scenario == "bad-arguments":
                return call("update_beat", {"beat_id": "not-an-integer", "title": "Oops"})
            if goal.lower() == "queue videos":
                return call("enqueue_video_jobs", {})
            if goal.lower() == "show story":
                return call("get_story", {})
            if goal.lower() in ("draft story", "write script") or goal.lower().startswith(
                "rename opening beat to "
            ):
                return call("get_story", {})
            return {
                "role": "assistant",
                "content": (
                    "This is a scripted model, not natural-language AI. Try: draft story, "
                    "write script, show story, rename opening beat to TITLE, or queue videos."
                ),
            }
        if not results[-1]["ok"]:
            return {"role": "assistant", "content": "Tool failed: " + results[-1]["error"]}
        if len(results) == 1 and goal.lower() == "draft story":
            if not results[0]["data"]["beats"]:
                return call("generate_story", {})
        if len(results) == 1 and goal.lower() == "write script":
            return call("generate_script", {})
        if len(results) == 1 and goal.lower().startswith("rename opening beat to "):
            beats = results[0]["data"]["beats"]
            if not beats:
                return {"role": "assistant", "content": "No beat to rename; draft a story first."}
            return call(
                "update_beat",
                {
                    "beat_id": beats[0]["id"],
                    "title": goal[len("rename opening beat to ") :],
                },
            )
        return {"role": "assistant", "content": "Observed saved result: " + json.dumps(results[-1])}


async def generate_structured(
    settings: Settings,
    messages: list[dict],
    schema: type[Draft],
    scenario: str = "normal",
) -> Draft:
    json_schema = schema.model_json_schema()
    schema_instruction = (
        "\nReturn ONLY a JSON object, no markdown or explanation, matching this JSON Schema:\n"
        + json.dumps(json_schema)
    )
    messages = [
        {**messages[0], "content": messages[0]["content"] + schema_instruction},
        *messages[1:],
    ]
    response = await LLMClient(settings, scenario).chat(
        messages,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": schema.__name__,
                "strict": True,
                "schema": json_schema,
            },
        },
    )
    content = response.get("content")
    if not isinstance(content, str):
        raise ModelOutputError("Expected JSON answer text, not a tool call.")
    try:
        candidate = json.loads(content)
        return schema.model_validate(candidate)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise ModelOutputError(f"Generated output rejected: {exc}") from exc
