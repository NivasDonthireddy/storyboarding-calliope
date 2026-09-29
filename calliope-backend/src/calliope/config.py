from dataclasses import dataclass, field
from pathlib import Path

from fastapi import Request


@dataclass(frozen=True)
class Settings:
    # No production configuration or environment variables are loaded.
    data_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parents[2] / "data")
    offline: bool = False
    llm_base_url: str = "http://10.0.8.198:8080/v1"
    llm_model: str = "Agents-A1-abliterated-Q4_0"
    comfyui_base_url: str = "http://localhost:8188"
    request_timeout_sec: float = 180
    render_timeout_sec: float = 300
    poll_interval_sec: float = 1
    agent_max_steps: int = 6

    def __post_init__(self) -> None:
        object.__setattr__(self, "data_dir", self.data_dir.resolve())

    @property
    def db_path(self) -> Path:
        return self.data_dir / "playground.db"

    @property
    def assets_dir(self) -> Path:
        return self.data_dir / "assets"

    @property
    def workflow_dir(self) -> Path:
        return Path(__file__).resolve().parents[2] / "workflows"


def get_settings(request: Request) -> Settings:
    return request.app.state.settings
