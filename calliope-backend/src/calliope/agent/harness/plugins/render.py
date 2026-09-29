from calliope.agent.harness.registry import ToolContext, ToolDefinition, ToolRegistry
from calliope.models.schemas import StrictModel


class RenderArgs(StrictModel):
    workflow_name: str = "video"
    clip_ids: list[int] | None = None


async def t_enqueue_video_jobs(ctx: ToolContext, args: dict) -> dict:
    from calliope.agent.video_agent import enqueue_video_jobs

    jobs = await enqueue_video_jobs(ctx.settings, ctx.project_id, **args)
    return {"jobs": jobs, "note": "Queued only. Run the worker separately to render."}


def register(registry: ToolRegistry) -> None:
    registry.register(
        ToolDefinition(
            "enqueue_video_jobs",
            "Queue video jobs for selected clip IDs, or all clips if omitted. "
            "Requires user render approval. This does not run the worker.",
            RenderArgs,
            t_enqueue_video_jobs,
            requires_approval=True,
        )
    )
