import json


def build_story_messages(project: dict) -> list[dict]:
    return [
        {
            "role": "system",
            "content": (
                "Develop the user's story idea, not a different story. Write exactly four visual "
                "beats ordered 1..4, a logline, reusable characters and locations. Keep it brief."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "task": "story",
                    "project": project,
                    "required_beat_count": 4,
                }
            ),
        },
    ]


def build_script_chunk_messages(story: dict, start: int, count: int, previous: list) -> list[dict]:
    return [
        {
            "role": "system",
            "content": (
                "Write exactly count scenes starting at the 1-based start index. Use the story "
                "beats at those positions. Use ONLY the supplied character and location IDs. "
                "Write a heading, short visible action, and two short SPEAKER: dialogue lines "
                "separated by a newline. Aim for 8 seconds per scene. Continue previous_tail."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "task": "script",
                    "story": story,
                    "start": start,
                    "count": count,
                    "previous_tail": previous[-2:],
                }
            ),
        },
    ]


def build_coverage_messages(scene: dict) -> list[dict]:
    return [
        {
            "role": "system",
            "content": (
                "Split the scene into short shot clips. Each clip has a self-contained visual "
                "description, duration_sec 1..8, and dialog_lines_covered: the 1-based indices "
                "of nonempty dialogue lines it performs. Assign EVERY line exactly once across "
                "the clips; no omissions or repetitions. Use two clips when possible."
            ),
        },
        {"role": "user", "content": json.dumps({"task": "coverage", "scene": scene})},
    ]
