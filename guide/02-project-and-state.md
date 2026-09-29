# Lesson 2: Save the idea and establish your source of truth

[Previous: Story design](01-story-design.md) | [Course map](README.md) | [Next: Model responses](03-prompts-and-responses.md)

**Today:** follow one familiar FastAPI request into SQLite. We are still not asking a model to write anything.

## 1. Start the isolated course API

Use the [course setup command](README.md#set-up-once-in-lesson-2), then open **http://127.0.0.1:8012/docs**.

Run `GET /api/health`.

Expect `offline: false`, `worker: "manual"`, and a database path under:

```text
calliope-backend\data\course-live\playground.db
```

The health response describes configuration; it is not proof that either remote model service is reachable. A project save does not need those services.

## 2. Predict, then create

**Predict:** Will this action generate a plot, or only store our brief?

Call `POST /api/projects` with:

```json
{
  "title": "The Last Lantern",
  "idea": "Mira, a traveler in a yellow raincoat with a dark braid, can leave a flooded station alone. She turns back after hearing a stranded stranger. Carrying a dented brass lantern whose amber flame is fading, she must guide them both to the exit. Keep one station location and make her choice to help the center of the story.",
  "genre": "Drama",
  "tone": "Tense, then hopeful",
  "target_duration": "30 seconds"
}
```

Copy the returned **project ID** into your notebook. Every later `{project_id}` path parameter means this value, not necessarily `1`.

Run `GET /api/projects/{project_id}`. The saved fields should match your request.
Run `GET /api/projects/{project_id}/story`. Its beats, characters, and locations should still be empty.

**We have saved an idea, not generated a story.**

## 3. Trace five small pieces of Python

Open [routers/projects.py](../calliope-backend/src/calliope/routers/projects.py), at `create_project`.

| Code landmark | Meaning |
|---|---|
| `payload: ProjectCreate` | FastAPI parses and validates the body using a Pydantic model |
| `payload.model_dump()` | Convert that object to a dictionary |
| `INSERT INTO projects ...` | Insert its values into SQLite |
| `cur.lastrowid` | Obtain the ID assigned by SQLite |
| `read_project(...)` | Read the saved row for the response |

Now open [db.py](../calliope-backend/src/calliope/db.py), at `get_db`. In the mini, `with conn:` commits when the block succeeds and rolls back on an exception. The outer `finally` closes the connection.

This is why you do not see a separate `conn.commit()` in every mini route. It is a helper convention, not an AI behavior.

The router prefix is attached in [main.py](../calliope-backend/src/calliope/main.py), at `create_app`. That turns the route's empty `@router.post("")` path into `/api/projects`.

## 4. Distinguish identity, order, and content

Suppose you eventually have:

```text
project_id = 7
beat id = 41, order_index = 1
scene id = 58, order_index = 1
clip id = 93, order_index = 2, scene_id = 58
```

These are **illustrative IDs**.

`id` identifies a record. `order_index` places it in a sequence. The title and description are content.

Different tables can both have a row with ID `1`; they still represent different things. An agent needs real IDs from reads so it can select the intended records.

In [db.py](../calliope-backend/src/calliope/db.py), inspect the relationships:

```text
projects
  -> story_beats
  -> characters
  -> locations
  -> scenes
       -> scene_characters -> characters
       -> clips
            -> jobs may reference a clip
```

A character can appear in many scenes; a scene can contain many characters. The `scene_characters` table records that many-to-many relationship.

There is no mini `scenes.beat_id` link. The script generator connects beats to scenes through supplied context and its writing convention. Do not invent a database relationship that is not present.

## 5. Use a small failure to understand validation

Send a separate `POST /api/projects` request:

```json
{"title": "   ", "idea": "Find the exit."}
```

Expect **422**. `StrictModel` strips surrounding string whitespace, and `ProjectCreate.title` requires nonempty text. No project should be inserted for that request.

Now try `GET /api/projects/{project_id}` with an ID you have confirmed is absent. Expect **404**.

These mean different things:

| Status | Meaning here |
|---|---|
| 200 | This operation returned normally; inspect its body for what it actually did |
| 422 | The request data did not match the API's input model |
| 404 | The referenced record was not found |
| 409 | The current saved state conflicts with the requested operation |
| 502 | A model output/request failure surfaced through the mini model-error handler |

Later, an HTTP 200 can contain a job whose `status` is `failed`. HTTP success alone is not the definition of success for a multi-stage operation.

## Debugger stop

Use the [IDE setup](../README.md#set-up-your-ide-debugger), with parameters matching the course:

```text
serve --port 8012 --data-dir .\calliope-backend\data\course-live
```

That relative data path assumes the IDE working directory is **`learning-playground`**,
as the setup table specifies. The course's terminal `uv run` commands use that same folder.

Set a breakpoint at the SQL insert in `create_project`. Inspect `payload` before execution, then step over the insert and inspect `cur.lastrowid`.

If the breakpoint never triggers for the whitespace-only title, that is expected: FastAPI rejected the body before calling the handler.

## Checkpoint

**What survives closing the browser: the request object, the project row, or both?**

<details>
<summary>Answer and reasoning</summary>

The committed row is saved in SQLite and can be read in a later request. The particular Python `payload` object belongs to one request's execution; it is not the persistent project.

The future model will only know about this row if our code reads it and supplies information from it. Database persistence and model context are not the same thing.

</details>

Keep your project ID. [Lesson 3](03-prompts-and-responses.md) starts exactly where the LLM boundary begins.
