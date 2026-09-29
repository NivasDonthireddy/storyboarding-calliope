# Mini Calliope: your learning playground

**Use `uv` for every install, app run, and test command on Windows.** No pip commands,
manual environment activation, or direct `python.exe` launches are needed.
First run one offline demo, then try the API or debugger.
You do not need to learn every mode at once.
After that, [Walk with me: storybuilding and GenAI](guide/README.md) provides eight
lessons on prompts, scenes, tool calls, agents, images, and video.

**For real model debugging, select `Calliope API Debug Ollama`**, not the
Offline configuration. The profile keeps its legacy name and database but now uses
the llama-server at `10.0.8.198:8080`. See [Debug with llama-server](#debug-with-llama-server).

Quick links: [Local setup](#start-here-make-the-first-small-thing-work) |
[Run the API](#b-keep-the-api-running-and-send-requests-yourself) |
[Database map](guide/database-map.md) |
[PyCharm run and debug](#set-up-your-ide-debugger) |
[VS Code run and debug](#debug-in-vs-code) |
[llama-server](#debug-with-llama-server) |
[Automated tests](#run-automated-tests) |
[Troubleshooting](#troubleshooting-local-runs)

This is a small, separate Python project you can change without changing the real application.
It follows Calliope's backend directory names and the same important boundaries:

```text
project -> story beats/cast -> scene script -> shot clips -> jobs -> media
                                  ^
user -> agent -> model tool call -> Python tool executor
```

**The code defaults to live generation, but start with `--offline`.** Offline mode
uses predictable fake model responses and needs no AI server, GPU, or API key.
Real generation is covered in [Debug with llama-server](#debug-with-llama-server).

No production configuration, databases, prompts, or Python modules are imported. You do
not need the Svelte frontend: FastAPI's `/docs` page is your interactive control panel.

## What is what?

| Item | What it means |
|---|---|
| `run.py` | The entry point: always launch this file, not individual files under `src`. |
| `uv sync` | Creates and installs this project's environment from its dependency lockfile. |
| `uv run` | Runs the app or tests in that environment, selecting Python and checking dependencies for you. |
| `calliope-backend\src\calliope` | Application code: API routes, model calls, agents, database, and jobs. |
| `demo` | Automatically sends example requests inside the Python process, prints results, then exits. It does **not** start a browser-accessible server. |
| `serve` | Starts the API and keeps running. You send requests from `/docs` or `playground.http`. |
| `agent` | Runs a scripted conversation/tool workflow, prints results, then exits. Leave this for later. |
| `--offline` | A modifier for any mode: use fake generation instead of contacting real AI servers. |
| PyCharm **Run** | Execute the selected configuration normally; line breakpoints do not pause it. |
| PyCharm **Debug** | Execute the same configuration with the debugger; breakpoints let you pause and inspect values. |
| `uv run ... pytest` | Runs automated checks. It does not start the interactive application. |

**Run and Debug are PyCharm buttons. `demo` and `serve` are arguments to the application.**
You can Run or Debug either mode.

## Start here: make the first small thing work

### 1. Open the playground folder

Open `C:\Projects\learning-playground` as the project in PyCharm, then open its
**Terminal** tab using **PowerShell**. All terminal commands in this README start
from that folder, **not** its parent repository or the `calliope-backend` subfolder:

```powershell
Set-Location 'C:\Projects\learning-playground'
```

If your checkout is elsewhere, substitute its actual location. You should see
`run.py`, `README.md`, and `calliope-backend` in this folder.

### 2. Install the project dependencies once

You need `uv` installed and available in your terminal. Check with `uv --version`.
If it is missing, follow the [official uv installation instructions](https://docs.astral.sh/uv/getting-started/installation/),
then reopen your terminal. The project requires Python **3.11 or newer**; `uv` selects
a compatible interpreter and can download one if needed.

Restore the locked environment:

```powershell
uv sync --locked --project .\calliope-backend --extra dev
```

This creates or updates `calliope-backend\.venv` and installs the application and
`pytest`. An existing `.venv` folder alone does not mean the packages are installed.
You do not need to repeat this before every run: `uv run` checks the environment.

If the command fails with `invalid peer certificate: UnknownIssuer`, use Windows'
trusted certificates without disabling certificate verification:

```powershell
uv --native-tls sync --locked --project .\calliope-backend --extra dev
```

If the same certificate error occurs during an app or test command, use
`uv --native-tls run` in place of `uv run`, keeping the rest of the command unchanged.
Do not disable certificate verification.

Do not install this mini package into the production backend environment: both intentionally
use the import name `calliope`. Their environments are separate; `run.py` also checks which
package it loaded. Prefer the launcher rather than running individual package files directly.

**No environment activation or interpreter path is required in the terminal.**
Every run command below has the same prefix:

| Command part | Meaning |
|---|---|
| `uv run` | Run the following program in the uv-managed environment. |
| `--locked` | Use the existing lockfile; fail rather than silently update it if it is out of date. |
| `--project .\calliope-backend` | Select the backend's `pyproject.toml`, `uv.lock`, and `.venv`. It does not change your working directory. |
| `--extra dev` | Include this project's test dependencies as well as the app dependencies. |
| `.\run.py` | Launch the application; uv automatically uses Python for this `.py` file. |
| `demo --offline --until project` | Arguments passed to the application, not to uv. |

Keep `--offline` **after `.\run.py`**. It means "use the application's fake AI."
uv has its own offline option for dependency downloads; that is not the setting used here.

### 3. Run the smallest example

Copy this complete command into the terminal:

```powershell
uv run --locked --project .\calliope-backend --extra dev .\run.py demo --offline --until project
```

It creates one project in the local SQLite database. Look for `=== Mode ===` with
`"offline": true`, then `=== 1. Saved project (no model call) ===` with a generated `id`.
It then exits and returns you to the terminal prompt. **That is success, not a crash.**
In PyCharm, the equivalent successful ending is `Process finished with exit code 0`.

Nothing opens in the browser because this is a **demo**, not a running API server.
Every demo invocation creates a new project and keeps earlier experiments.

## Your two ways to experiment

### A. Run an automatic demo and let it finish

After the first project works, run through story generation:

```powershell
uv run --locked --project .\calliope-backend --extra dev .\run.py demo --offline --until story
```

Expect the saved project followed by `=== 2. Saved story (model -> schema -> SQLite) ===`,
including four beats, characters, and locations. Offline text is canned; it does not
understand arbitrary ideas or change when you edit a prompt.

`--until` tells **demo** where to stop. Earlier stages always run first on a new project:

| Value | Last completed stage |
|---|---|
| `project` | Save an idea; no model call. |
| `story` | Generate and save beats, characters, and locations. |
| `script` | Write scenes with one default clip per scene. |
| `coverage` | Split scenes into planned shots; no media rendering. This is the default if `--until` is omitted. |
| `assets` | Queue and execute one character image job. |
| `video` | Also queue and execute one clip job. |
| `export` | Also write an export manifest; not an assembled movie. |

For example, to go further without rendering:

```powershell
uv run --locked --project .\calliope-backend --extra dev .\run.py demo --offline --until script
uv run --locked --project .\calliope-backend --extra dev .\run.py demo --offline --until coverage
```

Choose one command at a time. These are separate examples, not steps that reuse the same project.

### B. Keep the API running and send requests yourself

Use this when you want to create your own project and operate it one request at a time:

```powershell
uv run --locked --project .\calliope-backend --extra dev .\run.py serve --offline
```

Wait for `Application startup complete` and Uvicorn's `http://127.0.0.1:8010` address.
The process should **stay running**. Leave that terminal open.

1. Open **http://127.0.0.1:8010/api/health**. Expect `"status": "ok"`, `"offline": true`,
   and a database path under `calliope-backend\data\offline`.
2. Open **http://127.0.0.1:8010/docs**. This is Swagger UI, your manual API control panel.
3. Follow the [project walkthrough below](#walk-through-one-project-in-docs), starting
   with `POST /api/projects`.

Use `/docs`, not just `/`: the application has no homepage at the root URL.
The health response lists configured AI URLs even in offline mode; it does not mean
those servers were contacted or that they are reachable.

To stop, press **Ctrl+C** in the terminal, or **Stop** if you started it in PyCharm.
After editing application code, stop and start the server again; this launcher does not auto-reload.
Do not start a terminal server and a PyCharm server on the same port.

If port 8010 is already in use, choose another port rather than stopping an unknown process:

```powershell
uv run --locked --project .\calliope-backend --extra dev .\run.py serve --offline --port 8011
```

Then use `http://127.0.0.1:8011/docs` and `/api/health`.

**Optional HTTP client:** [playground.http](playground.http) sends requests to an
already-running server. Its green request arrows do **not** start the Python app.
Start `serve` first, make `@base` match the server's port, and replace the ID variables
with IDs from your responses. The file defaults to **8012** for the live debug
configuration; change `@base` to **8011** for offline debugging or **8010** for the
default terminal server above. Use `/docs` if your editor has no HTTP client.

The server binds only to localhost and has no background render worker. In API mode,
queuing a job does not execute it: you explicitly call `POST /api/jobs/run-next`.
In contrast, the demo's `assets`, `video`, and `export` stages call the worker for you.

### Where your data goes

Both the terminal and PyCharm launcher use these defaults:

```text
calliope-backend\data\offline\playground.db    demos and API runs with --offline
calliope-backend\data\live\playground.db       runs without --offline
```

The saved **Calliope API Debug Ollama** configuration explicitly uses
`calliope-backend\data\ollama\playground.db` instead, keeping its live model
experiments separate from both default databases.

An offline API run can read projects created by offline demos because they share that
database. Data survives process restarts. Use `GET /api/projects` to list saved projects;
do not assume the next ID will be `1`. `--data-dir` selects a different storage directory,
as shown in [Keep your experiments isolated](#keep-your-experiments-isolated).

### Clear all saved database rows

Use [clear_data.sql](clear_data.sql) in the project root to empty all ten application
tables in one transaction, deleting dependent rows before their parents. It preserves
table definitions and auto-increment counters, so new IDs do not restart at `1`.

**This permanently deletes the selected database's saved data.** Stop the API and demos,
back up the database, and connect your IDE's SQLite console to the intended
`playground.db` (offline, live, Ollama, or your custom data directory). With no active
transaction, execute the entire script and stop on any error. If a statement fails
after `BEGIN`, run `ROLLBACK;` rather than continuing to `COMMIT;`.

The script only clears the connected database; it does not delete generated assets,
exports, or trace files on disk.

## Walk through one project in `/docs`

Keep `serve --offline` running for your first walkthrough. **Stages 1-4 are enough
for a first manual test**; agents and media jobs can wait.

For each endpoint, expand it in `/docs`, click **Try it out**, fill in any path
parameters and request body, then click **Execute**. Inspect **Server response** for
the actual status code and body, not the example schema shown further down the page.
For generation requests below, replace Swagger's example request body with `{}` unless
a different body is shown.

Use IDs returned by your own requests. `project_id`, `session_id`, `scene_id`, `clip_id`,
and `job_id` identify different records. An entity ID is not its position on the story board.

### Stage 1: save the idea

Call `POST /api/projects`:

```json
{
  "title": "The Last Lantern",
  "idea": "Mira guides a stranger through a flooded station before her lantern goes out.",
  "genre": "Drama",
  "tone": "Tense, then hopeful",
  "target_duration": "30 seconds"
}
```

Expect HTTP `200` and a response containing `id`. Copy that value into the `project_id`
field for subsequent requests. Read it with `GET /api/projects/{project_id}`.
A project exists; no story has been generated.

**Change something:** Send an empty title. Notice the `422` validation response. Your
Python route should not execute its insert for that invalid request.

### Stage 2: generate the story

Call `POST /api/projects/{project_id}/generate-story` with `{}`.
Then read `GET /api/projects/{project_id}/story`.

Expect HTTP `200` and four beats plus characters and locations. With `--offline`,
these come from the fake model; without it, this stage calls the configured model server.

Follow:

```text
routers\story.py: draft_story -> generate_story
  -> agent\prompts.py: build_story_messages
  -> agent\llm.py: generate_structured -> LLMClient.chat
  -> fake response (offline) OR LLMClient._live_chat (live)
  -> JSON parsing + Pydantic validation
  -> insert beats, characters, locations
```

The mini version requests exactly four beats. SQLite, not the model, assigns saved IDs.
Generating a second full story on the same project returns `409` rather than replacing it.
Create another project when experimenting with different prompts.

**Change something:** Edit the story system instruction in `agent\prompts.py`, then run a
new live draft. Compare the raw prompt, raw response, and saved story. In offline mode, prompt
changes alone do not change the fake's canned content.

### Stage 3: turn saved beats into a script

Call `POST /api/projects/{project_id}/generate-script` with:

```json
{"with_clips": false}
```

Read `GET /api/projects/{project_id}/scenes`.

You should find ordered scene records with `heading`, `action`, `dialog`, character IDs,
location ID, and default clips whose `clip_path` is null.

`script_agent.py` sends **two scenes per request** so you can see two distinct chunks.
Each finished chunk is saved before the next one starts. If a later model request fails,
earlier scenes remain: inspect the database instead of assuming everything rolled back.

**Change something:** Inspect `previous_tail` in the second chunk's prompt. Explain why
the writer needs that data rather than assuming the model remembers a previous API call.

### Stage 4: plan shot coverage

Call `POST /api/projects/{project_id}/expand-clips` with `{}`.
Read the scenes again.

The real model chooses the clip count; the offline example produces two per scene.
`dialog_lines_covered` maps 1-based nonempty dialogue lines to clips. The mini validator
requires every line exactly once. No clip has been rendered yet.

Passing `{"with_clips": true}` in Stage 3 combines scene writing and this coverage stage,
as the full application's script tool normally does.

For the offline example, the first four stages should leave **four beats, four scenes,
and eight planned clips**, all with `clip_path: null`. This is a complete manual check
of the story-planning flow; null media paths are expected because you have not rendered.

**Change something:** In a new experiment, change the coverage instruction to ask for a
different shot split. Inspect the returned line assignments, not just descriptions.
Coverage cannot be regenerated after jobs exist for that project; this prevents destroying
the clip references used by your queued or completed renders.

### Stage 5: make the model choose and execute a tool

Create a session with `POST /api/agent/sessions`:

```json
{"project_id": 1}
```

Replace `1` with your project ID. Send a message using the returned session ID:

```http
POST /api/agent/sessions/{session_id}/messages
```

```json
{
  "content": "rename opening beat to The Lantern Awakens",
  "allow_render": false,
  "max_steps": 6
}
```

In **live mode**, this is a real tool-calling request to the model server. A typical exchange is:

```text
model: get_story({})
Python: return saved beats and IDs
model: update_beat({"beat_id": <actual ID>, "title": "The Lantern Awakens"})
Python: check the linked project, validate arguments, update SQLite
model: final answer
```

Read `GET /api/agent/sessions/{session_id}` for the persistent event trace. Match each
`tool_call_id` with its assistant tool call. Then reread the story to confirm the change.

The mini HTTP route waits for the turn to finish, rather than launching a background
task. That makes stepping and inspecting the return value easier.

To watch specialists on a **new** project:

```powershell
uv run --locked --project .\calliope-backend --extra dev .\run.py agent --offline --goal "build story and script"
```

That exact goal triggers a deliberately fixed story-then-script plan. Each specialist
has a restricted tool set. The command above uses fake responses; remove `--offline`
only when ready for real model tool calls. The planner itself is plain Python here,
not another LLM; the full application's planner is more flexible.

Offline commands are intentionally a small exact vocabulary: `draft story`, `write script`,
`show story`, `rename opening beat to TITLE`, `queue videos`, and `build story and script`.
For offline rename experiments, use an existing story and the exact command prefix.

### Stage 6: send a real image workflow to ComfyUI

**Live-mode details follow.** On your offline server, the same queue/worker requests
produce an SVG placeholder instead and do not contact ComfyUI.

The bundled `calliope-backend\workflows\image.json` is a small **local SD1.5 text-to-image
workflow**, not a paid external API node. It names a checkpoint found on your ComfyUI
server: `v1-5-pruned-emaonly-fp16.safetensors`. A different server may require changing
that filename. It uses 512x512, batch size 1, twenty Euler steps, and seed 42. Those
settings are directly visible in the JSON; change the seed or step count to experiment.

Start with one image, not the whole film. Call:

```http
POST /api/jobs/projects/{project_id}/render
```

```json
{
  "kind": "image",
  "workflow_name": "image",
  "prompt": "A brass lantern on a wooden bench inside a flooded station, warm amber light, cinematic photograph"
}
```

The response is a **pending job**, not an image. Inspect it using `GET /api/jobs/{job_id}`.
Then explicitly call `POST /api/jobs/run-next`. This executes the oldest pending job in
this playground database. Inspect the queue first if you have several experiments pending.

Read these boundaries in order:

```text
routers\jobs.py -> QueueManager.enqueue -> pending row
QueueWorker.run_next -> running row
ComfyUIClient.render
    -> patch prompt into the workflow
    -> inspect server node metadata
    -> POST /prompt
    -> GET /history/{prompt_id} until finished
    -> GET /view for the output bytes
worker -> local file + job output_paths + done
```

Open the returned output path directly, or use
`GET /api/assets/file?path=<returned-path>` in the browser/API client. This route serves
only files under this playground's assets directory.

To attach an image to a saved character instead, call
`POST /api/projects/{project_id}/generate-assets`:

```json
{
  "workflow_name": "image",
  "character_ids": [1],
  "location_ids": []
}
```

Replace the character ID with one returned by your story. After the worker finishes,
`GET /api/projects/{project_id}/assets` shows its `sheet_path`. The small example workflow
generates an ordinary image from the character description, not a sophisticated production
character-sheet layout.

Each live ComfyUI job keeps raw HTTP traces under
`calliope-backend\data\live\traces\comfyui-job-...` by default.
You can inspect the submitted graph, polling replies, and downloaded output.

### Stage 7: generate a real video from a saved clip

In offline mode this produces a storyboard JSON placeholder, **not** a playable video.
The model and rendering details below apply only to live mode.

The bundled `calliope-backend\workflows\video.json` uses the local **Wan 2.2 TI2V 5B**
model in text-to-video mode. Its installed model files are
`wan2.2_ti2v_5B_fp16.safetensors`, `umt5_xxl_fp8_e4m3fn_scaled.safetensors`,
and `wan2.2_vae.safetensors`.

The small learning recipe uses **512x320, 25 frames, 12 fps, twenty UniPC steps**, and
H.264 MP4 output. Text encoding runs on CPU. The positive prompt is genuinely fed into
the model; this is not a slideshow, placeholder, or external provider call.

Call:

```http
POST /api/jobs/projects/{project_id}/generate-videos
```

```json
{"workflow_name": "video", "clip_ids": [1]}
```

Use a real clip ID from your scene response, then explicitly run the next job. The clip
description and its allocated dialogue become the prompt; the downloaded video is attached
to `clips.clip_path`.

**The demo video is approximately 2.08 seconds and silent.** Its frame count/fps come
from the workflow, not automatically from `clips.duration_sec`. Putting dialogue in a
prompt does not give this video model an audio track or guarantee visible lip-sync.
These limits keep the learning render small; edit the graph deliberately when you want
to experiment with longer clips. Larger frames/models can require much more GPU memory.

Follow the workflow's nodes while reading the trace:

```text
UNETLoader + CLIPLoader + VAELoader
    -> positive/negative text conditioning + empty video latent
    -> KSampler (denoise the latent)
    -> VAEDecode (turn latent samples into frames)
    -> CreateVideo + SaveVideo (encode an MP4)
```

The latent is the model's compressed working representation, not yet a viewable frame.
Notice that `Wan22ImageToVideoLatent` is also used without a start image here; this
particular recipe is text-to-video despite that node name.

### Optional: use your own local workflow

Export a working **API-format** workflow from your ComfyUI and register it with
`POST /api/workflows/video` (or a different name). Registration overrides the named
built-in only in the selected data directory; it does not edit the bundled file.
The wrapper records the prompt mapping:

```text
kind: "video"
prompt_node: the string ID of the node holding your positive prompt
prompt_input: that node's text input name, commonly "text" or "prompt"
workflow: the actual exported API graph object (not the UI nodes/links format)
```

`GET /api/workflows` lists available names. `GET /api/workflows/nodes/{class_type}` lets
you inspect the remote server's input definitions. Every non-prompt setting remains in
your exported graph, making resolution, steps, models, and frame count visible rather
than hidden behind automatic configuration.

For an image-to-video workflow, the optional `reference_node` and `reference_input`
mapping lets the client upload the first available reference image. The bundled
text-to-video workflow does not use character reference images. This is intentionally
a single-reference teaching adapter, not the production app's full multi-reference system.

Missing or invalid live workflows produce an explicit error, never a fake video.
Credential-bearing workflows and recognized paid API nodes are rejected by this teaching
adapter. The main repository's Krea/MiniMax examples can involve external providers;
owning ComfyUI does not make those provider calls local. Do not paste credentials into
these files or traces.

For predictable offline exercises:

```powershell
uv run --locked --project .\calliope-backend --extra dev .\run.py demo --offline --until export
```

This exercises all stages with an SVG image, a **storyboard JSON file instead of video**,
and an export manifest. Without `--offline`, `demo --until assets` runs one actual image;
`demo --until video` also runs one actual clip using the bundled video workflow.
`demo --until export` adds the manifest.

### Stage 8: inspect the ordered export manifest

Call `POST /api/jobs/projects/{project_id}/export`, then run the worker. The mini export
lists available clips in scene/clip order and explicitly lists skipped clips.

**It produces JSON, not an assembled movie**, even in live mode. This keeps the sample
focused on generation, tool calls, and job handoffs; the full app adds FFmpeg assembly.
A successful manifest does not mean every planned clip was rendered.

## Open the data at each boundary

Live model calls save a JSON file under the selected data directory:

```text
traces\llm-<request-id>.json
  url
  request                 messages, schemas/tools, model, sampling settings
  status_code
  response_text           exact response body from the HTTP service
  response                parsed response envelope, including usage if supplied
  error                   present on handled transport/parsing failures
```

There is no silent switch to a fake if the live server fails. Inspect the `502` response
and the trace filename it identifies. Invalid JSON and invalid schema data are explicit
failures, not successful-looking fallback stories.

The mini client uses **non-streaming** chat completions to make the entire request and
response easy to inspect. The production client also handles streaming. This mini client
includes `enable_thinking=false` through llama's chat-template options. Support depends
on the server and model template. The raw envelope preserves any reasoning or usage
fields the server returns.

For table relationships, keys, and column definitions, see the
[visual database map](guide/database-map.md).

Open `playground.db` using your IDE's SQLite database viewer. Useful read-only queries:

```sql
SELECT id, project_id, order_index, title FROM story_beats ORDER BY project_id, order_index;
SELECT id, project_id, heading, dialog FROM scenes ORDER BY id;
SELECT id, scene_id, dialog_lines_covered, clip_path FROM clips ORDER BY id;
SELECT id, kind, status, error FROM jobs ORDER BY id;
SELECT id, session_id, type, data_json FROM agent_events ORDER BY id;
```

These are your learning databases, not `calliope-backend\data` in the main application.
Traces can contain your full prompts and generated content. They are Git-ignored; avoid
putting secrets in prompts or sharing traces without reviewing them.

## Set up your IDE debugger

For **manual runs**, use the `uv run` commands in PyCharm's **Terminal**; no run
configuration is needed. A terminal `uv run` does not attach PyCharm's debugger.
For request-by-request debugging, use the saved API configuration below. It keeps the
server running while you send requests yourself, instead of automatically executing
the demo and exiting.

There are two saved API choices:

| Configuration | Mode | Browser URL |
|---|---|---|
| **Calliope API Debug Ollama** (legacy name) | Real `Agents-A1-abliterated-Q4_0` calls to llama-server at `10.0.8.198:8080` | `http://127.0.0.1:8012/docs` |
| **Calliope API Debug Offline** | Fake model responses | `http://127.0.0.1:8011/docs` |

For real generation, follow [the llama-server settings and breakpoint walkthrough](#debug-with-llama-server).
The next steps describe the optional offline configuration.

### 1. Select the saved PyCharm API configuration

Open `C:\Projects\learning-playground` as the PyCharm project and complete the uv
dependency setup above. The configuration is stored in
`.run\Calliope API Debug Offline.run.xml`. Select **Calliope API Debug Offline** in
the toolbar dropdown or under **Run > Edit Configurations > Python**. Your existing
**Calliope Demo Offline** configuration is separate and unchanged.

If the new configuration is not listed yet, reload files from disk or reopen the
project. Do not create a duplicate with the same name.

| Field | Exact value for this checkout |
|---|---|
| Name | `Calliope API Debug Offline` |
| Python interpreter | `C:\Projects\learning-playground\calliope-backend\.venv\Scripts\python.exe` (created and managed by `uv`) |
| Run target type | **Script path**, not Module name |
| Script path | `C:\Projects\learning-playground\run.py` |
| Script parameters / Parameters | `serve --offline --port 8011` |
| Working directory | `C:\Projects\learning-playground` |
| Run with `uv run` | Enabled |
| Debug just my code | Enabled |
| Interpreter options / `.env` files | Empty |

The saved environment variables configure the launcher tools, not application secrets:

| Variable | Purpose |
|---|---|
| `PYTHONUNBUFFERED=1` | Show Python output promptly. |
| `UV_PROJECT` | Points to this checkout's `calliope-backend`, where `pyproject.toml` and `uv.lock` live. |
| `UV_LOCKED=true` | Prevent uv from silently changing the lockfile. |
| `UV_NATIVE_TLS=true` | Use Windows' trusted certificates for uv downloads. |

If the interpreter is missing, select the existing uv environment under **Add Local
Interpreter**, rather than creating another environment. The saved SDK name matches
this checkout; reselect the interpreter if you move the project. Script, working-directory,
and uv-project paths use PyCharm's project-directory macro.

The interpreter path is an **IDE setting**, not a terminal command. Do not put `uv.exe`
in a Python interpreter field, or paste the full `uv run ...` command into script
parameters. Keep **Run with `uv run`** enabled and continue using uv for dependency
management and manual commands.

**Do not select `playground | 1. Save an idea (no model call)` to launch the app.**
That configuration sends a request to an already-running server; it does not start
Python. Use the named API configuration rather than generating an argument-free
configuration by right-clicking `run.py`.

### 2. Debug one browser request

1. Open `calliope-backend\src\calliope\routers\projects.py`. Find `create_project` and
   click the gutter beside `with get_db(settings.db_path) as conn:` (currently line 23).
   If there is already a red dot, keep it; clicking it again removes the breakpoint.
2. Select **Calliope API Debug Offline** and click **Debug** (bug icon), or **Shift+F9**
   with the default Windows keymap. Wait for application startup.
3. Open **http://127.0.0.1:8011/api/health**, then **http://127.0.0.1:8011/docs**.
   Expect `"offline": true`. Merely opening these pages does not call `create_project`.
4. In `/docs`, execute `POST /api/projects` with the
   [Stage 1 request body](#stage-1-save-the-idea). PyCharm pauses at the breakpoint.
5. Inspect `payload` and `settings` in **Variables**. Use **Step Over** (**F8**) through
   the insert. Inspect `project_id` after its assignment, not before.
6. Use **Resume Program** (**F9**) to let the browser receive its response. Save the
   returned ID, and leave the debugger running for your next request.

The browser waits while a request is paused. Do not repeatedly click Execute.
**Run** starts the same API without stopping at breakpoints. **Stop** ends the server.
Restart after code changes; this launcher does not auto-reload.

The saved offline editor configuration uses **8011**, leaving **8010** available for
a terminal server and **8012** for the live configuration. Debug only one API
process on each port. For this offline exercise, change `playground.http`'s `@base`
from its live default of 8012 to 8011. A default offline terminal run and the
offline editor configuration share data; the live configuration uses separate storage.

### 3. Continue through the codebase request by request

Remove or disable the previous breakpoint and put the next one on an executable line
inside the indicated function. Keep the same API process running. Paths below are
relative to `calliope-backend\src\calliope`.

| Request | Starting function and next boundary |
|---|---|
| `POST /api/projects` | `routers\projects.py`: `create_project` -> database insert |
| `POST /api/projects/{project_id}/generate-story`, body `{}` | `routers\story.py`: `generate_story` -> prompts -> `agent\llm.py`: `generate_structured` -> saved story |
| `POST /api/projects/{project_id}/generate-script`, body `{"with_clips":false}` | `routers\scenes.py`: `write_script` -> `agent\script_agent.py` |
| `POST /api/projects/{project_id}/expand-clips`, body `{}` | `routers\scenes.py`: `expand_clips` -> `agent\coverage_agent.py` |
| Agent session creation, then a message | `routers\agent.py`: `create_session`, then `post_message` -> runner -> tool loop -> registry/executor |
| Render request, then `POST /api/jobs/run-next` | `routers\jobs.py`: `render`, then `run_next` -> queue worker -> media handling |
| Export request, then `POST /api/jobs/run-next` | `routers\jobs.py`: `enqueue_export` -> queue worker -> `export\runner.py` |

Use the [API walkthrough](#walk-through-one-project-in-docs) for complete request
bodies and prerequisites. Use the IDs returned by your own requests, and send the
corresponding GET request after each operation to inspect what was saved.

In PyCharm, use **F7 / Step Into** to follow your functions, **F8 / Step Over** to
execute a call without entering it, **Shift+F8 / Step Out** to return to its caller,
and **F9 / Resume** to finish the request. Use the call stack to see how you reached
the paused function. Button names are reliable if your keymap uses different shortcuts.

**Optional automatic demo:** your existing **Calliope Demo Offline** configuration
still uses the same interpreter and script with `demo --offline --until story`.
It creates a new project, generates the story, and exits; no browser request is needed.
This is useful for one linear trace, but it is not the request-by-request API mode.

### More useful breakpoint locations

Start with one breakpoint. Add these only when you reach the corresponding feature.
Locations are identified by function name so they remain useful if line numbers change.

| File under `calliope-backend\src\calliope` | Breakpoint | Inspect |
|---|---|---|
| `routers\projects.py` | `create_project`, before the SQL insert | `payload`, `settings`; `project_id` after assignment |
| `agent\llm.py` | `generate_structured`, at `return schema.model_validate(candidate)` | `candidate`, `schema`; works offline and live |
| `agent\llm.py` | `_live_chat`, immediately before `client.post` | `payload`, `messages`, `tools`; **live mode only** |
| `agent\llm.py` | Immediately after `response = await client.post(...)` completes | `response.status_code`, `response.text`; **live mode only** |
| `agent\script_agent.py` | `_persist_scenes` | `scenes`, IDs assigned by SQL |
| `agent\coverage_agent.py` | After `generate_structured` | `draft.clips`, line assignments |
| `agent\harness\loop.py` | Before `registry.execute` | `name`, `raw_args`, parsed `args` |
| `agent\harness\registry.py` | Before `tool.executor` | validated arguments, `ctx.project_id` |
| `agent\harness\loop.py` | Before appending the observation | `result`, `tool_call_id`, `messages` |
| `queue\worker.py` | Worker execution | queued payload, produced paths, job state |

If the IDE navigates to the production `calliope` package instead, keep this playground
open as a separate project, use its `.venv`, and right-click `calliope-backend\src` >
**Mark Directory as > Sources Root**. Runtime imports are anchored by `run.py`.

`await` waits for I/O; it does not jump into the remote server's Python process. Step over
the network call, then inspect what came back. You can debug the local boundary, not
the internals of a model running on another machine through this debugger.

Stopping the IDE debugger does not undo committed rows or automatically stop an already
submitted ComfyUI workflow. Keep experiments small and inspect job state after interruption.

## Debug in VS Code

Open **`C:\Projects\learning-playground`**, not just `calliope-backend`, as the VS Code
folder. Install the recommended Microsoft **Python** and **Python Debugger** extensions
when prompted. uv must be available on PATH; reopen VS Code after installing uv if needed.

The workspace includes these settings:

| File | Purpose |
|---|---|
| `.vscode\launch.json` | Live API, offline API, and offline demo configurations using the uv-managed Python interpreter, `run.py`, the playground working directory, unbuffered output, and `justMyCode: true`. |
| `.vscode\tasks.json` | `uv: sync playground`, run before each debug launch: locked dependency sync with `--extra dev` and Windows native TLS. |
| `.vscode\settings.json` | Default Python interpreter points to this project's `.venv`; terminal environment activation is disabled. |
| `.vscode\extensions.json` | Recommends the Python and Python Debugger extensions. |

**uv owns dependency installation and the environment.** VS Code's Python Debugger
launches Python from that environment directly so it can attach its debugger.
Do not replace the debug configuration's Python interpreter with `uv.exe` or change
its type to a shell task. Manual terminal commands still use `uv run`.

For real model calls, select **Calliope API Debug Ollama**, press **F5**, and
use port **8012** as described [below](#debug-with-llama-server). To practice without
any model calls, use the offline walkthrough:

1. Open **Run and Debug** (**Ctrl+Shift+D**) and select **Calliope API Debug Offline**.
   Its arguments are `serve --offline --port 8011`.
2. Set a breakpoint in `routers\projects.py` inside `create_project`, as in the
   PyCharm walkthrough above. Stop any other debug API you started on port 8011.
3. Press **F5**. VS Code runs the uv preparation task, then starts the API under
   the debugger. If preparation fails, fix the task error rather than choosing to
   debug anyway.
4. Wait for startup and open **http://127.0.0.1:8011/docs**. Execute `POST /api/projects`
   with the Stage 1 body. The debugger pauses; inspect **Variables**, **Watch**, and
   **Call Stack** in the sidebar.
5. Use **F10 / Step Over**, **F11 / Step Into**, **Shift+F11 / Step Out**, and
   **F5 / Continue**. Use **Shift+F5 / Stop** when finished.

Continue with the same request-by-request sequence documented for PyCharm. Swagger
works without an HTTP-client extension. `playground.http` also works if you separately
use a compatible HTTP client, but that is not required.

The **Calliope Demo Offline** launch option uses
`demo --offline --until story` and exits after the automatic example. It does not
serve `/docs`. Matching PyCharm and VS Code configurations use the same ports and
databases, so do not run the same API configuration in both editors simultaneously.

## Run automated tests

**Manual testing** means sending your own requests using `/docs`.
**Automated testing** means running the assertions already written under
`calliope-backend\tests`. No `serve` process, browser, GPU, or remote AI server is
needed for these tests. They use temporary databases and fake responses or mocked
HTTP; real outbound HTTP is blocked by the test fixtures.

From `C:\Projects\learning-playground`, run one small test first:

```powershell
uv run --locked --project .\calliope-backend --extra dev pytest -c .\calliope-backend\pyproject.toml .\calliope-backend\tests\test_story_script.py::test_story_is_persisted_once -q
```

It checks that a story is saved and readable, and that regenerating it returns `409`.
Run the full story/script test file when changing that flow:

```powershell
uv run --locked --project .\calliope-backend --extra dev pytest -c .\calliope-backend\pyproject.toml .\calliope-backend\tests\test_story_script.py -q
```

Run all existing tests when you want to check the whole playground:

```powershell
uv run --locked --project .\calliope-backend --extra dev pytest -c .\calliope-backend\pyproject.toml .\calliope-backend\tests -q
```

Here uv runs `pytest` instead of `.\run.py`; `--extra dev` ensures pytest is installed
from this project's dependencies rather than fetched as a separate tool.
`-c` selects this backend's pytest configuration even though you are running from
the playground root. `-q` reduces output. Success ends with a `passed` summary and
exit code `0`; a failure prints the assertion or exception to investigate. Tests do
not reset or modify the demo/API databases.

**In PyCharm:** select the same project interpreter, search Settings for
**Default test runner**, and choose **pytest**. Open `test_story_script.py`, right-click
`test_story_is_persisted_once`, and choose **Run** for that test. To step through it,
set a breakpoint on an executable line in the test or application code and choose
**Debug** for that test instead. If editing the generated pytest configuration,
use `C:\Projects\learning-playground\calliope-backend` as its working directory.
Do not put pytest arguments into your demo or API configuration.

## Deliberately break things

These are **optional failure exercises**, not setup commands. Run them one at a time
after the normal story example works. No API server needs to be running:

```powershell
uv run --locked --project .\calliope-backend --extra dev .\run.py demo --offline --until story --scenario invalid-json
uv run --locked --project .\calliope-backend --extra dev .\run.py demo --offline --until story --scenario invalid-data
uv run --locked --project .\calliope-backend --extra dev .\run.py agent --offline --scenario unknown-tool
uv run --locked --project .\calliope-backend --extra dev .\run.py agent --offline --scenario bad-arguments
uv run --locked --project .\calliope-backend --extra dev .\run.py agent --offline --scenario loop --max-steps 3
```

The first two deliberately exit with a `RuntimeError` containing HTTP `502`.
The new project remains saved, but no story is saved for that failed draft.
Tool errors are returned as observations and recorded in the session; the last
scenario ends at the step budget. Failures are part of these exercises.

To debug invalid generated data, temporarily set the demo configuration's parameters
to `demo --offline --until story --scenario invalid-data`. Place a breakpoint at
`return schema.model_validate(candidate)` inside `agent\llm.py`'s
`generate_structured` and inspect `candidate` before validation. For `invalid-json`,
break earlier at `candidate = json.loads(content)` and inspect `content` instead.
Afterward, remove `--scenario ...` from the parameters and remove the breakpoint.

For live experiments, edit the **mini** prompt and start a new project. First predict
whether the change affects the model request, the validator, the stored rows, or the
tool's permissions. Then compare prediction with observation.

## Troubleshooting local runs

| Symptom | What to do |
|---|---|
| `uv` is not recognized | Install uv using the official instructions linked in setup, then reopen the terminal so it picks up the updated PATH. |
| `No module named 'fastapi'`, `'uvicorn'`, or `'pytest'` | Use the full documented `uv run --locked --project .\calliope-backend --extra dev ...` command, not bare Python or pytest. For IDE debugging, select the same uv-managed interpreter. |
| Dependency installation or `uv run` reports `UnknownIssuer` | Add `--native-tls` immediately after `uv`, as in setup. If it still fails, resolve the machine's trusted certificate/proxy configuration; do not disable TLS verification. |
| uv cannot find `pyproject.toml` or the project | Run from `C:\Projects\learning-playground` and include `--project .\calliope-backend`; the playground root has no `pyproject.toml`. |
| `run.py` cannot be found | Set the terminal or run configuration's working directory to `C:\Projects\learning-playground`. Do not prepend another `learning-playground` to the relative command paths. |
| `the following arguments are required: command` | Enter `demo --offline --until story` or `serve --offline` in **Script parameters**, then select that named Python configuration. |
| Demo exits and `/docs` will not open | Expected: `demo` does not host a server. Start `serve --offline` and leave it running. |
| Browser shows `404` at `http://127.0.0.1:8010/` | Use `/docs` or `/api/health`; there is no root homepage. |
| Browser or HTTP client reports connection refused | Start the Python **API** configuration, wait for startup, and match the request's port to it. An HTTP request configuration cannot launch the server. |
| Requests work but never reach the debug server | Confirm the address: live debugging and `playground.http` default to **8012**, offline debugging uses **8011**, and the default terminal server uses **8010**. |
| `WinError 10048` / address already in use | Stop your own previous server or choose another unused port in the launch arguments; update the browser URL and HTTP client's `@base` too. Do not run matching configurations in both editors simultaneously. |
| Breakpoint never pauses | Use **Debug**, not Run; ensure breakpoints are enabled and not muted. In API mode, actually send the relevant request. `_live_chat` is never called offline. |
| The model server is running but the app still returns fake responses | Select **Calliope API Debug Ollama**, not Offline. Removing `--offline` from another configuration requires stopping and restarting it. Confirm `/api/health` reports `offline: false` on **8012**. |
| llama-server reports that a model is missing | Inspect `http://10.0.8.198:8080/v1/models` and use the exact loaded model ID in `--model`; the configured default is `Agents-A1-abliterated-Q4_0`. An embedding-only model cannot generate stories. |
| VS Code has no debugger for `debugpy` | Install the recommended Microsoft Python Debugger extension and reload VS Code. |
| VS Code's `uv: sync playground` task fails | Read the task's terminal output; confirm uv is on PATH and the lockfile matches the manifest. Do not bypass a failed preparation task. |
| Browser request stays pending while debugging | Resume execution in PyCharm. A paused handler cannot finish the HTTP response. |
| Blank project title gives `422` without reaching the handler | Expected: request validation rejects the body before `create_project`. Use the valid Stage 1 body to reach its breakpoint. |
| Story generation returns `409` | That project already has a story. Create a new project and use its returned ID. |
| Live generation returns `502` or times out | Return to `--offline` to learn locally, or check the live server configuration and the trace path in the error. Offline is never selected automatically on failure. |
| Code changes seem ignored | Stop and restart the API process, confirm the selected configuration, and ensure imports resolve to this playground. |
| Image/video job remains `pending` | Queuing is separate from execution. Inspect `/api/jobs`, then explicitly call `POST /api/jobs/run-next`. It runs the oldest pending job, not necessarily the one you just queued. |

## Debug with llama-server

**Live versus offline is controlled by the launch arguments.** Changing the model URL
does not override `--offline`; that flag deliberately skips HTTP calls and returns
fake responses. The saved **Calliope API Debug Ollama** configurations omit it.
Their legacy name and `data\ollama` storage path are retained so existing projects
and IDE database connections continue to work; neither requires a local Ollama service.

Your current `calliope-backend\src\calliope\config.py` uses these defaults:

| Setting | Current value / purpose |
|---|---|
| `llm_base_url` | `http://10.0.8.198:8080/v1` -- llama-server's OpenAI-compatible API |
| `llm_model` | `Agents-A1-abliterated-Q4_0` -- the loaded model alias reported by the server |
| `comfyui_base_url` | `http://localhost:8188` -- a separate service, only needed for image/video jobs |

Keep **`/v1`** on the model base URL: the client appends `/chat/completions`.
The resulting endpoint is `http://10.0.8.198:8080/v1/chat/completions`.

### Switch the server or model in one place

Edit **only `llm_base_url` and `llm_model` in
[`Settings`](calliope-backend/src/calliope/config.py)**, then restart the API/debug
session. These shared defaults apply to terminal `serve`, `demo`, and `agent` runs,
both editors' live debug profiles, and all story, script, coverage, and agent model
calls. No launch-configuration or test changes are needed when switching models.

This mini app does **not** load a `.env` file or production environment settings.
`--model` is an optional per-run model override; omit it to use the shared setting.
Both live debug configurations omit that override. Use the exact model ID returned
by the chosen server's `/v1/models` endpoint and retain `/v1` in `llm_base_url`.

### Model choice on the server

Inference runs on the server at `10.0.8.198:8080`, not on this Windows machine.
The default alias **`Agents-A1-abliterated-Q4_0`** was selected from
`GET /v1/models` with `status.value` equal to `loaded`; other listed models may
be unloaded. The application uses this explicit default and does not automatically
choose a different model if the server's loaded models change.

Changing the model name does not guarantee story quality, schema-valid JSON,
or native tool-call support. Agent flows send tool definitions, so the model must support
that request format. Unsupported requests remain explicit errors; the app does
not silently switch to another model or offline output.

### Select the live configuration

Ensure the remote server is reachable. Open **http://10.0.8.198:8080/v1/models**
and confirm `Agents-A1-abliterated-Q4_0` is loaded. No local model download is needed.

| Setting | Saved value in both editors |
|---|---|
| Configuration | **Calliope API Debug Ollama** |
| Script | `C:\Projects\learning-playground\run.py` |
| Arguments | `serve --port 8012 --data-dir .\calliope-backend\data\ollama` |
| Working directory | `C:\Projects\learning-playground` |
| Interpreter | This project's uv-managed `.venv` |
| Offline flag | **Absent** |
| Data | `calliope-backend\data\ollama\playground.db` |

In **PyCharm**, choose this name in the toolbar, then **Debug / Shift+F9**.
Its settings are saved in `.run\Calliope API Debug Ollama.run.xml`, with **Run with
`uv run`** and **Debug just my code** enabled.

In **VS Code**, choose this name in **Run and Debug**, then press **F5**.
The uv preparation task runs first, and the debugger uses that environment.
Stop the previous editor debug session before switching configurations.

Check **http://127.0.0.1:8012/api/health** for `offline: false`,
`llm_url: "http://10.0.8.198:8080/v1"`, and `model: "Agents-A1-abliterated-Q4_0"`.
Then open **http://127.0.0.1:8012/docs** or send individual requests from
`playground.http`, whose default `@base` is now 8012.

The health endpoint reports configuration, not a successful generation.
Saving a project alone also makes no model call.

### Follow one real model call

1. Execute `POST /api/projects` with the Stage 1 body, and keep its returned ID.
   The live debug database is separate; IDs from offline sessions may not exist here.
2. Set a breakpoint in `agent\llm.py` at the `if not self.settings.offline` line
   in `LLMClient.chat`.
3. Execute `POST /api/projects/{project_id}/generate-story` with `{}`.
   When paused, inspect `self.settings.offline` (`False`), `llm_base_url`, and `llm_model`.
4. Follow the call into `_live_chat`, or move the breakpoint to
   `response = await client.post(trace["url"], json=payload)`.
   Inspect `trace["url"]`, `payload["model"]`, `payload["messages"]`, and
   `payload["response_format"]`.
5. Step over the HTTP call. llama-server now runs real inference. Inspect
   `response.status_code` and `response.text` when the call returns, then resume.
6. Read the saved story with `GET /api/projects/{project_id}/story` and inspect the
   raw request/response trace under `calliope-backend\data\ollama\traces`.

Your local debugger follows the application and the HTTP boundary. It cannot step
inside the remote llama-server inference process. While paused, the browser waits.
The first request may also include model-loading time; later calls can reuse the
loaded model. Move or disable breakpoints when you want requests to finish unattended.

**Story, script, and coverage generation use server-enforced JSON schemas.**
`generate_structured` sends the selected Pydantic schema in `response_format`
with `type: "json_schema"` and `strict: true`, as well as keeping it in the prompt.
llama-server constrains the output structure; Python still parses the JSON and
validates it with Pydantic before saving. Unsupported formats and malformed or
schema-invalid replies remain explicit errors, not silent fallbacks.
Inspect `response.text` and the saved trace when diagnosing
failures. Agent tool-call requests do not use this response format. Structured
output does not guarantee story quality or identical wording between runs.

### Equivalent uv terminal commands

For a real story demo that exits:

```powershell
uv run --locked --project .\calliope-backend --extra dev .\run.py demo --until story --data-dir .\calliope-backend\data\ollama
```

For the same live API without an attached IDE debugger:

```powershell
uv run --locked --project .\calliope-backend --extra dev .\run.py serve --port 8012 --data-dir .\calliope-backend\data\ollama
```

Do not start this terminal server while an editor's API is already using 8012.
The course's separate live examples also use 8012; stop your own existing server
or choose another free port before starting a second configuration.

**llama-server handles text and tool calls, not ComfyUI rendering.** Story, script, coverage,
and agent debugging need only llama-server. Image/video jobs additionally need the configured
ComfyUI service and its workflow models. `demo --until assets`, `video`, or `export`
executes real render jobs when `--offline` is absent; keep the first debugging run
at `--until story`.

## How this maps back to the full application

All source paths below live under `calliope-backend\src\calliope` in both projects.

| Path | Responsibility retained in the mini |
|---|---|
| `main.py`, `config.py`, `db.py` | API composition, isolated settings, SQLite |
| `models\schemas.py` | Request and generated-data shapes |
| `routers\projects.py`, `story.py`, `scenes.py` | Save/read project, story, scene, and clip data |
| `agent\prompts.py`, `llm.py` | Prompt construction and real model HTTP boundary |
| `agent\script_agent.py`, `coverage_agent.py` | Chunked scene writing and shot planning |
| `agent\harness\registry.py`, `plugins` | Advertised tools connected to Python executors |
| `agent\harness\loop.py`, `runner.py`, `orchestrator.py`, `log.py` | Tool feedback loop, session, specialists, trace |
| `agent\asset_agent.py`, `video_agent.py` | Prepare entity/clip render jobs |
| `queue\manager.py`, `worker.py` | Saved work and explicit execution |
| `comfyui` | Workflow submission, completion, output download |
| `export\runner.py` | Ordered artifact collection |

Important deliberate simplifications:

| Full application | Learning playground |
|---|---|
| Svelte UI, canvas, Build Scene, SSE | Swagger UI, CLI output, saved traces |
| Flexible duration planning | Four beats and one scene per beat; duration text is teaching context, not a runtime guarantee |
| More permissive parsing/retries | Strict JSON/Pydantic validation; fail visibly so you can inspect the response |
| Regeneration/replacement | Full story/script regeneration on existing content rejected |
| Background agent and queue tasks | Agent request waits; worker runs one job per explicit request |
| Dynamic LLM planner | One fixed two-role plan for the exact demo goal |
| Extensive render policies | Explicit `allow_render` argument for agent video enqueue |
| MCP, memory, skills, 3D, many workflow adapters | Omitted: they are not needed to trace the core generation path |
| FFmpeg movie export | Manifest of ordered media files, not an assembled movie |

This is a teaching subset, not a production replacement or a byte-for-byte copy. In
particular, our tools validate their schemas explicitly; the production registry does
not apply a generic JSON Schema validator to every executor.

Continue with [the local learning guide](guide/README.md).
Read one lesson there, then exercise the corresponding small module here.

## Keep your experiments isolated

The API has no authentication and is intended for localhost learning, not deployment.
Live prompts are sent to the configured model/render servers. The current localhost
defaults stay on this computer; changing the endpoints to remote hosts sends them
there instead. Imported workflows may contact additional providers depending on
their nodes; use ones you understand.

If you want a completely fresh experiment, select a new directory instead of deleting data:

```powershell
uv run --locked --project .\calliope-backend --extra dev .\run.py serve --offline --data-dir .\calliope-backend\data\experiment-02
```

Use a different new directory for a live experiment; an explicit `--data-dir` is used
as-is and does not automatically add an `offline` or `live` subfolder.
Do not point it at the production application's storage. Modes are recorded on jobs;
a live job cannot run as an offline placeholder, or an offline job as a live render.
If you stop the process during a render, inspect its trace and remote history before
submitting another job. The mini intentionally has no automatic crash-retry queue or global
ComfyUI cancellation, which could interfere with other work on your server.

For automated checks that leave these databases untouched, see
[Run automated tests](#run-automated-tests).
