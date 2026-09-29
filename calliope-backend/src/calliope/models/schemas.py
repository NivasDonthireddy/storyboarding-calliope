from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

GenerationScenario = Literal["normal", "invalid-json", "invalid-data"]
AgentScenario = Literal["normal", "unknown-tool", "bad-arguments", "loop"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)


class ProjectCreate(StrictModel):
    title: str = Field(min_length=1, max_length=200)
    idea: str = Field(min_length=1)
    genre: str = "Drama"
    tone: str = "Hopeful"
    target_duration: str = "30 seconds"


class GenerationOptions(StrictModel):
    scenario: GenerationScenario = "normal"


class ScriptOptions(GenerationOptions):
    with_clips: bool = True


class BeatDraft(StrictModel):
    order_index: int = Field(ge=1)
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)


class CharacterDraft(StrictModel):
    name: str = Field(min_length=1)
    appearance: str = Field(min_length=1)


class LocationDraft(StrictModel):
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)


class StoryDraft(StrictModel):
    logline: str = Field(min_length=1)
    beats: list[BeatDraft] = Field(min_length=4, max_length=4)
    characters: list[CharacterDraft] = Field(min_length=1)
    locations: list[LocationDraft] = Field(min_length=1)


class SceneDraft(StrictModel):
    order_index: int = Field(ge=1)
    heading: str = Field(min_length=1)
    action: str = Field(min_length=1)
    dialog: str
    duration_sec: int = Field(ge=1)
    character_ids: list[int]
    location_id: int


class ScriptDraft(StrictModel):
    scenes: list[SceneDraft] = Field(min_length=1)


class ClipDraft(StrictModel):
    description: str = Field(min_length=1)
    dialog_lines_covered: list[int]
    duration_sec: int = Field(ge=1, le=8)


class CoverageDraft(StrictModel):
    clips: list[ClipDraft] = Field(min_length=1)


class BeatUpdate(StrictModel):
    title: str = Field(min_length=1)


class SessionCreate(StrictModel):
    project_id: int = Field(ge=1)


class MessageCreate(StrictModel):
    content: str = Field(min_length=1, max_length=2000)
    scenario: AgentScenario = "normal"
    allow_render: bool = False
    max_steps: int | None = Field(default=None, ge=1, le=20)
