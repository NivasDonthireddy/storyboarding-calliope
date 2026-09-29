from calliope.agent.coverage_agent import expand_scene_coverage
from calliope.agent.harness.plugins.story import EmptyArgs
from calliope.agent.harness.registry import ToolContext, ToolDefinition, ToolRegistry
from calliope.agent.script_agent import generate_script
from calliope.routers.scenes import list_scenes


async def t_list_scenes(ctx: ToolContext, args: dict) -> dict:
    return list_scenes(ctx.settings, ctx.project_id)


async def t_generate_script(ctx: ToolContext, args: dict) -> dict:
    return await generate_script(ctx.settings, ctx.project_id)


async def t_break_into_shots(ctx: ToolContext, args: dict) -> dict:
    return await expand_scene_coverage(ctx.settings, ctx.project_id)


def register(registry: ToolRegistry) -> None:
    registry.register(
        ToolDefinition(
            "list_scenes",
            "Read the saved scenes and their clips.",
            EmptyArgs,
            t_list_scenes,
        )
    )
    registry.register(
        ToolDefinition(
            "generate_script",
            "Write scenes from saved story, then expand shot coverage. "
            "Requires a story and an empty script.",
            EmptyArgs,
            t_generate_script,
        )
    )
    registry.register(
        ToolDefinition(
            "break_into_shots",
            "Replace clip plans from scenes, before creating any jobs.",
            EmptyArgs,
            t_break_into_shots,
        )
    )
