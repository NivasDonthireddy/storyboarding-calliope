# Lesson 8: Learn from experiments, diagnose failures, and build your second story

[Previous: Video and jobs](07-video-and-jobs.md) | [Course map](README.md)

**Today:** move from following instructions to explaining the application yourself.

You do not need to memorize every implementation detail. You do need a reliable method for answering: **what went in, what came out, what ran, and what was saved?**

## 1. Keep a short experiment record

For each experiment, record:

```text
Question:
Prediction:
One thing I changed:
Project/session/job IDs:
Prompt/workflow trace:
Observed result:
What this result proves:
What it does not prove:
```

Example:

```text
Question: Does a stronger visual anchor keep Mira's clothing consistent?
Prediction: Including "yellow raincoat, dark braid" will reduce wardrobe changes.
One thing changed: The character constraint in the initial story brief.
Observed result: Three generated scenes retained the anchor; one omitted it.
Proves: These particular scene outputs differed in anchor retention.
Does not prove: Every future video will depict the same face or clothes.
```

An experiment is useful even when the prediction is wrong. The goal is to locate the responsible boundary, not defend your first guess.

## 2. Compare prompts fairly

Create two **new projects** from the same original brief. Do not generate the comparison from `projects.idea` after drafting without checking it: that field now contains the generated logline.

For a simple A/B comparison:

| Hold fixed | Change |
|---|---|
| Model alias, code, original idea, genre, duration text | One sentence of instruction or one tone value |

Use at least a few drafts if you want evidence beyond a single demonstration. LLM sampling means different answers can occur without your intended change being the only cause.

For images, hold workflow/model, resolution, sampling settings, and prompt fixed when comparing seeds. Hold the seed fixed when comparing a prompt change, while remembering that identical seeds do not guarantee bit-identical execution in every environment.

Do not change prompt, model, seed, CFG, and resolution together and then conclude "the prompt fixed it."

## 3. Score engineering correctness and story quality separately

Use two scorecards rather than one vague impression.

**Application evidence**

| Question | Evidence |
|---|---|
| Did the intended model receive the intended input? | Saved request payload |
| Did generated data match the required structure? | Successful validation or explicit error |
| Were real IDs and project boundaries respected? | Tool result and saved records |
| Did an actual render complete? | Job status, downloaded bytes, playable/viewable output |
| Did the planned stage finish, or only part of it? | Stage result plus records |

**Story/media quality:** score each item 0 = missing, 1 = partly clear, 2 = clear.

| Criterion | What to look for |
|---|---|
| Goal | The protagonist's objective can be stated in one sentence |
| Causality | Events lead to consequences rather than merely following one another |
| Choice | A meaningful decision affects the outcome |
| Stakes | The viewer understands why success or failure matters |
| Payoff | The ending responds to the setup and choice |
| Visual specificity | Action can be shown rather than explained only as inner thought |
| Continuity | Cast, setting, objects, and movement remain coherent |
| Economy | The material fits a short concept without unnecessary new threads |

A technically successful run can score poorly on story quality. A wonderful generated paragraph can fail the application's required structure. Both observations matter.

## 4. Use the debugger at boundaries

Configure the IDE using the [playground instructions](../README.md#set-up-your-ide-debugger). For API exercises, run the course server under the debugger; for a single linear trace, use `demo --until story`.

| Where to stop | Inspect | What you learn |
|---|---|---|
| `routers/projects.py`, `create_project` | `payload`, insert ID | FastAPI data becomes a saved row |
| `agent/llm.py`, before the HTTP POST | `payload["messages"]`, tools, model | What the model actually receives |
| `agent/llm.py`, after the POST | `response.text`, parsed message | Raw envelope versus answer text |
| `generate_structured`, before validation | `candidate`, `schema` | Parsing versus declared structure |
| `script_agent.py`, before `_persist_scenes` | `draft.scenes`, real entity IDs | Generated content becomes records |
| `harness/loop.py`, before registry execution | Tool name and parsed arguments | Model request becomes a dispatch |
| `harness/registry.py`, before executor | `ctx`, validated arguments | Scope/approval and runtime validation |
| `comfyui/client.py`, before `/prompt` | Patched graph | Workflow configuration becomes remote work |
| `queue/worker.py`, before `_attach` | `job`, output paths | Downloaded media becomes an entity reference |

Find these symbols in the [mini source tree](../calliope-backend/src/calliope), not the production backend.

Step over network calls to inspect their responses. Your local debugger cannot reveal the remote model's internal computation. Also, returned reasoning text is generated output, not guaranteed access to the model's internal causal process.

If the code you changed seems ignored, first check the interpreter/package path and whether you restarted the non-autoreloading server. Do not immediately blame the model.

## 5. Practice predictable failures offline

Keep the live main project untouched. These CLI runs create separate learning projects
using offline mode. Run them in PowerShell from `C:\Projects\learning-playground`.

**Bad generated JSON:**

```powershell
uv run --locked --project .\calliope-backend --extra dev .\run.py demo --offline --until story --scenario invalid-json
```

Expect an explicit model-output error and a nonzero CLI exit. The project can exist, but the rejected draft should not insert story rows.

**Readable JSON with the wrong structure:**

```powershell
uv run --locked --project .\calliope-backend --extra dev .\run.py demo --offline --until story --scenario invalid-data
```

The fake returns `{"beats":"four"}`. `json.loads` can parse it; Pydantic rejects it.

**Unknown tool, invalid arguments, and an endless requester:**

```powershell
uv run --locked --project .\calliope-backend --extra dev .\run.py agent --offline --scenario unknown-tool
uv run --locked --project .\calliope-backend --extra dev .\run.py agent --offline --scenario bad-arguments
uv run --locked --project .\calliope-backend --extra dev .\run.py agent --offline --scenario loop --max-steps 3
```

The first two return error observations in the agent trace. The third reaches `step_limit`. These agent result statuses are distinct from the CLI raising an HTTP error during a direct generation request.

Offline runs print fake-model inputs/outputs to the console; they do not produce live HTTP `llm-...json` traces. Session events still record agent exchanges.

Read the existing focused examples in [test_llm_http.py](../calliope-backend/tests/test_llm_http.py), [test_agent.py](../calliope-backend/tests/test_agent.py), and [test_comfy_http.py](../calliope-backend/tests/test_comfy_http.py) after you understand the behavior. Their mocked responses are controlled experiments, not live quality measurements.

## 6. Diagnose with a sequence, not guesses

Use this sequence when something looks wrong:

```text
1. Was my API input valid and linked to the intended project/session?
2. What did Python read from the database?
3. What did the actual model/workflow request contain?
4. What did the remote service return?
5. Did parsing/validation/tool execution succeed?
6. What rows and files exist now?
7. Is the remaining problem content quality rather than transport or state?
```

Do not retry a write or render just to see what happens. Some work may already have committed or been submitted remotely.

Some common wrong diagnoses:

| Symptom | Tempting conclusion | More useful first question |
|---|---|---|
| Model invents an appearance | "The database forgot it" | Was the correct appearance in this request? |
| Changed prompt has no effect | "The LLM ignores everything" | Did I restart Python, and am I in live mode? |
| Edited workflow has no effect | "ComfyUI is broken" | Is this an old queued snapshot or a registered override? |
| Agent says it cannot render | "It has no intelligence" | Was the tool available and `allow_render` granted? |
| HTTP 200 but no video | "The UI lost the file" | Did I only enqueue? What does the job body say? |
| Video has no sound | "The model skipped dialogue" | Does this workflow contain any audio-generation stage? |

## 7. Put the wider GenAI vocabulary in the correct boxes

You now have practical anchors for terms that otherwise sound abstract:

| Concept | Meaning | Status in this mini |
|---|---|---|
| Prompt engineering | Design the supplied instructions/context/output requirements | Used directly |
| Structured output | Make generated content fit an application data contract | Prompted JSON plus Pydantic validation |
| Tool calling | Model requests a named capability; application executes it and returns an observation | Implemented |
| Agent | Bounded program coordinating model decisions and tool feedback | Implemented |
| Orchestration | Coordinate stages or specialist runs | Fixed two-role example |
| Embedding | Numeric representation of information | Text conditioning exists in media workflows; no app-level semantic search |
| RAG | Retrieve relevant external material and include it in generation context | Not implemented; reading project rows is not evidence of a vector-search pipeline |
| MCP | Protocol for exchanging capabilities with another program | Not implemented; local Python tools work without it |
| Conversation memory | Retained messages supplied again on later calls | Main-session event replay |
| Long-term semantic memory | Selectively storing/retrieving durable useful facts | No separate semantic-memory system here |
| Fine-tuning | Update trained model parameters using data | Not performed |
| LoRA | A parameter-efficient adaptation method often used with trained models | No LoRA training/loading path in the bundled recipes |
| Multimodal application | An application works across modalities such as text, image, and video | Yes, through separate stages; not proof that the llama call itself receives images |
| Guardrails | Code-level restrictions/validation around model-driven behavior | Tool scopes, argument validation, render flag, and local file/workflow restrictions |
| Evaluation | Check whether outputs satisfy the task and quality criteria | Your traces, existing tests, and the rubric above |

An **optional future RAG extension** might retrieve a relevant passage from a story bible and add it to `build_script_chunk_messages`. An **optional MCP extension** might expose the read-story capability through a separate server. Those require implementation; changing the terminology does not add them.

The [earlier MCP lesson](../../docs/learning/05-understanding-mcp.md) and [state lesson](../../docs/learning/06-state-jobs-and-reliability.md) explain the larger application and protocol labs separately.

Treat model-generated content as data to validate, not trusted instructions to execute arbitrarily. A schema alone is neither authorization nor protection against every prompt-injection scenario.

## 8. Your capstone: The Last Delivery

Now develop a different story without following the exact Last Lantern content.

**New premise:** A delivery cyclist discovers that the final parcel is a birthday gift for a child in a dark apartment building. She must decide whether to leave it at the locked entrance or find a way to deliver it before the celebration ends.

Keep it grounded, with one building, two or three characters, and one visible decision. Do not add a new tool or feature yet.

1. Write a one-sentence logline, goal, obstacle, stakes, and theme. Outline four causal beats yourself.
2. Create a new **live-mode** project. Generate its story and score it against the same rubric. Offline mode would return the canned Lantern story.
3. Generate scenes with `with_clips:false`. Inspect both chunk prompts, real character/location IDs, and whether the second chunk preserves continuity.
4. Expand coverage before any jobs exist. Account for every dialogue line and explain each shot's purpose.
5. Create a linked agent session. Rename one beat through a tool call and prove that other beat titles did not change.
6. Generate one project image with the generic `/render` endpoint and one saved clip with `/generate-videos`. Explain which parts of the story actually appear in each prompt.
7. Export the manifest. Explain every included and skipped clip instead of claiming the whole film is finished.

Your evidence packet can be a notebook with paths; do not copy secrets or entire unrelated logs into it:

```text
Original human brief and four-beat outline
Saved project/scene/clip IDs
One story model request and raw response
Second scene chunk with previous_tail
One matched tool call/result pair
One image path and one video path
One job's workflow snapshot and completion trace
Manifest with included/skipped clips
Quality score and one proposed improvement
```

**You have completed the capstone when you can explain those artifacts without rereading this guide**, not merely when every endpoint returned something.

## Final explained checkpoints

**Why does adding three minutes to the project duration not automatically create a three-minute movie?**

<details>
<summary>Answer</summary>

The mini fixes the beat count, derives scene count from beats, requests approximate scene writing, and uses a video recipe with a fixed frame count/FPS. It does not coordinate those into a runtime-constrained editing pipeline. The target is context, not an enforced end-to-end duration contract.

</details>

**Why might an agent remember a chat fact but the inner scene writer omit it?**

<details>
<summary>Answer</summary>

The outer agent and inner structured writer receive different prompts. The scene writer receives what its builder reads and includes, not the entire agent conversation. Trace the actual inner request before diagnosing memory loss.

</details>

**Where would you add a rule that a scene must reference only existing project characters?**

<details>
<summary>Answer</summary>

In application validation before persistence. The mini already checks supplied character/location IDs in `generate_script`. A prompt can ask for correct IDs, but the code must enforce the rule.

</details>

**What is the most important division of responsibility in this app?**

<details>
<summary>Answer</summary>

Models generate content and propose actions. Python builds context, communicates with services, validates results, enforces allowed actions, writes state, executes jobs, and connects outputs to records. You supply the creative goal and evaluate whether the result serves the story.

</details>

## Bridge back to the larger Calliope

Use the same relative source paths in the full backend to compare the core seams: model client, prompt builders, generation functions, registry, loop, runner, queue, and media output attachment.

Expect additional behavior there: richer story entities, different count/chunk rules, streaming events, a model-based planner, replacement policies, more workflows, and FFmpeg export.

Use [the whole-application walkthrough](../../docs/learning/00-guided-walkthrough.md) for that second pass. Your mental model is now the same four questions:

**What was supplied? What was generated? What did code execute? What was saved or produced?**
