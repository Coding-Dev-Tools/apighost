"""Regression tests for remaining coverage gaps.

Targets:
- parser.py:50-53  _resolve_ref list-index resolution (ValueError, IndexError)
- parser.py:233    requestBody with $ref
- vcr.py:41-45     _save_cassette cleanup on write failure
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from apighost.parser import _resolve_ref, parse_spec
from apighost.vcr import _atomic_write_json

# --- parser.py:50-53  _resolve_ref list-index edge cases ---


def test_resolve_ref_list_index_valid():
    """_resolve_ref resolves numeric index into a list."""
    spec = {"items": [{"name": "first"}, {"name": "second"}]}
    result = _resolve_ref("#/items/1", spec)
    assert result == {"name": "second"}


def test_resolve_ref_list_index_out_of_range():
    """_resolve_ref returns {} when list index exceeds length."""
    spec = {"items": [{"name": "only"}]}
    result = _resolve_ref("#/items/5", spec)
    assert result == {}


def test_resolve_ref_list_index_non_numeric():
    """_resolve_ref returns {} when list part is not an integer."""
    spec = {"items": [{"name": "only"}]}
    result = _resolve_ref("#/items/abc", spec)
    assert result == {}


def test_resolve_ref_nested_list_then_dict():
    """_resolve_ref traverses list -> dict correctly."""
    spec = {"paths": [{"get": {"summary": "list-get"}}]}
    result = _resolve_ref("#/paths/0/get", spec)
    assert result == {"summary": "list-get"}


# --- parser.py:233  requestBody with $ref ---


def test_parse_spec_request_body_with_ref(tmp_path):
    """parse_spec resolves requestBody.$ref to the component schema."""
    import yaml

    raw = {
        "openapi": "3.0.0",
        "info": {"title": "RefBody", "version": "1.0"},
        "paths": {
            "/widgets": {
                "post": {
                    "operationId": "createWidget",
                    "requestBody": {"$ref": "#/components/requestBodies/WidgetBody"},
                    "responses": {"200": {"description": "ok"}},
                }
            }
        },
        "components": {
            "requestBodies": {
                "WidgetBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {"color": {"type": "string"}},
                            }
                        }
                    }
                }
            }
        },
    }
    spec_file = tmp_path / "ref_body.yaml"
    spec_file.write_text(yaml.dump(raw), encoding="utf-8")
    spec = parse_spec(str(spec_file))
    create = spec.endpoints[0]
    assert create.request_body_schema is not None
    assert "properties" in create.request_body_schema
    assert "color" in create.request_body_schema["properties"]


# --- vcr.py:41-45  _save_cassette cleanup on failure ---


def test_atomic_write_json_cleans_up_on_replace_failure(tmp_path):
    """_atomic_write_json removes temp file when os.replace fails."""
    target = tmp_path / "fail-test.json"

    # Force os.replace to fail so the except branch runs
    with (
        patch("apighost.vcr.os.replace", side_effect=OSError("disk full")),
        pytest.raises(OSError, match="disk full"),
    ):
        _atomic_write_json(target, {"key": "value"})

    # Temp file must be cleaned up — check no .tmp files remain
    tmp_files = list(tmp_path.glob("*.tmp"))
    assert not tmp_files, f"temp files {tmp_files} were not cleaned up after failure"
