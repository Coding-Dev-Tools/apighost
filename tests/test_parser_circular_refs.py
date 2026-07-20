"""Regression tests for circular/self-referential $ref resolution (parser.py).

Before the cycle guard in ``_resolve_schema_refs`` a spec whose schema
transitively referenced itself raised ``RecursionError`` and crashed
``parse_spec`` / ``apighost serve``. These tests pin the non-crashing behavior
and verify that legitimate (non-circular) refs still resolve fully.
"""

from __future__ import annotations

import json

from apighost.faker_utils import generate_value
from apighost.parser import _resolve_ref, _resolve_schema_refs, parse_spec


def _write(tmp_path, spec: dict):
    p = tmp_path / "spec.json"
    p.write_text(json.dumps(spec), encoding="utf-8")
    return p


def _spec(schemas: dict, response_ref: str) -> dict:
    return {
        "openapi": "3.0.0",
        "info": {"title": "T", "version": "1.0.0"},
        "paths": {
            "/x": {
                "get": {
                    "responses": {
                        "200": {
                            "description": "ok",
                            "content": {
                                "application/json": {"schema": {"$ref": response_ref}}
                            },
                        }
                    }
                }
            }
        },
        "components": {"schemas": schemas},
    }


def test_direct_self_reference_does_not_recurse(tmp_path):
    schemas = {
        "Node": {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "children": {
                    "type": "array",
                    "items": {"$ref": "#/components/schemas/Node"},
                },
            },
        }
    }
    spec = parse_spec(_write(tmp_path, _spec(schemas, "#/components/schemas/Node")))
    ep = spec.endpoints[0]
    resolved = ep.responses[200].schema_ref
    # Outer object is fully expanded; the recursive point is truncated.
    assert resolved["type"] == "object"
    assert resolved["properties"]["id"]["type"] == "integer"
    assert resolved["properties"]["children"]["type"] == "array"
    assert resolved["properties"]["children"]["items"] == {}
    # And fake data can be generated from it without blowing up.
    value = generate_value(resolved)
    assert isinstance(value, dict)


def test_mutual_recursion_does_not_recurse(tmp_path):
    schemas = {
        "A": {"type": "object", "properties": {"b": {"$ref": "#/components/schemas/B"}}},
        "B": {"type": "object", "properties": {"a": {"$ref": "#/components/schemas/A"}}},
    }
    spec = parse_spec(_write(tmp_path, _spec(schemas, "#/components/schemas/A")))
    resolved = spec.endpoints[0].responses[200].schema_ref
    assert resolved["properties"]["b"]["type"] == "object"
    # A -> B -> A closes the cycle and is truncated.
    assert resolved["properties"]["b"]["properties"]["a"] == {}


def test_non_circular_ref_used_twice_is_fully_resolved(tmp_path):
    """A shared (non-circular) ref appearing in sibling branches must resolve
    fully in *both* places — the cycle guard must be path-scoped, not global."""
    schemas = {
        "Addr": {"type": "object", "properties": {"city": {"type": "string"}}},
        "Person": {
            "type": "object",
            "properties": {
                "home": {"$ref": "#/components/schemas/Addr"},
                "work": {"$ref": "#/components/schemas/Addr"},
            },
        },
    }
    spec = parse_spec(_write(tmp_path, _spec(schemas, "#/components/schemas/Person")))
    resolved = spec.endpoints[0].responses[200].schema_ref
    for slot in ("home", "work"):
        assert resolved["properties"][slot]["properties"]["city"]["type"] == "string"


def test_resolve_ref_handles_external_and_missing_refs():
    # External/URL refs are unsupported -> empty schema, never an exception.
    assert _resolve_ref("https://example.com/x.yaml#/A", {}) == {}
    assert _resolve_ref("#/components/schemas/Missing", {"components": {}}) == {}


def test_resolve_ref_decodes_json_pointer_escapes():
    spec = {"paths": {"/a/b": {"note": "hit"}}}
    # ~1 decodes to '/', so this points at the "/a/b" key.
    assert _resolve_ref("#/paths/~1a~1b", spec) == {"note": "hit"}


def test_resolve_schema_refs_tolerates_non_dict_input():
    assert _resolve_schema_refs(None, {}) is None
    assert _resolve_schema_refs({}, {}) == {}


def test_recursion_limit_not_hit_on_deep_cycle(tmp_path):
    """Guard against RecursionError even with a low interpreter recursion limit."""
    import sys

    schemas = {
        "Loop": {
            "type": "object",
            "properties": {"next": {"$ref": "#/components/schemas/Loop"}},
        }
    }
    path = _write(tmp_path, _spec(schemas, "#/components/schemas/Loop"))
    old = sys.getrecursionlimit()
    sys.setrecursionlimit(200)
    try:
        spec = parse_spec(path)  # must not raise RecursionError
    finally:
        sys.setrecursionlimit(old)
    assert spec.endpoints
