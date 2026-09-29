from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from calliope.agent.llm import ModelOutputError
from calliope.config import Settings
from calliope.db import migrate_db
from calliope.routers import agent, assets, jobs, projects, scenes, story, workflows


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        migrate_db(settings)
        yield

    app = FastAPI(
        title="Mini Calliope learning playground",
        description="Live llama/ComfyUI by default. Jobs run only when you call run-next.",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.include_router(projects.router, prefix="/api/projects", tags=["1. Projects"])
    app.include_router(story.router, prefix="/api/projects", tags=["2. Story"])
    app.include_router(scenes.router, prefix="/api/projects", tags=["3. Script and coverage"])
    app.include_router(agent.router, prefix="/api/agent", tags=["4. Agents"])
    app.include_router(assets.router, prefix="/api", tags=["5. Assets"])
    app.include_router(workflows.router, prefix="/api/workflows", tags=["6. Workflows"])
    app.include_router(jobs.router, prefix="/api/jobs", tags=["7. Jobs"])

    @app.exception_handler(ModelOutputError)
    async def model_error(request: Request, exc: ModelOutputError):
        return JSONResponse(status_code=502, content={"detail": str(exc)})

    @app.get("/api/health")
    def health():
        return {
            "status": "ok",
            "offline": settings.offline,
            "database": str(settings.db_path),
            "model": settings.llm_model,
            "llm_url": settings.llm_base_url,
            "comfyui_url": settings.comfyui_base_url,
            "worker": "manual",
        }

    return app
