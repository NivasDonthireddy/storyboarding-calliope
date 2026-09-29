from calliope.agent.harness import build_harness
from calliope.agent.harness.log import append_event
from calliope.agent.harness.loop import run_turn
from calliope.agent.harness.registry import ToolContext

ROLE_TOOLS = {
    "story": {"get_story", "generate_story", "update_beat"},
    "script": {"get_story", "list_scenes", "generate_script", "break_into_shots"},
}


async def orchestrate(
    ctx: ToolContext,
    goal: str,
    history: list[dict],
    *,
    scenario: str,
    max_steps: int,
) -> dict:
    registry = build_harness()
    if goal.strip().lower() != "build story and script":
        return await run_turn(
            ctx,
            registry,
            history,
            allowed=set(registry.tools),
            scenario=scenario,
            max_steps=max_steps,
        )
    # Deliberately fixed plan: the full application's planner is another LLM call.
    plan = [("story", "draft story"), ("script", "write script")]
    append_event(ctx.settings, ctx.session_id, "plan", {"tasks": plan})
    results = []
    for role, task in plan:
        result = await run_turn(
            ctx,
            registry,
            [{"role": "user", "content": task}],
            allowed=ROLE_TOOLS[role],
            scenario=scenario,
            max_steps=max_steps,
            agent_name=role,
        )
        results.append({"agent": role, **result})
        if result["status"] != "completed":
            return {"status": result["status"], "tasks": results, "answer": result["answer"]}
    return {
        "status": "completed",
        "tasks": results,
        "answer": "Specialist runs finished; inspect data.",
    }
