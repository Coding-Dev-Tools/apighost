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
    # All these should work — path params extracted from URL
    resp_1 = client.get("/pets/1")
    resp_100 = client.get("/pets/100")
    assert resp_1.status_code == 200
    assert resp_100.status_code == 200


def test_head_request(petstore_spec):
    """Test HEAD requests aren't registered if not in spec."""
    app = create_app(petstore_spec)
    client = app.test_client()
    resp = client.head("/pets")
    # HEAD may work due to Flask auto-handling, but shouldn't fail
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
    # Zero latency should respond in under 0.5s
    assert elapsed < 0.5


def test_latency_applies_delay(petstore_spec):
    """Test that latency_range adds a measurable delay to responses."""
    import time
    # 50ms-100ms latency — small enough to be fast, large enough to measure
    app = create_app(petstore_spec, latency_range=(0.05, 0.1))
    client = app.test_client()
    start = time.monotonic()
    resp = client.get("/pets")
    elapsed = time.monotonic() - start
    assert resp.status_code == 200
    # Should take at least 50ms with latency applied
    assert elapsed >= 0.04  # small tolerance for timing variance
