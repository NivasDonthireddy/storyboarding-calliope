# Lesson 3: Your first real model request, explained slowly

[Previous: Save the idea](02-project-and-state.md) | [Course map](README.md) | [Next: Scenes and coverage](04-scenes-and-coverage.md)

**Today:** turn the saved brief into beats, while separating six things: a model, its input context, generated text, parsed JSON, validated data, and a good story.

## 1. What are we calling?

An **LLM** is a large language model. Its trained parameters let it predict continuations of supplied input. In this application, the useful continuation can be story text, structured JSON, or a tool request.

**Training** changes model parameters using examples. **Inference** uses an already-trained model to produce an answer. Our generation endpoint performs inference; it does not train a personal model on Mira.

The llama server is the **serving software**. The `model` alias chooses the trained model it serves. A llama.cpp-compatible server does not imply that every model behind it belongs to the Llama model family.

Open [config.py](../calliope-backend/src/calliope/config.py). `llm_base_url` and `llm_model` are separate settings. A model service and the FastAPI application are separate programs:

```text
your API request -> Mini Calliope Python -> model server -> model inference
                           <- HTTP response with generated output <-
```

## 2. Predict before sending

We will call `POST /api/projects/{project_id}/generate-story` with:

```json
{}
```

Why is the body empty? The project ID selects a saved brief. Python will read the title, idea, genre, tone, and duration; we do not need to paste them again.

Before executing, predict:

```text
Does the model receive the entire repository? No.
Does it directly insert database rows? No.
How many beats does the mini require? Four.
Will my exact sentences match another live run? Not necessarily.
```

Now execute it once. Read the returned story, then run `GET /api/projects/{project_id}/story` to inspect the saved version.

Record the opening beat ID, first character ID, and one location ID.

## 3. Inspect the actual prompt, not an imagined one

In the server console, find:

```text
LLM request/response trace: .../traces/llm-<request-id>.json
```

Open that exact file. For this course it is under:

```text
calliope-backend\data\course-live\traces
```

UUID filenames are not ordered conversation steps; use the filename printed for the request or file modification times.

Inspect these fields in order:

| Trace location | What you are looking at |
|---|---|
| `url` | The actual model HTTP endpoint |
| `request.model` | The requested model alias |
| `request.messages[0].content` | System instruction plus generated JSON Schema |
| `request.messages[1].content` | JSON-serialized task and project data |
| `response_text` | The model service's raw HTTP response body |
| `response.choices[0].message.content` | Generated story answer text inside the response envelope |
| `response.usage`, if supplied | Token accounting reported by the server |

A **prompt** is the input instructions/data. **Context** is all information supplied for this call, including the message list and, for later agent calls, tool definitions and observations.

The context is not "everything that ever happened." Here it is explicitly constructed by `build_story_messages` in [prompts.py](../calliope-backend/src/calliope/agent/prompts.py).

The `system` and `user` roles are protocol labels. In this structured generation path, Python builds both messages. The role `user` does not mean every character in that message was typed directly into chat by a human.

## 4. Understand the controls Python sends

Open `LLMClient._live_chat` in [llm.py](../calliope-backend/src/calliope/agent/llm.py). Its actual request includes:

```python
"temperature": 0.3,
"stream": False,
"max_tokens": 4096,
"chat_template_kwargs": {"enable_thinking": False},
```

| Setting/concept | Meaning | What it does not guarantee |
|---|---|---|
| Temperature | Influences sampling from the model's possible next outputs | Factuality, good plotting, or obedience |
| Token | A unit of model input/output, often part of a word | One token is not always one word or one JSON field |
| `max_tokens` | Requested output-generation limit | It is not the whole model's context-window size |
| Context window | Capacity for input plus generated sequence, subject to the serving configuration | Stored chat history is not automatically unlimited |
| `stream=False` | Wait for a complete response body in this mini | A slow response is not necessarily a dead program |
| `enable_thinking=False` | A llama chat-template request to disable that mode | It is not a guarantee about every server or an inspection of internal model cognition |

The client is asynchronous: `await client.post(...)` yields while waiting for I/O. That does not make your one request run all stages simultaneously, or let your IDE step into the remote model process.

Other model APIs may expose `top_p`, input/output seeds, or strict structured-output modes. This mini request does not explicitly configure them. Do not attribute a result to a control that was never sent.

## 5. Cross the text-to-data boundary

The HTTP envelope is JSON, but its `message.content` can itself be a **string containing JSON**.

An **illustrative fragment of generated answer text**:

```json
{
  "logline": "Mira must guide a stranger to the station exit before her lantern goes out.",
  "beats": [
    {
      "order_index": 1,
      "title": "The way out",
      "description": "Mira sees the exit stairs beyond the flooded platform."
    }
  ]
}
```

This fragment explains the shape; by itself it is **not a valid complete `StoryDraft`**. The real schema requires exactly four beats, characters, and locations too.

In `generate_structured`, follow:

```python
candidate = json.loads(content)
return schema.model_validate(candidate)
```

Those are actual source lines. The first turns JSON text into Python data. The second checks that data against the selected Pydantic model.

The helper also appends `schema.model_json_schema()` to the system prompt and sends that same schema in `response_format` with `type: "json_schema"` and `strict: true`. llama-server uses it to constrain the generated JSON structure. Python still checks the result with `model_validate` after the response.

**This is server-enforced JSON-schema output plus application validation.** It applies to story, script, and coverage generation, not agent tool-call requests. The client does not silently retry malformed replies or fall back if the server rejects the format. A valid JSON structure still does not guarantee good storytelling or identical wording between runs.

Compare:

| Candidate | Problem |
|---|---|
| `Here is a lovely story!` | Not JSON |
| `{"beats":"four"}` | JSON syntax is valid, but the data does not match `StoryDraft` |
| Four beats with missing character fields | Incomplete structure |
| Four valid beats that ignore Mira's choice | May pass structural validation but fail our story goal |

`StrictModel` rejects extra fields and limits coercion. `StoryDraft` checks the beat count. It does not prove that events are causal, appearances are consistent, or every requested story constraint was followed. Even beat ordering should be inspected; the field constraint alone is not a full sequence validator.

## 6. Find where the story becomes durable

Return to `generate_story` in [routers/story.py](../calliope-backend/src/calliope/routers/story.py).

After successful parsing/validation, Python inserts beats, characters, and locations in a transaction. SQLite assigns the IDs. Leaving the database context successfully commits the changes.

The generated `logline` replaces the saved `projects.idea`. There is no separate logline column here. Keep your original brief in your notebook for fair comparisons.

A repeated story-generation request is not a free "read latest story" operation. In this implementation, the model call happens **before** the existing-story conflict check, and the request can then return `409`. Use `GET /story` to read; use a new project to compare drafts.

## 7. Judge the output as a writer

Inspect your four beats against these questions:

```text
Is Mira's objective clear?
Does hearing the stranger change her course?
Does the fading lantern affect the action, not just the adjectives?
Does the ending resolve the goal?
Are there unsupported extra characters or locations?
Can we understand the choice from visible behavior?
```

A coherent answer matters more than matching our illustrative titles.

**Small experiment, on a new project:** copy the original brief, changing only the tone to "Quiet, warm, reassuring." Generate once and compare with the tense version. Keep the same model and code.

One sample per tone is a demonstration, not strong evidence that tone alone caused every difference. Model sampling adds variation. Later we will repeat controlled comparisons and score them using the same rubric.

## Debugger stop and checkpoint

Break at `_live_chat` just before the POST and inspect `payload`. Step over the request, then inspect `response.text`. Break at `schema.model_validate(candidate)` and compare the string response with the parsed dictionary.

**If a model returns flawless JSON but invents a helicopter rescue, which layer should detect the storytelling problem?**

<details>
<summary>Answer and reasoning</summary>

The JSON parser only checks syntax. Pydantic checks declared structure and constraints. Neither understands our complete narrative intent. Human review, explicit domain rules, or a separately evaluated critique step is needed to notice that the story abandoned the intended choice and setting.

Improve the brief or prompt with the missing constraint, then compare new drafts. Do not mistake lower temperature or valid JSON for a quality guarantee.

</details>

Keep the main project's story. [Lesson 4](04-scenes-and-coverage.md) will read those saved rows into a different model request.
