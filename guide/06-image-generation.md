# Lesson 6: Turn a visual intention into pixels

[Previous: Tools and agents](05-tools-and-agents.md) | [Course map](README.md) | [Next: Video and jobs](07-video-and-jobs.md)

**Today:** generate one real image and understand the model workflow behind it.

Keep your main project. Coverage should already be complete. Once we create jobs, the mini will refuse to replace that project's clip plans.

## 1. Give the image a storytelling job

Our lantern is not just an attractive object. It represents the fragile guide that lets Mira help someone else.

An image prompt should express observable choices:

```text
Subject: a dented brass lantern
Action/state: its small flame glows
Setting: a wooden bench in a flooded station
Framing: close view with the station visible behind
Lighting: warm amber light against a cool background
Style: cinematic photograph
```

Avoid asking for "the most emotional masterpiece ever" without specifying what should be visible. Style adjectives cannot replace subject, composition, and action.

A **positive prompt** describes what to produce. A **negative prompt** supplies conditioning associated with things to avoid. Neither is a guaranteed include/exclude filter.

## 2. Queue one image, then pause

Call `POST /api/jobs/projects/{project_id}/render`:

```json
{
  "kind": "image",
  "workflow_name": "image",
  "prompt": "Close view of a dented brass lantern glowing on a wooden bench inside an old flooded train station, warm amber light against cool blue reflections, cinematic photograph"
}
```

Save the returned job ID. Inspect:

```http
GET /api/jobs/{job_id}
```

You should see `status: "pending"`, a `payload`, and empty `output_paths`.

**Do not run the worker yet.** The saved job is a chance to inspect exactly what will be sent.

Look inside `payload.workflow`, `payload.prompt`, `payload.mode`, and `payload.render_settings`. This is a snapshot prepared by `render_payload` in [patcher.py](../calliope-backend/src/calliope/comfyui/patcher.py).

This direct image path does **not** ask the llama model to rewrite your prompt first.

## 3. Read the recipe as a graph

Open [image.json](../calliope-backend/workflows/image.json), or call `GET /api/workflows/image`.

The file has a wrapper (`kind`, prompt mapping) and an API workflow graph:

```text
CheckpointLoaderSimple
  -> model --------------------------+
  -> CLIP -> positive/negative text -+-> KSampler -> VAEDecode -> SaveImage
  -> VAE -------------------------------------------^
EmptyLatentImage ---------------------^
```

Read these actual nodes in order:

| Node | Role |
|---|---|
| `"4"`: `CheckpointLoaderSimple` | Load the installed SD1.5 checkpoint's model/text-encoder/VAE components |
| `"6"`: `CLIPTextEncode` | Encode the positive prompt into conditioning |
| `"7"`: `CLIPTextEncode` | Encode the negative prompt |
| `"5"`: `EmptyLatentImage` | Set the latent canvas size and batch count |
| `"3"`: `KSampler` | Use the model and conditioning to sample latent content |
| `"8"`: `VAEDecode` | Decode latent samples into image pixels |
| `"9"`: `SaveImage` | Save the produced image |

For example:

```json
{"clip": ["4", 1]}
```

In a node's inputs, this means **connect to output slot 1 of workflow node `"4"`**. It is not character ID 4, clip ID 1, or a pair of model tokens. Node connections describe dataflow.

The wrapper maps our prompt to node `"6"`'s `text` input. `patch_workflow` copies the graph, patches that text, and sets a job-specific filename prefix. It does not overwrite the negative prompt.

## 4. Build a useful mental model of image inference

This is a **conceptual explanation**, not a line-by-line implementation of Stable Diffusion:

```text
prompt text -> text encoder -> numeric conditioning
noise + latent canvas -> repeated model-guided sampling -> latent representation
latent representation -> VAE decoder -> pixels
```

An **embedding** is a numeric representation. Here the text encoder turns prompt information into numbers the image-generation pipeline can use.

A **latent** is a compressed working representation, not an RGB picture you can open. `EmptyLatentImage` sets its canvas; the sampler uses the seed/noise process. The empty-latent node alone does not paint the requested subject.

**Denoising** is the useful intuition for the sampling process: iteratively transform a noisy representation into content guided by the model and prompt. Modern generation families may use diffusion or flow-matching formulations; the image and video recipes should not be assumed to have identical mathematics.

**VAE** means variational autoencoder. The decoding component turns generated latent samples into pixels. It is not an LLM interpreting story meaning at the last moment.

**Checkpoint/weights** are trained parameters loaded for inference. A saved workflow is not a trained model; it is a recipe connecting model components and processing steps.

## 5. Distinguish the controls

The bundled image workflow currently uses 512x512, batch 1, seed 42, 20 Euler steps, and CFG 7.

| Control | Useful interpretation | Common misconception |
|---|---|---|
| Seed | Controls the sampling noise initialization | Same seed guarantees identical output across all hardware/software |
| Steps | Number of sampling iterations requested | Twenty steps means twenty LLM calls |
| CFG | Classifier-free guidance scale; changes conditioning guidance strength | Higher always means better prompt adherence and quality |
| Sampler | Numerical sampling method, here `euler` | All samplers behave identically at the same step count |
| Scheduler | How sampling levels/timesteps are arranged | It is the application's background-job scheduler |
| Width/height | Output/latent dimensions configured for the workflow | More pixels have no effect on memory or runtime |
| Denoise | Controls the portion/strength of the denoising process for the configured path | It is the model's confidence score |
| Precision/quantization | How model numbers are represented, affecting memory and potentially quality | FP8 or FP16 selects a story genre or image style |

The LLM's `temperature` and an image sampler's CFG are **different controls at different model boundaries**.

Keep defaults for your first run. Learn what each does by changing one at a time, not by moving six controls after every unsatisfying result.

## 6. Run the job and find the actual file

Inspect `GET /api/jobs` and ensure the pending job is the one you intend to run.

Call:

```http
POST /api/jobs/run-next
```

This request waits for one job's execution. On success, inspect `status: "done"` and `output_paths`.

Open the PNG at its returned path, or use `GET /api/assets/file` with that path as the `path` query parameter.

Follow the local execution in [worker.py](../calliope-backend/src/calliope/queue/worker.py) and [client.py](../calliope-backend/src/calliope/comfyui/client.py):

```text
claim pending job
    -> validate workflow/node availability
    -> submit POST /prompt
    -> receive remote prompt_id
    -> poll GET /history/{prompt_id}
    -> download output using GET /view
    -> save local bytes and mark job done
```

The local **job ID** and ComfyUI's **prompt ID** are different identifiers. The request/response traces preserve their relationship.

Find the new `traces/comfyui-job-.../` directory. Its numbered files preserve HTTP requests and replies. The final media response trace points to the downloaded raw file instead of embedding all image bytes in JSON.

## 7. Evaluate the image as a story asset

Do not start with "Is it pretty?" Ask:

```text
Is the main subject unmistakably a brass lantern?
Can I see the intended light?
Does the environment fit our station?
Does the composition direct attention to the meaningful detail?
Are there artifacts that would distract from the story?
```

A beautiful image of a lantern in a desert still fails our location requirement.

This generic render belongs to the project through its job. It does not automatically become a character reference or an item record.

To generate one saved character's reference image instead, call `POST /api/projects/{project_id}/generate-assets`:

```json
{"workflow_name": "image", "character_ids": [1], "location_ids": []}
```

Replace `1` with your character ID. Run that new job separately. The worker stores its path in `characters.sheet_path`.

The simple workflow may not create a polished multi-view sheet despite that field name. And the bundled video workflow does not automatically condition on this image. We will trace that distinction next.

## Controlled experiment: change only the seed

In live mode, get `GET /api/workflows/image`. Copy its complete response body into `POST /api/workflows/image-seed43`, changing only:

```text
workflow -> "3" -> inputs -> seed: 42 becomes 43
```

This is an edit instruction, not standalone JSON to submit. The registration body still needs the whole workflow wrapper and graph.

Submit the **same image prompt** with `workflow_name: "image-seed43"`, then run the new job. Compare composition and details.

Hold model, prompt, negative prompt, steps, sampler, and resolution fixed. You are observing variation under a changed seed, not proving that a new prompt is better. Identical-node results may also be cached by ComfyUI; a repeated HTTP submission does not prove every node was recomputed.

## Checkpoint

**A model generated the story. Why is another model needed to produce the image?**

<details>
<summary>Answer and reasoning</summary>

The story LLM produced language. The image workflow uses a text encoder, a generative image model, sampling, and decoding to produce pixels. The application passes useful text between these stages, but the outputs, components, and controls are different.

</details>

**Why did editing `image.json` after enqueueing not change the pending job?**

<details>
<summary>Answer and reasoning</summary>

The job captured its workflow at enqueue time. Inspect `payload.workflow`; it is the stored recipe that the worker will use. Enqueue a new job for the edited recipe.

</details>

Continue to [Lesson 7](07-video-and-jobs.md) with your selected clip ID and a clear distinction between text, latent representations, and files.
