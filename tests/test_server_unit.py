"""Unit tests for server.py internals — _extract_path_params, _build_response_for_endpoint, _make_response."""

import json
from apighost.schema import ApiSpec, Endpoint, Response, Scenario
from apighost.server import (
    _build_response_for_endpoint,
    _extract_path_params,
    _make_response,
    create_app,
)

# ── _extract_path_params ──────────────────────────────────────────────────

class TestExtractPathParams:
    """Direct unit tests for _extract_path_params."""

    def test_single_param(self):
        result = _extract_path_params("/users/{id}", "/users/42")
        assert result == {"id": "42"}

    def test_multiple_params(self):
        result = _extract_path_params("/orgs/{org}/repos/{repo}", "/orgs/devforge/repos/apighost")
        assert result == {"org": "devforge", "repo": "apighost"}

    def test_no_params(self):
        result = _extract_path_params("/health", "/health")
        assert result == {}

    def test_trailing_slash(self):
        """Trailing slash on actual path should still match."""
        result = _extract_path_params("/users/{id}", "/users/42/")
        assert result == {"id": "42"}

    def test_no_match(self):
        """Completely different path should return empty dict."""
        result = _extract_path_params("/users/{id}", "/items/99")
        assert result == {}

    def test_param_with_hyphenated_value(self):
        """Path param values may contain hyphens."""
        result = _extract_path_params("/apps/{app_name}", "/apps/my-cool-app")
        assert result == {"app_name": "my-cool-app"}

    def test_param_with_dot_in_value(self):
        """Path param values may contain dots (e.g., versions)."""
        result = _extract_path_params("/releases/{version}", "/releases/v1.2.3")
        assert result == {"version": "v1.2.3"}

    def test_empty_path_segment_no_match(self):
        result = _extract_path_params("/users/{id}", "/users//")
        assert result == {}

    def test_extra_segments_no_match(self):
        """Path with extra segments beyond template should not match."""
        result = _extract_path_params("/users/{id}", "/users/42/extra")
        assert result == {}


# ── _make_response ─────────────────────────────────────────────────────────

class TestMakeResponse:
    """Direct unit tests for _make_response."""

    def setup_method(self):
        from flask import Flask
        self.app = Flask(__name__)

    def test_json_body(self):
        """Dict body should produce a JSON response."""
        with self.app.app_context():
            resp, status = _make_response(200, {"key": "value"})
            assert status == 200

    def test_string_body(self):
        """String body should produce a text response with the given content type."""
        with self.app.app_context():
            resp = _make_response(200, "plain text", content_type="text/plain")
            assert resp.status_code == 200
            assert resp.content_type.startswith("text/plain")

    def test_custom_status(self):
        """Custom status code should be preserved."""
        with self.app.app_context():
            resp, status = _make_response(418, {"error": "I'm a teapot"})
            assert status == 418


# ── _build_response_for_endpoint ───────────────────────────────────────────

class TestBuildResponseForEndpoint:
    """Direct unit tests for _build_response_for_endpoint."""

    def _make_endpoint(self, path="/test", method="GET", responses=None):
        return Endpoint(
            path=path,
            method=method,
            responses=responses or {},
        )

    def test_scenario_override(self):
        """Scenario override should take full precedence."""
        ep = self._make_endpoint(responses={200: Response(status_code=200, example={"default": "data"})})
        scenario = Scenario(name="override-test", overrides={"GET /test": {"status": 503, "body": {"error": "overloaded"}}})
        body, status = _build_response_for_endpoint(ep, scenario=scenario)
        assert status == 503
        assert body == {"error": "overloaded"}

    def test_scenario_override_no_body_key(self):
        """Scenario override with only status should default body to {}."""
        ep = self._make_endpoint()
        scenario = Scenario(name="status-only", overrides={"GET /test": {"status": 404}})
        body, status = _build_response_for_endpoint(ep, scenario=scenario)
        assert status == 404
        assert body == {}

    def test_no_response_definitions_fallback(self):
        """Endpoint with no response definitions should return a fallback message."""
        ep = self._make_endpoint()
        body, status = _build_response_for_endpoint(ep)
        assert status == 200
        assert "GET /test" in body.get("message", "")

    def test_example_used_when_present(self):
        """Response with an example should return the example directly."""
        example = {"id": 1, "name": "Example Pet"}
        ep = self._make_endpoint(responses={200: Response(status_code=200, example=example)})
        body, status = _build_response_for_endpoint(ep)
        assert body == example

    def test_schema_ref_used_when_no_example(self):
        """Response with schema_ref but no example should generate from schema."""
        schema = {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}
        ep = self._make_endpoint(responses={200: Response(status_code=200, schema_ref=schema)})
        body, status = _build_response_for_endpoint(ep)
        # generate_value should produce an object with a 'name' key
        assert isinstance(body, dict)
        assert "name" in body

    def test_scenario_not_matching_other_endpoint(self):
        ep = self._make_endpoint(path="/other")
        scenario = Scenario(name="wrong-endpoint", overrides={"GET /test": {"status": 500, "body": {"error": "nope"}}})
        body, status = _build_response_for_endpoint(ep, scenario=scenario)
        assert status != 500 or body != {"error": "nope"}


# ── Integration: create_app edge cases ─────────────────────────────────────

class TestCreateAppEdgeCases:
    """Integration-level edge case tests for create_app."""

    def test_empty_spec(self):
        """Spec with no endpoints should still serve home and health."""
        spec = ApiSpec(title="Empty", version="0.0.0")
        app = create_app(spec)
        client = app.test_client()

        resp = client.get("/")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["endpoints"] == []

        resp = client.get("/_apighost/health")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["endpoints"] == 0

    def test_method_not_allowed(self):
        """An endpoint registered for GET should reject POST."""
        spec = ApiSpec(
            title="Single",
            endpoints=[Endpoint(path="/items", method="GET", responses={200: Response(status_code=200)})],
        )
        app = create_app(spec)
        client = app.test_client()

        resp = client.get("/items")
        assert resp.status_code == 200

        resp = client.post("/items")
        assert resp.status_code == 405

    def test_home_includes_scenario_name(self):
        """Home route should show scenario name when provided."""
        spec = ApiSpec(title="Test", endpoints=[])
        scenario = Scenario(name="error-500")
        app = create_app(spec, scenario=scenario)
        client = app.test_client()

        resp = client.get("/")
        data = json.loads(resp.data)
        assert data["scenario"] == "error-500"

    def test_recorder_with_multiple_endpoints(self):
        """Recorder should capture interactions across multiple endpoints."""
        spec = ApiSpec(
            title="Multi",
            endpoints=[
                Endpoint(path="/a", method="GET", responses={200: Response(status_code=200)}),
                Endpoint(path="/b", method="GET", responses={200: Response(status_code=200)}),
            ],
        )
        from apighost.vcr import Recorder
        recorder = Recorder()
        app = create_app(spec, recorder=recorder)
        client = app.test_client()
        client.get("/a")
        client.get("/b")
        client.get("/a")

        assert recorder.count == 3
        paths = [i.request_path for i in recorder.interactions]
        assert paths == ["/a", "/b", "/a"]
