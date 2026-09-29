# Lesson 1: Think like a storyteller before asking a model

[Course map](README.md) | [Next: Save the idea](02-project-and-state.md)

**Today:** turn a vague idea into a small story you can judge. No server required.

If we cannot say what makes our story work, we cannot tell whether an AI-generated answer is good. Fluent paragraphs and valid JSON can still describe a weak story.

## 1. Start with a situation, then introduce a choice

Compare these:

> A woman carries a lantern in a flooded station.

> A woman who could escape alone chooses to guide a stranger out before her lantern dies.

The first is a useful image. The second gives us a goal, an obstacle, a choice, and a possible loss. Those give the next event a reason to happen.

We will call our protagonist **Mira**. A protagonist is the central character whose pursuit and decisions organize the story; it does not mean that every shot must show her.

Fill in this **story brief**:

| Question | Our working answer |
|---|---|
| Who is this about? | Mira, a traveler with a brass lantern |
| What does she want now? | Reach the station exit |
| What interrupts that goal? | A stranded stranger calls for help |
| What does she choose? | Turn back instead of leaving alone |
| What makes the choice difficult? | Water, darkness, and a fading light |
| What is at stake? | Whether both people reach safety |
| What changes by the end? | An isolated traveler becomes someone another person can trust |

This is a planning aid, not an existing database schema. The mini app has no separate `stakes` or `theme` column. Put essential constraints into the `idea` when you want them available to generation.

## 2. Premise, logline, theme, genre, and tone are not synonyms

A **premise** is the central situation or possibility: a fading lantern becomes the only guide through a flooded station.

A **logline** compresses the story's dramatic engine into a sentence:

> When a stranger calls from a dark platform, a traveler must guide them through a flooded station before her lantern goes out.

A useful starting pattern is:

```text
When [disruption], [protagonist] must [goal] despite [obstacle],
or else [stakes].
```

Use the pattern to clarify, not to force every story into identical wording.

**Theme** is the idea the choices explore: perhaps courage is making room for someone else. The film need not have Mira announce that sentence. Her decision can express it.

**Genre** suggests the kind of experience and conventions: drama, mystery, comedy.
**Tone** is how the telling feels: tense, gentle, hopeful, unsettling.

The same rescue can be a tense drama or a warm adventure. "Drama" alone does not tell the model the lighting, pacing, or emotional texture you want.

## 3. Build causal beats, not a list of decorations

A **story beat** is a meaningful event, decision, discovery, or change. Here is our four-beat teaching outline:

| Beat | What happens | What changes? | Why the next beat follows |
|---|---|---|---|
| 1. The way out | Mira spots the station exit | Escape seems possible | She is about to leave when a voice interrupts |
| 2. The call | She locates a stranger across the platform | Her goal expands from "me" to "both of us" | She must guide the stranger rather than simply walk away |
| 3. The fading flame | The lantern dims while they move together | Their guide is becoming unreliable | Mira must commit to the final stretch |
| 4. Shared daylight | They reach the exit together | The external goal is resolved; trust has replaced isolation | The ending pays off her earlier choice |

Read between beats using **"because," "but," or "therefore."**

Now compare a weaker outline:

```text
There is a station.
There is a lantern.
There is a stranger.
There is an exit.
```

These are objects and locations. They do not yet explain movement, decisions, or consequences.

**Your turn:** write one sentence explaining what would be lost if beat 2 were removed. If the answer is "nothing important," that beat probably needs a stronger function.

## 4. A beat is not a scene, and a scene is not a shot

For beat 2:

```text
BEAT:
Mira chooses to help instead of leaving alone.

SCENE:
INT. FLOODED STATION - NIGHT
Mira stops at the exit stairs. A voice calls from the far platform.
She turns, lifts the lantern, and steps back into the station.
STRANGER: Over here!
MIRA: Follow the light.

SHOTS:
A wide view establishes the distance between the two people.
A closer view shows Mira turning back and lifting the light.
```

The **beat** explains dramatic change. The **scene** is what plays out in a screenplay unit. The **shots** choose what the camera shows so the viewer can understand and feel it.

The mini app uses one generated scene per saved beat as a teaching shortcut. That is not a screenwriting law. One real scene can contain several beats, and one major beat can unfold over several scenes.

Likewise, a change from a wide shot to a close-up does not automatically create a new screenplay scene.

## 5. Translate internal meaning into visible evidence

"Mira feels conflicted" tells a reader about an internal state. A video generator benefits from an observable action:

> Mira looks toward the exit, then back toward the stranger. Her hand tightens around the lantern handle. She turns away from the stairs.

The principle is not "never use emotion words." It is **give the image something concrete to show**.

Use a few reusable visual anchors:

| Element | Stable anchor | Variable action |
|---|---|---|
| Mira | Yellow raincoat, dark braid | Turns, lifts the lantern, looks back |
| Lantern | Dented brass, amber flame | Swings slightly, flickers |
| Station | Submerged benches, tiled walls | Reflections move with the water |

Stable descriptions help continuity. Repeating a name alone does not guarantee the same face or wardrobe in independently generated images.

The mini stores character and location descriptions, but no dedicated item records. The lantern must travel through the idea, beat descriptions, scene action, and prompts rather than through an `items` table.

## 6. Know what a 30-second idea can reasonably contain

A short concept needs economy: few characters, one main location, one understandable decision.

Do not ask the model for six new locations, a complicated backstory, and several speeches while also expecting a clear 30-second film.

The app's `target_duration` is not an editing system. In this mini, four scenes are requested with an approximate eight-second writing target, and the bundled video workflow later renders about 2.08 seconds per job. We will measure that difference rather than hiding it.

## Small exercise

Write these four lines before continuing:

```text
Mira wants:
But:
She chooses:
By the end:
```

Then rewrite "Mira becomes brave" as an action a silent shot could show.

<details>
<summary>A worked answer, not the only correct answer</summary>

Mira wants to leave the station. But a stranger needs help and the lantern is fading. She chooses to guide the stranger rather than leave alone. By the end, both reach the exit.

Visible evidence of courage: Mira pauses at the stairs, hears the call, and turns back with the lantern raised. We infer the emotional meaning from the choice and action.

</details>

## Checkpoint

**A model returns four beautifully worded beats, but Mira never makes a decision. Has it met our storytelling goal?**

<details>
<summary>Answer and reasoning</summary>

Not necessarily. It may meet the application's list-length requirement while missing the dramatic engine in our brief. Structural validity and narrative quality are separate evaluations.

We should identify the missing decision and improve the brief or prompt, not assume that more adjectives or a larger model will automatically fix it.

</details>

Carry your brief into [Lesson 2](02-project-and-state.md). It will become data before it becomes a model prompt.
