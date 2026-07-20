"""Tests for parameter dedup / merge and array count correctness fixes.

Covers two correctness bugs fixed in one commit:
  1. parser.parse_spec: operation-level params must override path-level params
     with the same (name, in) key (OpenAPI 3.x spec compliance).
  2. faker_utils.generate_value for array type: count must be randomly chosen
     within [minItems, maxItems] rather than always pinned at the minimum.
"""

from __future__ import annotations

import textwrap

from apighost.faker_utils import generate_value
from apighost.parser import parse_spec

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_yaml(text: str, tmp_path):
    p = tmp_path / "spec.yaml"
    p.write_text(textwrap.dedent(text))
    return parse_spec(str(p))


# ---------------------------------------------------------------------------
# 1. Parameter merge: operation params override path-level params
# ---------------------------------------------------------------------------

SPEC_SHARED_ONLY = """
openapi: "3.0.0"
info:
  title: Test
  version: "1"
paths:
  /items/{id}:
    parameters:
      - name: id
        in: path
        required: true
        schema:
          type: string
    get:
      operationId: getItem
      responses:
        "200":
          description: ok
"""

SPEC_OP_OVERRIDE = """
openapi: "3.0.0"
info:
  title: Test
  version: "1"
paths:
  /items/{id}:
    parameters:
      - name: id
        in: path
        required: false
        schema:
          type: string
          description: path-level
    get:
      operationId: getItem
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: integer
            description: op-level override
      responses:
        "200":
          description: ok
"""

SPEC_OP_ADDS_NEW = """
openapi: "3.0.0"
info:
  title: Test
  version: "1"
paths:
  /items/{id}:
    parameters:
      - name: id
        in: path
        required: true
        schema:
          type: string
    get:
      operationId: getItem
      parameters:
        - name: filter
          in: query
          required: false
          schema:
            type: string
      responses:
        "200":
          description: ok
"""

SPEC_NO_OVERLAP = """
openapi: "3.0.0"
info:
  title: Test
  version: "1"
paths:
  /items:
    get:
      operationId: listItems
      parameters:
        - name: page
          in: query
          required: false
          schema:
            type: integer
      responses:
        "200":
          description: ok
"""


def test_shared_params_only_no_duplication(tmp_path):
    """Path-level params with no operation params -> no duplicates."""
    spec = _parse_yaml(SPEC_SHARED_ONLY, tmp_path)
    ep = spec.endpoints[0]
    names = [p.name for p in ep.parameters]
    assert names.count("id") == 1, f"Expected 1 'id' param, got: {names}"


def test_operation_param_overrides_path_param(tmp_path):
    """Operation-level param with same (name, in) must override, not duplicate."""
    spec = _parse_yaml(SPEC_OP_OVERRIDE, tmp_path)
    ep = spec.endpoints[0]
    id_params = [p for p in ep.parameters if p.name == "id" and p.location == "path"]
    assert len(id_params) == 1, f"Expected exactly 1 'id' path param, got {len(id_params)}"
    # The operation-level version (required=True) must win
    assert id_params[0].required is True, "Operation-level param (required=True) must override path-level (required=False)"


def test_operation_adds_new_param_alongside_shared(tmp_path):
    """Operation can add a new param without losing the shared path param."""
    spec = _parse_yaml(SPEC_OP_ADDS_NEW, tmp_path)
    ep = spec.endpoints[0]
    names = {p.name for p in ep.parameters}
    assert "id" in names, "Shared 'id' path param must be present"
    assert "filter" in names, "Operation-level 'filter' query param must be present"
    assert len(ep.parameters) == 2, f"Expected 2 params total, got {len(ep.parameters)}: {names}"


def test_no_path_params_no_duplication(tmp_path):
    """Operation-only params with no path-level params -> no duplication."""
    spec = _parse_yaml(SPEC_NO_OVERLAP, tmp_path)
    ep = spec.endpoints[0]
    names = [p.name for p in ep.parameters]
    assert names.count("page") == 1


# ---------------------------------------------------------------------------
# 2. Array count: random within [minItems, maxItems]
# ---------------------------------------------------------------------------

def test_array_respects_exact_count():
    """minItems == maxItems -> always that exact count."""
    schema = {"type": "array", "items": {"type": "string"}, "minItems": 3, "maxItems": 3}
    for _ in range(10):
        result = generate_value(schema)
        assert len(result) == 3, f"Expected 3 items, got {len(result)}"


def test_array_count_within_bounds():
    """Count must be within [minItems, maxItems]."""
    schema = {"type": "array", "items": {"type": "integer"}, "minItems": 2, "maxItems": 4}
    for _ in range(30):
        result = generate_value(schema)
        assert 2 <= len(result) <= 4, f"Array length {len(result)} outside [2, 4]"


def test_array_no_bounds_uses_positive_count():
    """No minItems/maxItems -> still produces at least 1 item."""
    schema = {"type": "array", "items": {"type": "string"}}
    for _ in range(10):
        result = generate_value(schema)
        assert len(result) >= 1


def test_array_large_maxitems_capped():
    """maxItems > 5 should be capped at 5 for practicality."""
    schema = {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 100}
    for _ in range(10):
        result = generate_value(schema)
        assert len(result) <= 5, f"Expected cap at 5, got {len(result)}"


def test_array_varied_counts():
    """With a range of [1, 5], generated counts should not ALL be the same (probabilistic)."""
    schema = {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 5}
    counts = set(len(generate_value(schema)) for _ in range(60))
    # With 60 draws over range [1,5], probability of all being same < (1/5)^59 ≈ 0
    assert len(counts) > 1, f"Expected varied counts over 60 draws, got: {counts}"
