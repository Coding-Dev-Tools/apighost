"""Tests for parser edge cases: $ref resolution, dedup, invalid status codes, etc."""

import json
import tempfile
from apighost.parser import (
    _extract_example,
    _infer_type,
    _parse_parameters,
    _parse_responses,
    _resolve_ref,
    _resolve_schema_refs,
    get_param_pattern,
    load_spec,
    parse_spec,
)
from pathlib import Path

# --- _resolve_ref edge cases ---


def test_resolve_ref_missing_path_returns_empty():
    """When $ref points to a nonexistent path, return {}."""
    spec = {"components": {"schemas": {}}}
    result = _resolve_ref("#/components/schemas/Missing", spec)
    assert result == {}


def test_resolve_ref_valid_path():
    """Resolve a valid $ref through nested keys."""
    spec = {"components": {"schemas": {"Pet": {"type": "object"}}}}
    result = _resolve_ref("#/components/schemas/Pet", spec)
    assert result == {"type": "object"}


# --- _infer_type edge cases ---


def test_infer_type_empty_dict():
    """Empty schema dict defaults to 'string'."""
    assert _infer_type({}) == "string"


def test_infer_type_none():
    """None schema defaults to 'string'."""
    assert _infer_type(None) == "string"


def test_infer_type_ref():
    """Schema with $ref infers 'object'."""
    assert _infer_type({"$ref": "#/components/schemas/X"}) == "object"


# --- _resolve_schema_refs edge cases ---


def test_resolve_schema_refs_none():
    """None schema passes through."""
    assert _resolve_schema_refs(None, {}) is None


def test_resolve_schema_refs_empty_dict():
    """Empty schema dict passes through."""
    assert _resolve_schema_refs({}, {}) == {}


def test_resolve_schema_refs_nested_ref():
    """Recursively resolves $ref in a schema tree."""
    spec = {
        "components": {
            "schemas": {
                "Pet": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                }
            }
        }
    }
    schema = {"$ref": "#/components/schemas/Pet"}
    result = _resolve_schema_refs(schema, spec)
    assert result["type"] == "object"
    assert "properties" in result


def test_resolve_schema_refs_list_with_dicts():
    """Resolves refs inside list items that are dicts."""
    spec = {
        "components": {
            "schemas": {
                "Tag": {"type": "string"}
            }
        }
    }
    schema = {
        "type": "array",
        "items": [{"$ref": "#/components/schemas/Tag"}, {"type": "integer"}],
    }
    result = _resolve_schema_refs(schema, spec)
    assert result["items"][0] == {"type": "string"}
    assert result["items"][1] == {"type": "integer"}


def test_resolve_schema_refs_plain_values_preserved():
    """Non-dict, non-list values pass through unchanged."""
    schema = {"type": "string", "minLength": 1}
    result = _resolve_schema_refs(schema, {})
    assert result == {"type": "string", "minLength": 1}


# --- _parse_parameters edge cases ---


def test_parse_parameters_with_ref():
    """Parameters with $ref get resolved."""
    spec = {
        "components": {
            "parameters": {
                "limitParam": {
                    "name": "limit",
                    "in": "query",
                    "required": False,
                    "schema": {"type": "integer"},
                }
            }
        }
    }
    path_item = {
        "parameters": [{"$ref": "#/components/parameters/limitParam"}]
    }
    result = _parse_parameters(path_item, "/items", spec)
    assert len(result) == 1
    assert result[0].name == "limit"
    assert result[0].location == "query"


def test_parse_parameters_dedup_same_name():
    """Duplicate parameter names are deduplicated (first wins)."""
    path_item = {
        "parameters": [
            {"name": "limit", "in": "query", "required": False, "schema": {"type": "integer"}},
            {"name": "limit", "in": "query", "required": True, "schema": {"type": "integer"}},
        ]
    }
    result = _parse_parameters(path_item, "/items", {})
    assert len(result) == 1
    assert result[0].required is False  # first occurrence wins


def test_parse_parameters_no_params():
    """Path item with no parameters returns empty list."""
    result = _parse_parameters({}, "/items", {})
    assert result == []


# --- _parse_responses edge cases ---


def test_parse_responses_default_status():
    """'default' response maps to status code 0 (wildcard)."""
    responses_obj = {
        "default": {"description": "Unexpected error"}
    }
    result = _parse_responses(responses_obj, {})
    assert 0 in result
    assert result[0].description == "Unexpected error"


def test_parse_responses_invalid_status_skipped():
    """Non-numeric status codes are skipped."""
    responses_obj = {
        "2XX": {"description": "Should be skipped"},
        "200": {"description": "OK"},
    }
    result = _parse_responses(responses_obj, {})
    assert 200 in result
    assert 0 not in result  # "2XX" is not "default", so it's skipped


def test_parse_responses_with_ref():
    """Response $ref gets resolved."""
    spec = {
        "components": {
            "responses": {
                "NotFound": {
                    "description": "Not found",
                    "content": {"application/json": {"schema": {"type": "object"}}},
                }
            }
        }
    }
    responses_obj = {
        "404": {"$ref": "#/components/responses/NotFound"}
    }
    result = _parse_responses(responses_obj, spec)
    assert 404 in result
    assert result[404].description == "Not found"


def test_parse_responses_no_content():
    """Response with no content still creates a Response object."""
    responses_obj = {"200": {"description": "OK"}}
    result = _parse_responses(responses_obj, {})
    assert 200 in result
    assert result[200].schema_ref is None
    assert result[200].example is None


# --- _extract_example edge cases ---


def test_extract_example_none():
    """None schema returns None."""
    assert _extract_example(None) is None


def test_extract_example_default():
    """Falls back to 'default' when no 'example' key."""
    schema = {"default": 42}
    assert _extract_example(schema) == 42


def test_extract_example_nested_object():
    """Recursively extracts examples from object properties."""
    schema = {
        "type": "object",
        "properties": {
            "name": {"example": "Fluffy"},
            "age": {"default": 3},
        },
    }
    result = _extract_example(schema)
    assert result == {"name": "Fluffy", "age": 3}


def test_extract_example_array():
    """Extracts example from array items."""
    schema = {"type": "array", "items": {"example": "tag1"}}
    result = _extract_example(schema)
    assert result == ["tag1"]


def test_extract_example_enum():
    """Returns first enum value as example."""
    schema = {"enum": ["cat", "dog", "bird"]}
    assert _extract_example(schema) == "cat"


def test_extract_example_no_match():
    """Schema with no example/default/properties returns None."""
    schema = {"type": "string", "format": "date-time"}
    assert _extract_example(schema) is None


# --- load_spec edge cases ---


def test_load_spec_json():
    """Load a JSON spec file."""
    spec_data = {"openapi": "3.0.0", "info": {"title": "Test", "version": "1.0.0"}}
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as f:
        json.dump(spec_data, f)
        tmp = f.name
    try:
        result = load_spec(tmp)
        assert result["info"]["title"] == "Test"
    finally:
        Path(tmp).unlink()


def test_load_spec_yaml():
    """Load a YAML spec file."""
    import yaml

    spec_data = {"openapi": "3.0.0", "info": {"title": "YAML Test", "version": "1.0.0"}}
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yml", delete=False
    ) as f:
        yaml.dump(spec_data, f)
        tmp = f.name
    try:
        result = load_spec(tmp)
        assert result["info"]["title"] == "YAML Test"
    finally:
        Path(tmp).unlink()


# --- get_param_pattern edge cases ---


def test_get_param_pattern_no_params():
    """Path without parameters passes through unchanged."""
    assert get_param_pattern("/health") == "/health"


def test_get_param_pattern_multiple_params():
    """Multiple path params are all converted."""
    result = get_param_pattern("/users/{userId}/posts/{postId}/comments/{commentId}")
    assert result == "/users/<userId>/posts/<postId>/comments/<commentId>"


# --- parse_spec edge cases ---


def test_parse_spec_minimal():
    """Parse a minimal spec with no paths."""
    spec_data = {"openapi": "3.0.0", "info": {"title": "Empty", "version": "0.0.0"}}
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as f:
        json.dump(spec_data, f)
        tmp = f.name
    try:
        spec = parse_spec(tmp)
        assert spec.title == "Empty"
        assert spec.endpoints == []
    finally:
        Path(tmp).unlink()


def test_parse_spec_shared_parameters():
    """Shared path-level parameters propagate to operations."""
    spec_data = {
        "openapi": "3.0.0",
        "info": {"title": "Test", "version": "1.0.0"},
        "paths": {
            "/items/{itemId}": {
                "parameters": [
                    {"name": "itemId", "in": "path", "required": True, "schema": {"type": "string"}}
                ],
                "get": {
                    "operationId": "getItem",
                    "responses": {"200": {"description": "OK"}},
                },
                "delete": {
                    "operationId": "deleteItem",
                    "responses": {"200": {"description": "OK"}},
                },
            }
        },
    }
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as f:
        json.dump(spec_data, f)
        tmp = f.name
    try:
        spec = parse_spec(tmp)
        get_ep = [e for e in spec.endpoints if e.operation_id == "getItem"][0]
        del_ep = [e for e in spec.endpoints if e.operation_id == "deleteItem"][0]
        # Both inherit the shared path param
        assert any(p.name == "itemId" for p in get_ep.parameters)
        assert any(p.name == "itemId" for p in del_ep.parameters)
    finally:
        Path(tmp).unlink()


