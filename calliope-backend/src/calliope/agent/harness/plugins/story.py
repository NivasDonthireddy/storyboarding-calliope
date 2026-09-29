from pydantic import Field

from calliope.agent.harness.registry import ToolContext, ToolDefinition, ToolRegistry
from calliope.models.schemas import StrictModel
from calliope.routers.story import generate_story, get_story, update_beat


class EmptyArgs(StrictModel):
    pass


class UpdateBeatArgs(StrictModel):
    beat_id: int = Field(ge=1)
    title: str = Field(min_length=1)


async def t_get_story(ctx: ToolContext, args: dict) -> dict:
    return get_story(ctx.settings, ctx.project_id)


async def t_generate_story(ctx: ToolContext, args: dict) -> dict:
    return await generate_story(ctx.settings, ctx.project_id)


async def t_update_beat(ctx: ToolContext, args: dict) -> dict:
    return update_beat(ctx.settings, ctx.project_id, args["beat_id"], args["title"])


def register(registry: ToolRegistry) -> None:
    registry.register(
        ToolDefinition(
            "get_story",
            "Read saved story, characters, locations, and real IDs.",
            EmptyArgs,
            t_get_story,
        )
    )
    registry.register(
        ToolDefinition(
            "generate_story",
            "Generate four beats and cast. Only for a project without a story.",
            EmptyArgs,
            t_generate_story,
        )
    )
    registry.register(
        ToolDefinition(
            "update_beat",
            "Rename one beat using its real database ID from get_story.",
            UpdateBeatArgs,
            t_update_beat,
        )
    )
