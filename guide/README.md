# Walk with me: storybuilding and GenAI in Mini Calliope

[Playground reference](../README.md)

This is your **learning path**, not another setup reference. We will develop one short story, follow it through the real application, and explain the AI concepts exactly when they become useful.

You already know basic Python and FastAPI. Start there. An LLM call is still an HTTP request made by Python. A tool is still a function executed by Python. We will make the unfamiliar parts visible one boundary at a time.

**First read [Lesson 1: Think like a storyteller](01-story-design.md). No server or code changes are needed for that lesson.**

## What you will understand

By the end, you should be able to explain both sides of this diagram:

```text
STORY DECISIONS
premise -> goal/obstacle/stakes -> beats -> scenes -> camera coverage

APPLICATION WORK
save idea -> prompt an LLM -> validate/store JSON -> plan clips
                     ^
user -> agent loop -> accepted tool call -> Python executor

MEDIA WORK
prompt + workflow -> queued job -> model sampling -> files -> manifest
```

You will distinguish *a good story* from *valid JSON*, *a tool request* from *an executed change*, and *a saved clip plan* from *a generated video*.

Keep the [visual database map](database-map.md) beside the lessons to follow project
ownership, scene-character links, clips, jobs, and agent history in Mermaid diagrams.

This course covers the GenAI concepts exercised by this playground. It also locates embeddings, RAG, MCP, memory, and fine-tuning on the wider map without pretending that the mini app implements them.

## Your route

Use one lesson per sitting. The times are suggestions, not deadlines.

| Lesson | What we do together | Evidence you understood it |
|---|---|---|
| [1. Story design](01-story-design.md), 30 min | Build a premise, logline, character objective, stakes, and four causal beats | Explain why each beat changes the situation |
| [2. Save the idea](02-project-and-state.md), 30 min | Start the isolated API and create our project | Point to the validated input, SQL write, and saved ID |
| [3. Your first model call](03-prompts-and-responses.md), 60 min | Generate beats and inspect the real request/response | Separate prompt, model, tokens, parsing, validation, and story quality |
| [4. Scenes and coverage](04-scenes-and-coverage.md), 60 min | Expand beats into scenes, then shots | Explain continuity, chunking, dialogue allocation, and persistence |
| [5. Tools and agents](05-tools-and-agents.md), 60 min | Observe a read/edit loop and a two-specialist plan | Explain who decides, who executes, and how results return to the model |
| [6. Image generation](06-image-generation.md), 60 min | Generate a lantern image and read the workflow | Explain conditioning, latent space, sampling, seed, steps, CFG, and VAE |
| [7. Video and jobs](07-video-and-jobs.md), 60 min | Render one saved clip and inspect the export manifest | Distinguish workflow settings, runtime, job state, references, and actual media |
| [8. Experiments and capstone](08-experiments-and-capstone.md), 60-90 min | Diagnose failures and develop a second story yourself | Defend your conclusions using traces, records, and a story-quality rubric |

Inside each lesson: **predict -> run one action -> inspect -> explain -> change one thing**. Do not run the whole HTTP file at once.

## One continuous project, not eight unrelated demos

Our story is **The Last Lantern**:

> Mira can leave a flooded station alone, but turns back after hearing a stranger. With her lantern fading, she must guide them both to the exit.

Keep one main project for Lessons 2-7. Use a new project for prompt comparisons, full regeneration, and the capstone. Full story/script regeneration is intentionally rejected on existing content.

The `run.py demo` command creates a **new project every time**. `demo --until script` does not resume a project created by a previous `demo --until story`. For the continuous course, use the API as described below.

Keep this small record in your own notebook:

| Name | Value to copy from your responses |
|---|---|
| Project ID | |
| Opening beat ID | |
| First character ID | |
| First scene ID | |
| Selected clip ID, after coverage | |
| Agent session ID | |
| Image job ID and file path | |
| Video job ID and file path | |
| LLM trace filename for each generation | |

An ID is not a display position. Scene number 1 can have database ID 17. Refresh clip IDs after coverage because it replaces clip rows.

## Set up once, in Lesson 2

All shell commands in this course use **uv in PowerShell**, starting from the
**playground folder**, just like the main README:

```powershell
Set-Location 'C:\Projects\learning-playground'
```

If the mini environment has not been installed:

```powershell
uv sync --locked --project .\calliope-backend --extra dev
```

The [playground reference](../README.md#start-here-make-the-first-small-thing-work)
explains uv setup, certificate troubleshooting, and the common command prefix.
No manual environment activation or separate pip installation is needed.
Do not install the mini package into production's environment: both use the import name `calliope`.

For the course's live server:

```powershell
uv run --locked --project .\calliope-backend --extra dev .\run.py serve --port 8012 --data-dir .\calliope-backend\data\course-live
```

Open **http://127.0.0.1:8012/docs**. This is separate from the earlier playground's default port and data directory. If that port is already occupied, choose another unused port and use it consistently; do not stop an unrelated process.

In Swagger, expand an endpoint, select **Try it out**, enter path IDs and JSON, and select **Execute**. Read the response body as well as the HTTP status.

Alternatively, use [playground.http](../playground.http), changing `@base` to `http://127.0.0.1:8012` and its ID variables to your real IDs. The lessons sometimes add an action beyond that convenience file; Swagger exposes the complete API.

For deterministic offline exercises, use a **different** directory and port:

```powershell
uv run --locked --project .\calliope-backend --extra dev .\run.py serve --offline --port 8013 --data-dir .\calliope-backend\data\course-offline
```

| Mode | Model behavior | Media behavior |
|---|---|---|
| Live, no `--offline` | Calls the configured llama server | Calls ComfyUI only when you explicitly run a queued job |
| Offline | Canned Last Lantern responses and selected failure scenarios | SVG image / storyboard JSON, not model-generated images or MP4s |

The fake cannot teach you whether a new prompt is effective. Use it to understand control flow; use live mode for content and sampling experiments.

## Working rules that prevent confusion

**After editing Python:** stop your own course server and restart with the same command. This launcher does not use autoreload. The saved database remains.

**After editing a workflow JSON:** enqueue a new job. Jobs capture a workflow/settings snapshot when created; changing a file does not rewrite an old job.

**Before running a job:** inspect `GET /api/jobs`. `run-next` runs the oldest pending job in this course database, not necessarily the project tab you last viewed. Keep one pending experiment at a time.

**Before retrying:** inspect saved rows and the previous job. Text generation can commit partial scene chunks; a timed-out remote render may still finish. Stopping your local debugger is not undo or a remote ComfyUI cancellation.

**Keep the boundary clear:** edit only `learning-playground`. Do not point its data directory at production storage. Live traces contain complete prompts/responses; do not include secrets or sensitive material.

## Reading code without getting lost

Every source link in these lessons targets the **mini** implementation. Open only the named function first. You are not expected to understand the whole file before doing the exercise.

Examples have explicit labels:

| Label | Meaning |
|---|---|
| Actual source | An excerpt or named behavior in the current mini implementation |
| Illustrative | Possible story/model data; your live wording and IDs can differ |
| Paper exercise | Something to reason about without changing the application |
| Optional extension | Not implemented by the mini app; a later engineering assignment |

The course is grounded in the playground source inspected on **27 September 2026**. The earlier whole-application notes describe a larger implementation with different defaults. Do not transfer features such as streaming, a model-based planner, automatic retries, or film assembly into the mini app just because they exist in the full application.

**Your first action:** go to [Lesson 1](01-story-design.md), write the protagonist's objective, and stop at its checkpoint before opening the code.
