from fastapi import HTTPException

from calliope.agent.harness.log import append_event, derive_llm_history, read_events
from calliope.agent.harness.orchestrator import orchestrate
from calliope.agent.harness.registry import ToolContext
from calliope.config import Settings
from calliope.db import get_db
from calliope.models.schemas import MessageCreate


class AgentRunner:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def start_turn(self, session_id: int, payload: MessageCreate) -> dict:
        with get_db(self.settings.db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT * FROM agent_sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
            if row is None:
                raise HTTPException(404, "Session not found")
            if row["status"] == "running":
                raise HTTPException(409, "Session is already running")
            conn.execute("UPDATE agent_sessions SET status = 'running' WHERE id = ?", (session_id,))
            project_id = row["project_id"]
        status = "error"
        try:
            append_event(self.settings, session_id, "turn_start", {"content": payload.content})
            # Replay only main-loop history. Specialists have independent conversations.
            prior = [
                event
                for event in read_events(self.settings, session_id)
                if event["data"].get("agent") == "main"
            ]
            history = derive_llm_history(prior)
            user_message = {"role": "user", "content": payload.content}
            history.append(user_message)
            append_event(
                self.settings,
                session_id,
                "message",
                {
                    "agent": "main",
                    "message": user_message,
                },
            )
            ctx = ToolContext(self.settings, project_id, session_id, payload.allow_render)
            result = await orchestrate(
                ctx,
                payload.content,
                history,
                scenario=payload.scenario,
                max_steps=payload.max_steps or self.settings.agent_max_steps,
            )
            status = result["status"]
            return result
        finally:
            with get_db(self.settings.db_path) as conn:
                conn.execute(
                    "UPDATE agent_sessions SET status = ? WHERE id = ?",
                    (status, session_id),
                )
            append_event(self.settings, session_id, "turn_end", {"status": status})
