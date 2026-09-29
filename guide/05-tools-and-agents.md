# Lesson 5: Watch a model request an action, then watch Python do it

[Previous: Scenes and coverage](04-scenes-and-coverage.md) | [Course map](README.md) | [Next: Images](06-image-generation.md)

**Today:** make tool calling and agents feel like Python you can follow.

So far, you chose an endpoint and Python ran a fixed generation pipeline. We will now let the model choose a small action from an advertised set.

## 1. Separate three levels of behavior

| Level | Example | Who selects the operation? |
|---|---|---|
| Ordinary application function | Save a project | Your request and Python control flow |
| Fixed GenAI pipeline | Read beats, ask for scene chunks, save scenes | Python selects stages; the model supplies content |
| Tool-using agent | Read story, identify opening beat, request a rename, inspect result | The model requests operations within a Python-controlled loop |

An **agent** here is the bounded program around model calls, tools, observations, and state. The LLM is one component, not the whole agent.

The **harness** is the surrounding machinery: registry, loop, context, policy checks, and logging. The **runner** manages the session's turn. **Orchestration** coordinates multiple tasks or roles.

The filename `script_agent.py` does not by itself make `generate_script` an autonomous agent. Inspect the control flow instead of relying on names.

## 2. Start a conversation linked to your existing project

Call `POST /api/agent/sessions`:

```json
{"project_id": 1}
```

Replace `1` with the project ID in your notebook. Save the returned **session ID**.

Then call `POST /api/agent/sessions/{session_id}/messages`:

```json
{
  "content": "rename opening beat to The Lantern Awakens",
  "allow_render": false,
  "max_steps": 6
}
```

This phrasing works in the scripted offline model too. Live responses and exact tool ordering can vary.

**Predict:** Can the model safely assume that the opening beat's database ID is `1`?

No. It should read the project's actual story and IDs.

After the response, read both:

```http
GET /api/agent/sessions/{session_id}
GET /api/projects/{project_id}/story
```

The title should change if the tool succeeded. The scene action and already saved clip plans should not automatically change. This exercise changes a label, not the whole narrative.

## 3. A tool is a contract connected to an implementation

Open [plugins/story.py](../calliope-backend/src/calliope/agent/harness/plugins/story.py), at `UpdateBeatArgs`, `register`, and `t_update_beat`.

Find these three pieces:

```text
name/description: what the tool means
UpdateBeatArgs: the expected beat_id and title
t_update_beat: the Python executor
```

Now read `ToolRegistry.openai_payload` in [registry.py](../calliope-backend/src/calliope/agent/harness/registry.py).

It gives the model an OpenAI-compatible function definition containing the tool's name, description, and parameter schema. **It does not send the executor's Python source.**

The model does not gain arbitrary SQL or filesystem access. Python has registered a limited set of capabilities.

## 4. Zoom into one complete call/result exchange

Suppose `get_story` established that the first beat's ID is `41`. This is an **illustrative subsequent model message**:

```json
{
  "role": "assistant",
  "content": null,
  "tool_calls": [
    {
      "id": "call_rename",
      "type": "function",
      "function": {
        "name": "update_beat",
        "arguments": "{\"beat_id\":41,\"title\":\"The Lantern Awakens\"}"
      }
    }
  ]
}
```

The `arguments` value is a string containing JSON. It is not a Python dictionary yet, and it is not a completed write.

In [loop.py](../calliope-backend/src/calliope/agent/harness/loop.py), follow:

```text
read function.name
    -> json.loads(function.arguments)
    -> require a dictionary
    -> registry.execute(ctx, name, args, allowed)
```

Inside the registry, Python verifies that the tool is available, checks approval when relevant, and validates the arguments using Pydantic.

The host-created `ToolContext` supplies the project ID. `update_beat` checks both that project and the requested beat ID in its SQL update.

The result might become this **illustrative shortened tool message**:

```json
{
  "role": "tool",
  "tool_call_id": "call_rename",
  "content": "{\"ok\":true,\"data\":{\"id\":41,\"title\":\"The Lantern Awakens\"}}"
}
```

The real `data` includes additional beat fields. `tool_call_id` pairs the observation with the earlier request. The next model request includes that observation.

Now the model has evidence for its final sentence. It can also receive an error observation and decide how to respond.

**Model output requested the operation. Python performed the operation. The tool result reports what happened.**

## 5. Read the loop as familiar control flow

This is **teaching pseudocode**, not a second implementation:

```text
repeat up to max_steps:
    ask model with conversation and allowed tools
    save assistant response
    if no tool calls:
        return answer
    for each requested tool:
        parse arguments
        execute or return an explicit error
        append result to the conversation
return step-limit result
```

The feedback is the important part. Without the next model call, the model cannot use the tool's observation.

`max_steps` counts outer loop iterations, not every HTTP request or operation in the entire application. A single `generate_script` tool can make several inner model calls for writing and coverage.

When no tool calls arrive, the loop ends. That is a stopping condition, **not a semantic guarantee that the user's goal was completed**. Always compare the answer with tool results and saved data.

## 6. See the nested model calls

Ask yourself what happens if a model calls `generate_script`:

```text
Outer model call: "Use the generate_script tool."
    Python executor:
        reads saved story
        inner model call: write scenes 1-2 as JSON
        inner model call: write scenes 3-4 as JSON
        further model calls: coverage for each scene
        saves the results
    tool result returns to the outer conversation
Outer model call: summarizes the observation
```

All these calls can use the same configured model. The difference is their input and purpose.

The inner structured writer does not automatically receive the outer chat history. Its prompt builders decide what it sees. That explains why "I told the agent earlier" does not prove a constraint reached the scene-writing request.

## 7. Inspect persistent history

The session endpoint returns events such as `turn_start`, `step`, `message`, `tool_result`, and `turn_end`.

Within a `message` event, inspect `data.message`. For each assistant tool call, find the tool observation with the matching ID. Within a `tool_result` event, inspect `data.tool`, `data.call_id`, and `data.result`.

Read `derive_llm_history` in [log.py](../calliope-backend/src/calliope/agent/harness/log.py) and its use in [runner.py](../calliope-backend/src/calliope/agent/harness/runner.py).

The runner replays prior main-agent messages. Specialists have separate trails. This mini has no automatic history summarization or context-budget trimming. Very long sessions can exceed the model server's usable context; start a fresh learning session rather than assuming infinite memory.

## 8. Run two specialists on a fresh project

Do not run this build on the already-written main project. Instead, from
`C:\Projects\learning-playground` in PowerShell:

```powershell
uv run --locked --project .\calliope-backend --extra dev .\run.py agent --goal "build story and script" --data-dir .\calliope-backend\data\course-swarm
```

This creates a new project and runs live model calls. Add `--offline` and choose a separate `course-swarm-offline` directory for the deterministic version.

Open [orchestrator.py](../calliope-backend/src/calliope/agent/harness/orchestrator.py). Only that exact normalized goal selects a fixed two-task plan:

```text
story role -> draft story
script role -> write script
```

Tasks run **sequentially**, not in parallel. Each specialist gets its own task message and tool subset. The script role learns the earlier result by reading saved project data.

There is no extra planner LLM in this mini, no automatic agent-to-agent conversation, and no separate trained model per role. The full app adds a model-based planning layer.

## 9. Try a permission failure without starting a render

On your main session, send:

```json
{"content": "queue videos", "allow_render": false}
```

The offline model deterministically requests the render tool; a live model may request it or explain the restriction without calling. If it calls, the registry denies execution before enqueueing.

Inspect the actual tool trace and `GET /api/jobs`. There should be no job created by a denied tool.

The model cannot grant itself permission by adding `allow_render` to tool arguments. This flag comes from the API request into host context. It is a small teaching policy, **not user authentication**. Direct render endpoints are separate explicit API actions and do not go through this chat guard.

## Checkpoint

**Why can two agents use the same model and still behave differently?**

<details>
<summary>Answer and reasoning</summary>

They can receive different goals, message histories, instructions, and allowed tools. An agent role is an application configuration around inference, not necessarily a different set of trained weights.

The differences remain bounded by code. Prompts help guide choices; scope checks and validators enforce which operations actually run.

</details>

**What is MCP's role in the rename we just performed?**

<details>
<summary>Answer and reasoning</summary>

None. The tool executor is a local Python function registered in this application. MCP is a protocol for discovering/calling capabilities in another program; model tool calling does not require it. The mini has no MCP integration.

</details>

Next, [Lesson 6](06-image-generation.md) crosses from generated language into generated pixels.
