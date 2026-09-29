# Lesson 7: Render one story clip and follow its lifecycle

[Previous: Images](06-image-generation.md) | [Course map](README.md) | [Next: Experiments and capstone](08-experiments-and-capstone.md)

**Today:** understand how a saved shot plan becomes a short video, where continuity can break, and what export actually means in this mini.

## 1. Choose a small visual event

Pick one saved clip from `GET /api/projects/{project_id}/scenes`.

For a two-second learning render, a clear event such as **Mira slowly raises the lantern as reflections move across the water** is easier to judge than four cuts, a long conversation, and a complete rescue.

Three kinds of motion are different:

| Motion | Example |
|---|---|
| Subject | Mira raises her arm |
| Environment | Water ripples and the flame flickers |
| Camera | A slow push toward the lantern |

Combining too many instructions can make the output difficult to interpret. Camera motion is not a substitute for story action.

You cannot PATCH a clip's description through the mini's current API. To experiment with a new prompt without changing saved plans, use the generic `/render` endpoint; to follow the real scene-to-clip path, use the saved clip as described below. The full app has richer editing tools.

## 2. Prepare the saved clip's actual prompt

Call `POST /api/jobs/projects/{project_id}/generate-videos`:

```json
{"workflow_name": "video", "clip_ids": [5]}
```

`5` is only an example. Replace it with the selected clip ID from your current scene response.
Keep the scope to one clip.

Inspect the returned pending job's `payload.prompt`. Now open `enqueue_video_jobs` and `_clip_dialog` in [video_agent.py](../calliope-backend/src/calliope/agent/video_agent.py).

Python composes this prompt from:

```text
clip description and intended duration
parent scene's location
linked characters' names/appearances
only the dialogue lines allocated to this clip
project genre and tone
```

This composition is ordinary Python string-building. It is not an additional llama prompt-rewrite call in the mini.

The meaningful question is **what actually reached the video model?** An important constraint saved elsewhere cannot influence this call if it was not included or connected.

## 3. Inspect the text-to-video workflow

Open [video.json](../calliope-backend/workflows/video.json), or call `GET /api/workflows/video`.

| Component | Role in this recipe |
|---|---|
| Wan 2.2 TI2V 5B weights | The generative video model |
| UMT5 text encoder | Encode positive/negative prompt text into conditioning |
| Wan VAE | Decode generated latent video into frames |
| `Wan22ImageToVideoLatent` | Create the video latent layout; no start image is supplied here |
| `KSampler` | Run the configured model sampling |
| `CreateVideo`, `SaveVideo` | Package frames at the selected FPS and save an MP4 |

Although a node is named `CLIPLoader`, this workflow selects a Wan-compatible UMT5 text encoder. Node class names are interfaces; do not infer that every recipe uses the exact same text encoder as SD1.5.

Similarly, the latent node's name includes "ImageToVideo," but no start-image connection is present in this bundled graph. **The default recipe is text-to-video.**

## 4. Measure time instead of assuming it

The bundled settings are:

```text
width = 512
height = 320
length = 25 frames
fps = 12
sampling steps = 20
```

The nominal encoded duration is:

```text
25 / 12 = approximately 2.08 seconds
```

That is not automatically changed by `target_duration: "30 seconds"` or by a clip's stored `duration_sec`.

Keep three clocks separate:

| Clock | Meaning |
|---|---|
| Story/clip budget | How long the planned material is intended to take |
| Output duration | Frames divided by playback FPS, subject to container timing |
| Wall-clock generation time | How long inference, queue waiting, decoding, and download take |

A two-second output can require far more than two seconds of computation. A faster GPU affects wall-clock time, not the meaning of your story.

The bundled workflow produces **silent video**. Including `MIRA: Follow the light.` in a prompt does not add an audio track, guarantee speech, or ensure lip synchronization.

Do not simply choose arbitrary frame counts for future experiments; video model families can have frame-layout constraints. Begin with the working recipe and inspect supported node inputs before changing it.

## 5. Follow the saved job through execution

Inspect the queue, then call `POST /api/jobs/run-next`.

On success:

```text
job.status = "done"
job.output_paths = [actual local MP4 path]
selected clip.clip_path = that path
```

Read `GET /api/projects/{project_id}/scenes` again and open the MP4 from the selected clip.
The worker's `_attach` function in [worker.py](../calliope-backend/src/calliope/queue/worker.py) performs the database update.

Read `claim_next` in [manager.py](../calliope-backend/src/calliope/queue/manager.py):

```text
pending -> running -> done
                   -> failed
```

The database transaction claims a job before execution. This manual worker does one job per request. Calling `run-next` multiple times is not one request magically parallelizing itself.

The runner's chat turn and the render job are also different units. An agent can finish after queueing work while a video job remains pending.

## 6. Inspect continuity, not just file existence

Watch the clip twice:

```text
First pass: What event can I actually understand?
Second pass: What changes unexpectedly between frames?
```

Look for identity, wardrobe, object shape, direction of movement, lighting, and spatial relationships. These are **temporal and visual continuity** concerns. A valid MP4 does not prove they are good.

The miniature enqueue function gathers reference paths if character/location images exist. But `ComfyUIClient._upload_reference` uses them only when the registered definition has a reference mapping.

The bundled `video.json` has **no reference mapping**. Therefore generating a Mira image in Lesson 6 does not lock her face into the default video.

An optional registered image-to-video workflow can map a first reference image using `reference_node` and `reference_input`. That is conditioning, not fine-tuning. The mini adapter is single-reference and does not implement the full application's richer reference handling.

## 7. Failures are stages, not one generic "AI problem"

| Observation | First place to inspect |
|---|---|
| Job stays pending | Was `run-next` called? Is another earlier job being selected? |
| Workflow/model unavailable | Stored workflow and node-metadata trace |
| Submission rejected | Raw `/prompt` reply and `node_errors` |
| Remote execution failed | `/history/{prompt_id}` status/messages |
| Local timeout | Trace's prompt ID and last history response; remote work may continue |
| Job done, but wrong content | Actual prompt, model/workflow settings, and media quality |
| Video exists, but no sound | Expected behavior of this silent recipe |

The mini does not silently change live jobs into offline placeholders. Their recorded mode must match the worker's mode.

Do not interrupt or unload a shared ComfyUI server to "fix" one learning run. Inspect the specific job's trace. This mini does not implement automatic crash recovery or a per-job remote cancellation UI.

## 8. Export is a manifest here, not film assembly

Call:

```http
POST /api/jobs/projects/{project_id}/export
```

Then run the next job and open its JSON output.

In [export/runner.py](../calliope-backend/src/calliope/export/runner.py), `export_project` collects available clip files in scene/clip order and lists missing ones under `skipped_clips`.

If you planned eight clips but rendered one, you should normally find one available clip and seven skipped clips. A different live coverage count changes those numbers.

The generic lantern image does not appear as a video clip just because it belongs to the project. The export follows clip records with output paths.

The manifest's `duration_sec` values come from the stored clip budgets; this mini does not probe the actual MP4 to replace them with measured durations.

The larger application uses FFmpeg to assemble a movie. This mini deliberately stops at an inspectable manifest. Successful export of that manifest is not proof of a complete film.

## Checkpoint

**Why might a four-second clip plan produce a silent 2.08-second MP4 showing a different-looking Mira?**

<details>
<summary>Answer and reasoning</summary>

The bundled workflow fixes 25 frames at 12 FPS, has no audio-generation stage, and does not use a character reference image. The clip's text budget and character ID do not automatically change those workflow capabilities.

Inspect the actual graph and connections. More emphatic prompt wording cannot add a missing audio stage or reference-image connection.

</details>

You have followed a real idea-to-media path. [Lesson 8](08-experiments-and-capstone.md) turns that experience into a repeatable engineering and storytelling method.
