import json
import textwrap
from html import escape
from pathlib import Path


def render(kind: str, payload: dict, output_dir: Path) -> list[str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    if kind == "image":
        lines = textwrap.wrap(payload["prompt"], width=64)[:12]
        text = "".join(
            f'<text x="24" y="{84 + index * 24}">{escape(line)}</text>'
            for index, line in enumerate(lines)
        )
        path = output_dir / "simulated-image.svg"
        path.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="800" height="440">'
            '<rect width="100%" height="100%" fill="#e7eef5"/>'
            '<g font-family="sans-serif" font-size="18" fill="#152c42">'
            '<text x="24" y="40">SIMULATED IMAGE — no ComfyUI render</text>'
            f"{text}</g></svg>",
            encoding="utf-8",
        )
    elif kind == "video":
        path = output_dir / "simulated-storyboard.json"
        path.write_text(
            json.dumps(
                {
                    "mode": "simulated",
                    "format": "storyboard",
                    "notice": "This is a storyboard JSON document, not a playable video.",
                    "prompt": payload["prompt"],
                    "dialog": payload.get("dialog", ""),
                    "duration_sec": payload.get("duration_sec"),
                    "reference_paths": payload.get("reference_paths", []),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    else:
        raise ValueError(f"Unsupported simulated media kind: {kind}")
    return [str(path.resolve())]
