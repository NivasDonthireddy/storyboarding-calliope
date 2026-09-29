import json

from calliope.agent.harness.log import append_event
from calliope.agent.harness.registry import ToolContext, ToolRegistry
from calliope.agent.llm import LLMClient, ModelOutputError


async def run_turn(
    ctx: ToolContext,
    registry: ToolRegistry,
    history: list[dict],
    *,
    allowed: set[str],
    scenario: str = "normal",
    max_steps: int = 6,
    agent_name: str = "main",
) -> dict:
    client = LLMClient(ctx.settings, scenario)
    messages = [
        {
            "role": "system",
            "content": (
                f"You are Calliope's {agent_name} assistant for project {ctx.project_id}. "
                "Use tools to actually read and change saved data. Never invent IDs or claim a "
                "write happened without a successful tool result. Do only the user's request. "
                "Read story before generating a script. Do not regenerate existing content. "
                "When the goal is done, reply briefly without tools. If blocked, explain why. "
                f"Render approval: {ctx.allow_render}. You may queue jobs if approved, but "
                "cannot run the worker. Keep tool arguments small."
            ),
        },
        *history,
    ]
    failed = False
    for step in range(1, max_steps + 1):
        append_event(ctx.settings, ctx.session_id, "step", {"step": step, "agent": agent_name})
        response = await client.chat(messages, registry.openai_payload(allowed))
        calls = response.get("tool_calls") or []
        if not isinstance(calls, list):
            raise ModelOutputError("tool_calls must be an array.")
        messages.append(response)
        append_event(
            ctx.settings,
            ctx.session_id,
            "message",
            {
                "agent": agent_name,
                "message": response,
            },
        )
        if not calls:
            return {
                "status": "error" if failed else "completed",
                "answer": response.get("content") or "",
                "steps": step,
            }
        for call in calls:
            if not isinstance(call, dict) or not call.get("id"):
                raise ModelOutputError("Tool request missing its call ID.")
            function = call.get("function")
            if not isinstance(function, dict) or not isinstance(function.get("name"), str):
                raise ModelOutputError("Tool request missing its function name.")
            name = function["name"]
            raw_args = function.get("arguments", "{}")
            try:
                if not isinstance(raw_args, str):
                    raise ValueError("Tool arguments must be a JSON string.")
                args = json.loads(raw_args)
                if not isinstance(args, dict):
                    raise ValueError("Tool arguments must decode to an object.")
                result = await registry.execute(ctx, name, args, allowed)
            except (json.JSONDecodeError, ValueError) as exc:
                result = {"ok": False, "error": str(exc)}
            failed = not result["ok"]
            append_event(
                ctx.settings,
                ctx.session_id,
                "tool_result",
                {
                    "agent": agent_name,
                    "call_id": call["id"],
                    "tool": name,
                    "result": result,
                },
            )
            observation = {
                "role": "tool",
                "tool_call_id": call["id"],
                "content": json.dumps(result),
            }
            messages.append(observation)
            append_event(
                ctx.settings,
                ctx.session_id,
                "message",
                {
                    "agent": agent_name,
                    "message": observation,
                },
            )
    return {
        "status": "step_limit",
        "answer": "Stopped at the model-step budget.",
        "steps": max_steps,
    }
