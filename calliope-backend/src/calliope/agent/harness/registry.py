from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from fastapi import HTTPException
from pydantic import BaseModel, ValidationError

from calliope.agent.llm import ModelOutputError
from calliope.config import Settings


@dataclass
class ToolContext:
    settings: Settings
    project_id: int
    session_id: int
    allow_render: bool = False


@dataclass
class ToolDefinition:
    name: str
    description: str
    arguments: type[BaseModel]
    executor: Callable[[ToolContext, dict], Awaitable[dict]]
    requires_approval: bool = False


class ToolRegistry:
    def __init__(self):
        self.tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        if tool.name in self.tools:
            raise ValueError(f"Duplicate tool: {tool.name}")
        self.tools[tool.name] = tool

    def openai_payload(self, allowed: set[str]) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.arguments.model_json_schema(),
                },
            }
            for tool in self.tools.values()
            if tool.name in allowed
        ]

    async def execute(self, ctx: ToolContext, name: str, args: dict, allowed: set[str]) -> dict:
        tool = self.tools.get(name)
        if tool is None or name not in allowed:
            return {"ok": False, "error": f"Unknown or unavailable tool: {name}"}
        if tool.requires_approval and not ctx.allow_render:
            return {"ok": False, "error": "Rendering requires allow_render=true from the user."}
        try:
            validated = tool.arguments.model_validate(args)
            data = await tool.executor(ctx, validated.model_dump())
            return {"ok": True, "data": data}
        except HTTPException as exc:
            return {"ok": False, "error": str(exc.detail), "status_code": exc.status_code}
        except (ValidationError, ModelOutputError, ValueError) as exc:
            return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
