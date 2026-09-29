import copy
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from calliope.config import Settings

NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}")
SECRET_KEYS = re.compile(
    r"api.?key|access.?token|auth.?token|authorization|password|secret|credential", re.I
)


def workflow_path(directory: Path, name: str) -> Path:
    if not NAME.fullmatch(name):
        raise ValueError("Workflow names must contain only letters, digits, '-' and '_'")
    path = (directory / f"{name}.json").resolve()
    if not path.is_relative_to(directory.resolve()):
        raise ValueError("Workflow path is outside the workflow directory")
    return path


def asset_path(settings: Settings, value: str | Path) -> Path:
    path = Path(value)
    path = (path if path.is_absolute() else settings.assets_dir / path).resolve()
    if not path.is_relative_to(settings.assets_dir.resolve()):
        raise ValueError("Media paths must remain beneath the mini project's assets directory")
    return path


def _reject_credentials(value) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if SECRET_KEYS.search(str(key)) and item not in ("", None):
                raise ValueError("Workflows must not contain credentials or API keys")
            _reject_credentials(item)
    elif isinstance(value, list):
        for item in value:
            _reject_credentials(item)


def validate_workflow(definition: dict, kind: str | None = None) -> dict:
    if not isinstance(definition, dict):
        raise ValueError("A workflow definition must be a JSON object")
    if definition.get("kind") not in ("image", "video"):
        raise ValueError("Workflow kind must be 'image' or 'video'")
    if kind is not None and definition["kind"] != kind:
        raise ValueError(f"Choose a {kind} workflow, not a {definition['kind']} workflow")
    graph = definition.get("workflow")
    if not isinstance(graph, dict) or not graph:
        raise ValueError("workflow must be a nonempty ComfyUI API-format node graph")
    _reject_credentials(definition)
    clean = {}
    for node_id, node in graph.items():
        if not isinstance(node, dict) or not isinstance(node.get("inputs"), dict):
            raise ValueError(f"Node {node_id} must have an inputs object (use API format)")
        class_type = node.get("class_type")
        if not isinstance(class_type, str) or not class_type:
            raise ValueError(f"Node {node_id} needs a class_type")
        if any(name in class_type.lower() for name in ("krea", "minimax")):
            raise ValueError("Paid external API nodes are not supported; use local ComfyUI nodes")
        clean[str(node_id)] = {"class_type": class_type, "inputs": copy.deepcopy(node["inputs"])}
    result = {"kind": definition["kind"], "workflow": clean}
    for prefix in ("prompt", "reference"):
        node_id = definition.get(f"{prefix}_node")
        input_name = definition.get(f"{prefix}_input")
        if prefix == "reference" and node_id is None and input_name is None:
            continue
        if not isinstance(node_id, str) or node_id not in clean:
            raise ValueError(f"{prefix}_node must identify a node in the graph")
        if not isinstance(input_name, str) or input_name not in clean[node_id]["inputs"]:
            raise ValueError(f"{prefix}_input must identify an input on node {node_id}")
        if not isinstance(clean[node_id]["inputs"][input_name], str):
            raise ValueError(f"{prefix}_input must be a text input, not a node connection")
        result[f"{prefix}_node"] = node_id
        result[f"{prefix}_input"] = input_name
    for node_id, node in clean.items():
        for value in node["inputs"].values():
            if isinstance(value, list) and len(value) == 2 and isinstance(value[0], str):
                if value[0] not in clean or type(value[1]) is not int or value[1] < 0:
                    raise ValueError(f"Node {node_id} has an invalid node connection: {value}")
    return result


def load_workflow(settings: Settings, name: str, kind: str | None = None) -> dict:
    for directory in (settings.data_dir / "workflows", settings.workflow_dir):
        path = workflow_path(directory, name)
        if path.is_file():
            return validate_workflow(json.loads(path.read_text(encoding="utf-8")), kind)
    raise ValueError(
        f"Workflow '{name}' is missing. Register a local {kind or 'image/video'} API workflow "
        f"with POST /api/workflows/{name}; live mode never substitutes a simulated render."
    )


def patch_workflow(definition: dict, prompt: str, prefix: str) -> dict:
    graph = copy.deepcopy(definition["workflow"])
    graph[definition["prompt_node"]]["inputs"][definition["prompt_input"]] = prompt
    for node in graph.values():
        if "filename_prefix" in node["inputs"]:
            node["inputs"]["filename_prefix"] = f"calliope-learning/{prefix}"
    return graph


def render_payload(
    settings: Settings,
    kind: str,
    prompt: str,
    workflow_name: str,
    reference_paths: list[str] | None = None,
) -> dict:
    if kind not in ("image", "video") or not prompt.strip():
        raise ValueError("Render jobs require an image/video kind and a nonempty prompt")
    workflow_path(settings.data_dir / "workflows", workflow_name)
    url = urlsplit(settings.comfyui_base_url)
    if url.scheme not in ("http", "https") or not url.hostname or url.username or url.password:
        raise ValueError("ComfyUI base URL must be HTTP(S) without embedded credentials")
    if url.query or url.fragment:
        raise ValueError("ComfyUI base URL must not contain a query or fragment")
    return {
        "prompt": prompt,
        "workflow_name": workflow_name,
        "workflow": None if settings.offline else load_workflow(settings, workflow_name, kind),
        "reference_paths": [str(asset_path(settings, path)) for path in reference_paths or []],
        "mode": "simulated" if settings.offline else "live",
        "render_settings": {
            "comfyui_base_url": settings.comfyui_base_url,
            "request_timeout_sec": settings.request_timeout_sec,
            "render_timeout_sec": settings.render_timeout_sec,
            "poll_interval_sec": settings.poll_interval_sec,
        },
    }
