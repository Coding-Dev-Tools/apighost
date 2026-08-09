"""OpenAPI 3.0/3.1 spec parser for APIGhost."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

from .schema import ApiSpec, Endpoint, Parameter, Response


def load_spec(path: str | Path) -> dict:
    """Load an OpenAPI spec from a YAML or JSON file.

    Raises FileNotFoundError for missing files and ValueError with the
    filename for malformed YAML/JSON, giving users actionable context
    instead of raw parser tracebacks.
    """
    path = Path(path)
    raw = path.read_text(encoding="utf-8")
    if path.suffix.lower() in (".yaml", ".yml"):
        try:
            return yaml.safe_load(raw)
        except yaml.YAMLError as exc:
            raise ValueError(f"Malformed YAML in {path}: {exc}") from exc
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Malformed JSON in {path}: {exc}") from exc


def _resolve_ref(ref: str, spec: dict) -> dict:
    """Resolve a local JSON Reference ($ref) within the spec.

    Only in-document refs (starting with ``#/``) are supported; external
    file/URL refs resolve to an empty schema rather than raising. JSON Pointer
    escape sequences (``~1`` -> ``/``, ``~0`` -> ``~``) are decoded per RFC 6901.
    """
    if not isinstance(ref, str) or not ref.startswith("#/"):
        return {}
    current: Any = spec
    for part in ref[2:].split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif isinstance(current, list):
            try:
                current = current[int(part)]
            except (ValueError, IndexError):
                return {}
        else:
            return {}
    return current if isinstance(current, dict) else {}


def _infer_type(schema: dict) -> str:
    """Infer a JSON Schema type from a schema object."""
    if not schema:
        return "string"
    if "$ref" in schema:
        return "object"
    return schema.get("type", "string")


def _resolve_schema_refs(
    schema: dict | None, spec: dict, _seen: frozenset[str] = frozenset()
) -> dict | None:
    """Recursively resolve all $ref pointers in a schema tree.

    Circular references (a schema that transitively references itself — common
    for tree, comment-thread, and category/sub-category models) are detected via
    ``_seen`` (the set of refs already resolved on the current path) and
    truncated to an empty schema instead of recursing forever. Without this
    guard a self-referential spec raised ``RecursionError`` and crashed parsing.
    """
    if not isinstance(schema, dict) or not schema:
        return schema

    # A schema that is (or contains) a $ref resolves to its target; per the
    # OpenAPI 3.0 spec any sibling keys alongside $ref are ignored.
    ref = schema.get("$ref")
    if isinstance(ref, str):
        if ref in _seen:
            # Circular ref on this resolution path — stop expanding.
            return {}
        return _resolve_schema_refs(_resolve_ref(ref, spec), spec, _seen | {ref})

    resolved: dict[Any, Any] = {}
    for key, value in schema.items():
        if isinstance(value, dict):
            resolved[key] = _resolve_schema_refs(value, spec, _seen)
        elif isinstance(value, list):
            resolved[key] = [
                _resolve_schema_refs(item, spec, _seen) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            resolved[key] = value
    return resolved


def _parse_parameters(path_item: dict, path: str, spec: dict) -> list[Parameter]:
    """Parse parameters from a path item (shared + operation)."""
    params: list[Parameter] = []
    seen: set = set()

    for param in path_item.get("parameters", []):
        resolved = param
        if "$ref" in param:
            resolved = _resolve_ref(param["$ref"], spec)
        name = resolved.get("name", "")
        if name not in seen:
            seen.add(name)
            params.append(
                Parameter(
                    name=name,
                    location=resolved.get("in", "query"),
                    required=resolved.get("required", False),
                    schema_ref=resolved.get("schema", {}),
                    example=resolved.get("example")
                    or resolved.get("schema", {}).get("example"),
                )
            )

    return params


def _parse_responses(responses_obj: dict, spec: dict) -> dict[int, Response]:
    """Parse response codes from an OpenAPI responses object."""
    result: dict[int, Response] = {}
    for status_str, resp in responses_obj.items():
        resolved = resp
        if "$ref" in resp:
            resolved = _resolve_ref(resp["$ref"], spec)

        status_code = 200
        if status_str == "default":
            status_code = 0  # wildcard
        else:
            try:
                status_code = int(status_str)
            except ValueError:
                continue

        content = resolved.get("content", {})
        content_type = "application/json"
        schema_ref = None
        example = None

        if content:
            content_type = list(content.keys())[0]
            media = content[content_type]
            schema_ref = _resolve_schema_refs(media.get("schema", {}), spec)
            example = media.get("example") or _extract_example(schema_ref)

        result[status_code] = Response(
            status_code=status_code,
            content_type=content_type,
            schema_ref=schema_ref,
            example=example,
            description=resolved.get("description", ""),
        )
    return result


def _extract_example(schema: dict | None) -> Any:
    """Extract or construct an example from a schema."""
    if not schema:
        return None
    if "example" in schema:
        return schema["example"]
    if "default" in schema:
        return schema["default"]
    if schema.get("type") == "object" and "properties" in schema:
        return {k: _extract_example(v) for k, v in schema["properties"].items()}
    if schema.get("type") == "array" and "items" in schema:
        return [_extract_example(schema["items"])]
    if "enum" in schema:
        return schema["enum"][0]
    return None


def parse_spec(path: str | Path) -> ApiSpec:
    """Parse an OpenAPI spec file into an ApiSpec model."""
    raw = load_spec(path)
    info = raw.get("info", {})
    spec = ApiSpec(
        title=info.get("title", "Untitled API"),
        version=info.get("version", "0.0.0"),
        description=info.get("description", ""),
        servers=[s.get("url", "") for s in raw.get("servers", [])],
        components=raw.get("components", {}),
        raw=raw,
    )

    # Parse paths
    paths = raw.get("paths", {})
    for path_pattern, path_item in paths.items():
        # Shared parameters
        shared_params = _parse_parameters(path_item, path_pattern, raw)

        for method in ("get", "post", "put", "delete", "patch", "head", "options"):
            operation = path_item.get(method)
            if not operation:
                continue

            op_only = _parse_parameters(operation, path_pattern, raw)
            # Per OpenAPI 3.x spec: operation params override path-level params with
            # the same (name, in) key — deduplicate keeping the operation's version.
            op_keys = {(p.name, p.location) for p in op_only}
            op_params = [p for p in shared_params if (p.name, p.location) not in op_keys] + op_only

            endpoint = Endpoint(
                path=path_pattern,
                method=method.upper(),
                operation_id=operation.get("operationId", ""),
                summary=operation.get("summary", ""),
                description=operation.get("description", ""),
                parameters=op_params,
                responses=_parse_responses(operation.get("responses", {}), raw),
                tags=operation.get("tags", []),
                security=operation.get("security"),
                deprecated=operation.get("deprecated", False),
            )

            # Request body
            if "requestBody" in operation:
                rb = operation["requestBody"]
                if "$ref" in rb:
                    rb = _resolve_ref(rb["$ref"], raw)
                content = rb.get("content", {})
                if content:
                    content_type = list(content.keys())[0]
                    endpoint.request_body_schema = _resolve_schema_refs(
                        content[content_type].get("schema", {}), raw
                    )

            spec.endpoints.append(endpoint)

    return spec


def get_param_pattern(path: str) -> str:
    """Convert OpenAPI path params to Flask route params.

    /users/{userId}/posts -> /users/<userId>/posts
    """
    return re.sub(r"\{(\w+)\}", r"<\1>", path)
