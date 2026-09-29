import asyncio
import json
from pathlib import Path, PurePosixPath
from urllib.parse import quote
from uuid import uuid4

import httpx

from calliope.comfyui.patcher import asset_path, patch_workflow, validate_workflow
from calliope.config import Settings

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
VIDEO_SUFFIXES = {".mp4", ".webm", ".mov", ".mkv", ".gif"}


class ComfyUIError(RuntimeError):
    pass


class ComfyUIClient:
    def __init__(self, settings: Settings, render_settings: dict | None = None):
        self.settings = settings
        self.options = render_settings or {
            "comfyui_base_url": settings.comfyui_base_url,
            "request_timeout_sec": settings.request_timeout_sec,
            "render_timeout_sec": settings.render_timeout_sec,
            "poll_interval_sec": settings.poll_interval_sec,
        }
        self.trace_dir: Path | None = None
        self.sequence = 0

    def _trace(self, label: str, value) -> None:
        if self.trace_dir is None:
            raise RuntimeError("Start render() before recording its HTTP trace.")
        self.sequence += 1
        path = self.trace_dir / f"{self.sequence:03d}-{label}.json"
        path.write_text(json.dumps(value, indent=2), encoding="utf-8")

    async def _json(self, client: httpx.AsyncClient, method: str, path: str, **kwargs) -> dict:
        self._trace(
            "request",
            {
                "method": method,
                "url": str(client.base_url.join(path)),
                **kwargs,
            },
        )
        response = await client.request(method, path, **kwargs)
        self._trace("response", {"status_code": response.status_code, "body": response.text})
        if response.is_error:
            raise ComfyUIError(
                f"ComfyUI {path} returned HTTP {response.status_code}: {response.text}"
            )
        value = response.json()
        if not isinstance(value, dict):
            raise ComfyUIError(f"ComfyUI {path} returned a non-object response")
        return value

    async def _validate_nodes(
        self,
        client: httpx.AsyncClient,
        graph: dict,
        uploaded_input: tuple[str, str] | None = None,
    ) -> None:
        node_types = {}
        for node_id, node in graph.items():
            class_type = node["class_type"]
            if class_type not in node_types:
                info = await self._json(client, "GET", f"/object_info/{quote(class_type, safe='')}")
                node_types[class_type] = info.get(class_type)
            info = node_types[class_type]
            if not isinstance(info, dict):
                raise ComfyUIError(f"Node {node_id}: ComfyUI does not provide '{class_type}'")
            if info.get("api_node"):
                raise ComfyUIError(f"Node {node_id}: external paid API nodes are not supported")
            inputs = info.get("input", {})
            if not isinstance(inputs, dict) or not isinstance(inputs.get("required", {}), dict):
                raise ComfyUIError(f"ComfyUI returned invalid input metadata for {class_type}")
            required = inputs.get("required", {})
            missing = required.keys() - node["inputs"].keys()
            if missing:
                raise ComfyUIError(
                    f"Node {node_id} ({class_type}) is missing inputs: {sorted(missing)}"
                )
            for name, specification in required.items():
                if not isinstance(specification, list) or not specification:
                    raise ComfyUIError(f"ComfyUI returned invalid metadata for {class_type}.{name}")
                value = node["inputs"][name]
                if (node_id, name) == uploaded_input:
                    continue
                if isinstance(value, list):
                    continue  # ComfyUI validates connection types when accepting /prompt.
                if specification and isinstance(specification[0], list):
                    if value not in specification[0]:
                        raise ComfyUIError(
                            f"Node {node_id} ({class_type}): {name}={value!r} is unavailable; "
                            "inspect this node's /object_info and choose an installed option"
                        )

    async def _upload_reference(
        self,
        client: httpx.AsyncClient,
        definition: dict,
        graph: dict,
        reference_paths: list[str],
    ) -> None:
        if "reference_node" not in definition:
            return
        if not reference_paths:
            raise ValueError("This workflow requires a reference image; generate assets first")
        path = asset_path(self.settings, reference_paths[0])
        if not path.is_file() or path.suffix.lower() not in IMAGE_SUFFIXES:
            raise ValueError("The reference must be an existing PNG, JPEG, or WebP mini asset")
        upload_name = f"calliope-learning-{uuid4().hex}{path.suffix.lower()}"
        self._trace(
            "upload-request",
            {
                "method": "POST",
                "path": "/upload/image",
                "source_path": str(path),
                "filename": upload_name,
                "overwrite": False,
            },
        )
        response = await client.post(
            "/upload/image",
            files={"image": (upload_name, path.read_bytes())},
            data={"type": "input", "overwrite": "false"},
        )
        self._trace(
            "upload-response",
            {
                "status_code": response.status_code,
                "body": response.text,
            },
        )
        response.raise_for_status()
        value = response.json()
        if (
            not isinstance(value, dict)
            or not isinstance(value.get("name"), str)
            or not isinstance(value.get("subfolder", ""), str)
        ):
            raise ComfyUIError("ComfyUI upload response is missing the image name")
        name = str(PurePosixPath(value.get("subfolder", "")) / value["name"])
        graph[definition["reference_node"]]["inputs"][definition["reference_input"]] = name

    async def _wait(self, client: httpx.AsyncClient, prompt_id: str) -> dict:
        timeout = self.options["render_timeout_sec"]
        try:
            async with asyncio.timeout(timeout):
                while True:
                    history = await self._json(
                        client,
                        "GET",
                        f"/history/{quote(prompt_id, safe='')}",
                    )
                    entry = history.get(prompt_id)
                    if entry is not None:
                        if not isinstance(entry, dict):
                            raise ComfyUIError("ComfyUI returned an invalid history entry")
                        status = entry.get("status", {})
                        if not isinstance(status, dict):
                            raise ComfyUIError("ComfyUI returned an invalid history status")
                        if not isinstance(status.get("messages", []), list):
                            raise ComfyUIError("ComfyUI returned invalid history status messages")
                        errors = [
                            message
                            for message in status.get("messages", [])
                            if isinstance(message, list)
                            and message
                            and message[0] in ("execution_error", "execution_interrupted")
                        ]
                        if errors or status.get("status_str") in ("error", "failed"):
                            raise ComfyUIError(
                                f"ComfyUI execution failed for {prompt_id}: "
                                f"{json.dumps(errors or status)}"
                            )
                        if status.get("completed") is True or (
                            entry.get("outputs") and status.get("completed") is not False
                        ):
                            return entry
                    await asyncio.sleep(self.options["poll_interval_sec"])
        except TimeoutError as exc:
            raise ComfyUIError(
                f"ComfyUI render {prompt_id} timed out after {timeout}s. "
                "The remote job may still finish; no shared-server interrupt was sent."
            ) from exc

    async def _download(
        self,
        client: httpx.AsyncClient,
        history: dict,
        kind: str,
        output_dir: Path,
    ) -> list[str]:
        outputs = history.get("outputs", {})
        if not isinstance(outputs, dict):
            raise ComfyUIError("ComfyUI history outputs must be an object")
        suffixes = IMAGE_SUFFIXES if kind == "image" else VIDEO_SUFFIXES
        paths, seen = [], set()
        for node_output in outputs.values():
            if not isinstance(node_output, dict):
                raise ComfyUIError("ComfyUI node output must be an object")
            for key in ("images", "gifs", "videos"):
                values = node_output.get(key, [])
                if not isinstance(values, list):
                    raise ComfyUIError(f"ComfyUI '{key}' output must be a list")
                for value in values:
                    if not isinstance(value, dict) or not isinstance(value.get("filename"), str):
                        raise ComfyUIError("ComfyUI output is missing its filename")
                    suffix = PurePosixPath(value["filename"]).suffix.lower()
                    if suffix not in suffixes:
                        continue
                    params = {
                        "filename": value["filename"],
                        "subfolder": value.get("subfolder", ""),
                        "type": value.get("type", "output"),
                    }
                    if not all(isinstance(item, str) for item in params.values()):
                        raise ComfyUIError("ComfyUI filename, subfolder, and type must be text")
                    identity = tuple(params.values())
                    if identity in seen:
                        continue
                    seen.add(identity)
                    self._trace(
                        "view-request",
                        {"method": "GET", "path": "/view", "params": params},
                    )
                    response = await client.get("/view", params=params)
                    is_text = response.headers.get("content-type", "").split(";")[0] in (
                        "application/json",
                        "text/html",
                        "text/plain",
                    )
                    if response.is_error or is_text or not response.content:
                        self._trace(
                            "view-response",
                            {
                                "status_code": response.status_code,
                                "body": response.text,
                            },
                        )
                    response.raise_for_status()
                    if not response.content:
                        raise ComfyUIError("ComfyUI returned an empty media file")
                    if is_text:
                        raise ComfyUIError("ComfyUI /view returned text instead of generated media")
                    path = output_dir / f"output-{len(paths) + 1}{suffix}"
                    path.write_bytes(response.content)
                    self._trace(
                        "view-response",
                        {
                            "status_code": response.status_code,
                            "content_type": response.headers.get("content-type"),
                            "bytes": len(response.content),
                            "raw_body_path": str(path),
                        },
                    )
                    paths.append(str(path))
        if not paths:
            raise ComfyUIError(
                f"ComfyUI finished without downloadable {kind} outputs. "
                "Use a saving/output node that reports images, videos, or gifs in /history."
            )
        return paths

    async def render(
        self,
        definition: dict,
        prompt: str,
        output_dir: Path,
        reference_paths: list[str] | None = None,
        job_id: int | None = None,
    ) -> list[str]:
        trace_name = f"comfyui-job-{job_id or 'manual'}-{uuid4().hex}"
        self.sequence = 0
        self.trace_dir = self.settings.data_dir / "traces" / trace_name
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        output_dir = asset_path(self.settings, output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        try:
            definition = validate_workflow(definition)
            graph = patch_workflow(definition, prompt, trace_name)
            async with httpx.AsyncClient(
                base_url=self.options["comfyui_base_url"].rstrip("/"),
                timeout=self.options["request_timeout_sec"],
                trust_env=False,
            ) as client:
                uploaded_input = None
                if "reference_node" in definition:
                    uploaded_input = (definition["reference_node"], definition["reference_input"])
                await self._validate_nodes(client, graph, uploaded_input)
                await self._upload_reference(client, definition, graph, reference_paths or [])
                submitted = await self._json(
                    client,
                    "POST",
                    "/prompt",
                    json={"prompt": graph, "client_id": uuid4().hex},
                )
                if submitted.get("error") or submitted.get("node_errors"):
                    raise ComfyUIError(f"ComfyUI rejected workflow nodes: {json.dumps(submitted)}")
                prompt_id = submitted.get("prompt_id")
                if not isinstance(prompt_id, str) or not prompt_id:
                    raise ComfyUIError("ComfyUI /prompt response is missing prompt_id")
                history = await self._wait(client, prompt_id)
                return await self._download(client, history, definition["kind"], output_dir)
        except (ComfyUIError, httpx.HTTPError, OSError, ValueError) as exc:
            raise ComfyUIError(f"{exc}\nRaw ComfyUI trace: {self.trace_dir}") from exc
