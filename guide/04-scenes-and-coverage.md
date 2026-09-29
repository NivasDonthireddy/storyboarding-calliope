# Lesson 4: Turn dramatic beats into scenes, then camera coverage

[Previous: Model responses](03-prompts-and-responses.md) | [Course map](README.md) | [Next: Tools and agents](05-tools-and-agents.md)

**Today:** understand two different writing jobs: expanding a story into screenplay action, and dividing that action into shots.

Use the main project whose story you saved in Lesson 3. Do these steps **before creating render or export jobs**.

## 1. Ask what the scene needs to accomplish

For our "Mira hears the stranger" beat, define:

```text
At the start: Mira is about to leave alone.
Scene objective: decide whether to respond to the call.
Obstacle: the stranger is separated from the exit.
Visible choice: Mira turns back and raises the lantern.
At the end: she is committed to helping.
```

A scene should not merely repeat its beat title in a longer paragraph. It should make the change playable: who moves, who speaks, what the viewer discovers, and where attention goes.

An **illustrative screenplay moment**:

```text
INT. FLOODED STATION - NIGHT

Mira stops at the exit stairs. A hand waves beyond the submerged
benches. She looks toward the daylight above, then turns back
and lifts the brass lantern.

STRANGER: Over here!
MIRA: Follow the light.
```

`INT.` means interior; `EXT.` means exterior. The heading establishes place/time. Action describes visible events. Dialogue records spoken lines.

A useful distinction: **dialogue can carry intent; action can reveal the choice**. Having Mira explain her entire moral dilemma is usually less economical than showing her turn back.

## 2. Generate only the screenplay stage first

Call `POST /api/projects/{project_id}/generate-script` with:

```json
{"with_clips": false}
```

Then call `GET /api/projects/{project_id}/scenes`.

You should see four scenes, generated in two chunks, and one default clip record per scene. Those clip paths should be null. No image/video inference has run.

Record one scene ID. We will record final clip IDs only after coverage replaces the defaults.

## 3. Trace the handoff through saved context

Open `generate_script` in [script_agent.py](../calliope-backend/src/calliope/agent/script_agent.py), then `build_script_chunk_messages` in [prompts.py](../calliope-backend/src/calliope/agent/prompts.py).

```text
read saved project + beats + characters + locations
    -> calculate required scene count from beat count
    -> ask for scenes 1-2
    -> validate IDs/count, assign ordering, save and commit
    -> ask for scenes 3-4 with previous_tail
    -> validate and save the next chunk
```

There is no invisible conversation between the story-writing model call and the script-writing call. Python reads the story and sends it again as context.

Inspect the two new LLM trace files. In `request.messages[1].content`, find:

| Field | First chunk | Second chunk |
|---|---|---|
| `start` | 1 | 3 |
| `count` | 2 | 2 |
| `story` | Saved story and entity IDs | Saved story and entity IDs again |
| `previous_tail` | Empty | The previous two generated scene dictionaries |

These are mini-specific behaviors. The larger application's chunking/context representation differs.

Chunking helps keep each response manageable and lets completed work be saved progressively. It also creates a continuity problem: a later chunk needs enough context to continue coherently.

**This is not RAG chunking.** We are dividing output-writing work, not embedding documents for semantic search.

## 4. Inspect a scene as data

An **illustrative scene draft**, with example entity IDs:

```json
{
  "order_index": 2,
  "heading": "INT. FLOODED STATION - NIGHT",
  "action": "Mira in her yellow raincoat looks toward the exit, then turns back and raises the brass lantern.",
  "dialog": "STRANGER: Over here!\nMIRA: Follow the light.",
  "duration_sec": 8,
  "character_ids": [21, 22],
  "location_id": 31
}
```

The code field is `dialog`, not `dialogue`. The generation response wraps scene objects in `{"scenes": [...]}`.

The script generator checks that referenced characters and location belong to the supplied project data. It assigns scene ordering itself, inserts scene rows, creates character links, and creates default clips.

IDs give **referential continuity**: the scene points to the same saved Mira. Descriptions support **visual continuity**: repeated appearances should retain her raincoat and braid. Neither guarantees that every model output will depict the same person correctly.

**Pause:** Does a correct `character_id` prove that the action paragraph mentions the right clothes? No. That is a separate content check.

## 5. Now ask a director's question: how do we show it?

**Coverage** is the set of shots that communicates the scene's action and dialogue. Choose a shot because it serves the viewer, not just because a list of shot names sounds cinematic.

| Shot choice | Useful purpose in our scene |
|---|---|
| Wide | Show the distance between Mira, the stranger, and the exit |
| Medium | Show Mira's turn and gesture clearly |
| Close-up | Emphasize the fading flame or a moment of hesitation |
| Insert | Show a small meaningful detail, such as the lantern handle tightening in her grip |

The mini's clip schema does not have a separate `shot_size` field. Put framing in `description`; the full application has a richer clip model.

Call `POST /api/projects/{project_id}/expand-clips` with:

```json
{}
```

Read the scenes again. The offline model produces two clips per scene; the live model may choose a different number. Each selected scene's old clip rows have been replaced.

Record the actual clip ID you want to render later. Do not reuse an ID copied before this operation.

## 6. Follow dialogue allocation precisely

Imagine the parent scene has:

```text
1. STRANGER: Over here!
2. MIRA: Follow the light.
```

These numbers count **nonempty dialogue lines**, starting at 1. They are not character IDs.

An **illustrative coverage draft**:

```json
{
  "clips": [
    {
      "description": "Wide view across the flooded platform as the stranger waves.",
      "dialog_lines_covered": [1],
      "duration_sec": 4
    },
    {
      "description": "Medium view of Mira turning back and lifting the lantern.",
      "dialog_lines_covered": [2],
      "duration_sec": 4
    }
  ]
}
```

In [coverage_agent.py](../calliope-backend/src/calliope/agent/coverage_agent.py), the code flattens all assignments and requires:

```python
sorted(covered) == list(range(1, len(lines) + 1))
```

For our two lines, the assignments must collectively be exactly `[1, 2]`. `[1, 1, 2]` duplicates a line; `[1]` misses one.

This is a **domain invariant**: a rule about the application's meaning, beyond JSON syntax.

It does not verify that the visual descriptions cover every action, or that a generated video will speak the lines. Later, `_clip_dialog` in [video_agent.py](../calliope-backend/src/calliope/agent/video_agent.py) selects the assigned text for a clip's prompt. The bundled video model still produces silent video.

## 7. Avoid two easy false conclusions

**"The scene duration adds up, therefore my film is that long."** Not yet. The writing prompt aims at eight seconds per scene; the stored values are model output, not measured footage. Clip duration constraints and actual workflow frame counts are additional, separate layers.

**"I changed a beat, therefore its scenes and clips changed."** No. Saved scenes and clips are outputs of earlier generation. They are not reactive formulas. Regeneration is an explicit operation, and the mini rejects full script regeneration once scenes exist.

Coverage is also blocked once **any job** exists for the project, even a failed or completed one. This simple guard prevents breaking render associations. Plan your coverage first.

## Small paper experiment

Take one returned scene and fill in:

```text
Scene begins with:
Scene ends with:
What changed:
Shot 1 helps the viewer understand:
Shot 2 helps the viewer feel or notice:
```

If the two shots do the same job, suggest a clearer alternative. If a shot introduces a new costume or location, mark the continuity problem.

## Debugger stop and checkpoint

Break before `_persist_scenes` and inspect the validated `draft.scenes`. On the second model request, inspect `written` and `previous_tail`. In coverage, inspect `lines`, `covered`, and the IDs returned by the next scene read.

**Why is "four scenes saved" not proof that the entire script tool finished successfully?**

<details>
<summary>Answer and reasoning</summary>

The scene chunks commit before later work finishes. With the default `with_clips=True`, the coverage pass can fail after all scenes are already saved. Earlier chunks also survive a later writing failure.

Inspect the tool/HTTP result and saved stage-specific data. Partial progress and overall completion are different facts.

</details>

Next, [Lesson 5](05-tools-and-agents.md) adds the model-controlled decision loop around these ordinary generation functions.
