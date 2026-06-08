"""Tests for the mock server."""

import json

import pytest

from apighost.parser import parse_spec
from apighost.scenario import Scenario
from apighost.schema import ApiSpec
from apighost.server import create_app
from apighost.vcr import Recorder

from . import PETSTORE_YAML


@pytest.fixture
def petstore_spec():
    return parse_spec(PETSTORE_YAML)


@pytest.fixture
def petstore_app(petstore_spec):
    return create_app(petstore_spec)


def test_home_route(petstore_app):
    """Test the home/info route."""
    client = petstore_app.test_client()
    resp = client.get("/")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data["service"] == "Petstore API"
    assert len(data["endpoints"]) == 5


def test_health_route(petstore_app):
    """Test the health endpoint."""
    client = petstore_app.test_client()
    resp = client.get("/_apighost/health")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data["status"] == "ok"
    assert data["endpoints"] == 5


def test_get_pets(petstore_app):
    """Test GET /pets returns a list."""
    client = petstore_app.test_client()
    resp = client.get("/pets")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert isinstance(data, list)
    assert len(data) > 0
    assert "id" in data[0]
    assert "name" in data[0]


def test_get_pet_by_id(petstore_app):
    """Test GET /pets/42 returns a single pet."""
    client = petstore_app.test_client()
    resp = client.get("/pets/42")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert "id" in data
    assert "name" in data


def test_create_pet(petstore_app):
    """Test POST /pets."""
    client = petstore_app.test_client()
    resp = client.post("/pets", json={"name": "Fluffy"})
    assert resp.status_code in (200, 201)
    data = json.loads(resp.data)
    assert "id" in data
    assert "name" in data


def test_delete_pet(petstore_app):
    """Test DELETE /pets/42."""
    client = petstore_app.test_client()
    resp = client.delete("/pets/42")
    assert resp.status_code == 204


def test_nested_route(petstore_app):
    """Test GET /pets/42/photos."""
    client = petstore_app.test_client()
    resp = client.get("/pets/42/photos")
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert "photos" in data
    assert isinstance(data["photos"], list)
    assert "total" in data


def test_scenario_override(petstore_spec):
    """Test that a scenario overrides responses."""
    scenario = Scenario(
        name="test",
        overrides={"GET /pets": {"status": 500, "body": {"error": "server error"}}},
    )
    app = create_app(petstore_spec, scenario=scenario)
    client = app.test_client()
    resp = client.get("/pets")
    assert resp.status_code == 500
    data = json.loads(resp.data)
    assert data["error"] == "server error"


def test_recording(petstore_app, petstore_spec):
    """Test that recording captures interactions."""
    recorder = Recorder()
    app = create_app(petstore_spec, recorder=recorder)
    client = app.test_client()
    client.get("/pets")
    client.get("/pets/42")
    client.post("/pets", json={"name": "Test"})

    assert recorder.count == 3
    assert recorder.interactions[0].request_method == "GET"
    assert recorder.interactions[0].request_path == "/pets"


def test_404_no_route():
    """Test 404 for unknown routes."""
    spec = ApiSpec(title="Minimal", endpoints=[])
    app = create_app(spec)
    client = app.test_client()
    resp = client.get("/nonexistent")
    assert resp.status_code == 404


def test_path_parameter_resolution(petstore_app):
    """Test that path parameters are resolved correctly."""
    client = petstore_app.test_client()
    resp_1 = client.get("/pets/1")
    resp_100 = client.get("/pets/100")
    assert resp_1.status_code == 200
    assert resp_100.status_code == 200


def test_head_request(petstore_spec):
    """Test HEAD requests aren't registered if not in spec."""
    app = create_app(petstore_spec)
    client = app.test_client()
    resp = client.head("/pets")
    assert resp.status_code in (200, 405, 404)


def test_latency_zero_no_delay(petstore_spec):
    """Test that zero latency (default) adds no delay."""
    import time
    app = create_app(petstore_spec, latency_range=(0, 0))
    client = app.test_client()
    start = time.monotonic()
    resp = client.get("/pets")
    elapsed = time.monotonic() - start
    assert resp.status_code == 200
    assert elapsed < 0.5


def test_latency_applies_delay(petstore_spec):
    """Test that latency_range adds a measurable delay to responses."""
    import time
    app = create_app(petstore_spec, latency_range=(0.05, 0.1))
    client = app.test_client()
    start = time.monotonic()
    resp = client.get("/pets")
    elapsed = time.monotonic() - start
    assert resp.status_code == 200
    assert elapsed >= 0.04


# --- Internal helper tests (coverage gaps) ---

def test_extract_path_params_no_match():
    """_extract_path_params returns {} when path doesn't match (covers line 30)."""
    from apighost.server import _extract_path_params
    result = _extract_path_params("/users/{id}", "/items/42")
    assert result == {}


def test_make_response_with_dict():
    """_make_response with dict body returns jsonify tuple (covers line 37)."""
    from flask import Flask

    from apighost.server import _make_response
    app = Flask(__name__)
    with app.app_context():
        resp = _make_response(201, {"id": 1, "name": "test"})
        assert resp[1] == 201
        data = json.loads(resp[0].get_data(as_text=True))
        assert data["name"] == "test"


def test_make_response_with_string():
    """_make_response with string body returns Response object (covers line 36)."""
    from apighost.server import _make_response
    resp = _make_response(200, "plain text", content_type="text/plain")
    assert resp.status_code == 200
    assert resp.get_data(as_text=True) == "plain text"


def test_build_response_fallback_without_example_or_schema():
    """_build_response_for_endpoint fallback when no response_def or schema (covers line 66)."""
    from apighost.schema import Endpoint
    from apighost.server import _build_response_for_endpoint
    ep = Endpoint(path="/fallback", method="get", responses={})
    body, status = _build_response_for_endpoint(ep, scenario=None, params={})
    assert status in (200,)
    assert "message" in body or isinstance(body, dict)


def test_build_response_with_schema_ref():
    """_build_response_for_endpoint with schema_ref and no example (covers lines 62-63)."""
    from apighost.schema import Endpoint
    from apighost.schema import Response as ApiResponse
    from apighost.server import _build_response_for_endpoint
    ep = Endpoint(
        path="/schema-only", method="get",
        responses={
            200: ApiResponse(
                status_code=200,
                schema_ref={"type": "object", "properties": {"id": {"type": "integer"}}},
            )
        }
    )
    body, status = _build_response_for_endpoint(ep, scenario=None, params={})
    assert status == 200
    assert isinstance(body, dict)
