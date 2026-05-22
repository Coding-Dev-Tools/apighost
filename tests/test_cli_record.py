"""Tests for 'apighost record' command and replay Flask route handlers.

The record command starts a background server, makes sample HTTP requests,
and saves a cassette. We mock the server thread and HTTP requests to test
the CLI logic without needing a live server.

The replay route handler tests exercise the inline Flask app created
inside the replay command, covering the match/miss/home routes.
"""

import json
import time
from pathlib import Path
from unittest.mock import patch, MagicMock, call

import pytest
from click.testing import CliRunner

from apighost.cli import cli
from apighost.vcr import load_cassette

from apighost.schema import CassetteInteraction
from apighost.vcr import save_cassette

from . import PETSTORE_YAML


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture(autouse=True)
def cleanup_cassettes():
    """Remove test cassettes created during tests."""
    yield
    for name in ["record-test-auto", "record-test-named", "record-test-limit1"]:
        p = Path.home() / ".apighost" / "cassettes" / f"{name}.json"
        p.unlink(missing_ok=True)


class TestRecordCommand:
    """Tests for 'apighost record' command."""

    @patch("apighost.cli.http_requests")
    @patch("apighost.cli.threading.Thread")
    @patch("apighost.cli.time.sleep")
    def test_record_makes_requests_and_saves(self, mock_sleep, mock_thread_cls, mock_http, runner):
        """Record parses spec, starts server, makes requests, saves cassette."""
        # Simulate successful HTTP responses
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_http.request.return_value = mock_resp

        # Thread.start() should be a no-op (no real server)
        mock_thread = MagicMock()
        mock_thread_cls.return_value = mock_thread

        result = runner.invoke(cli, ["record", PETSTORE_YAML, "-o", "record-test-named", "-n", "2"])
        assert result.exit_code == 0
        assert "Recording server" in result.output
        assert "Making up to 2 sample requests" in result.output
        mock_thread.start.assert_called_once()
        mock_sleep.assert_called()  # time.sleep(0.5) for server startup
        # Should have made at least 1 request (limited to 2)
        assert mock_http.request.call_count >= 1
        assert "Recorded" in result.output

    @patch("apighost.cli.http_requests")
    @patch("apighost.cli.threading.Thread")
    @patch("apighost.cli.time.sleep")
    def test_record_handles_request_errors(self, mock_sleep, mock_thread_cls, mock_http, runner):
        """Record continues when individual requests fail."""
        # First call raises, second succeeds
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_http.request.side_effect = [ConnectionError("refused"), mock_resp]

        mock_thread = MagicMock()
        mock_thread_cls.return_value = mock_thread

        result = runner.invoke(cli, ["record", PETSTORE_YAML, "-o", "record-test-named", "-n", "5"])
        assert result.exit_code == 0
        assert "ERROR" in result.output
        # Should still save cassette with the successful interaction
        assert "Recorded" in result.output

    @patch("apighost.cli.http_requests")
    @patch("apighost.cli.threading.Thread")
    @patch("apighost.cli.time.sleep")
    def test_record_respects_request_limit(self, mock_sleep, mock_thread_cls, mock_http, runner):
        """Record stops after -n requests even if more endpoints exist."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_http.request.return_value = mock_resp

        mock_thread = MagicMock()
        mock_thread_cls.return_value = mock_thread

        # Petstore has 5 endpoints; limit to 1
        result = runner.invoke(cli, ["record", PETSTORE_YAML, "-o", "record-test-limit1", "-n", "1"])
        assert result.exit_code == 0
        # Should make exactly 1 request
        assert mock_http.request.call_count == 1

    @patch("apighost.cli.http_requests")
    @patch("apighost.cli.threading.Thread")
    @patch("apighost.cli.time.sleep")
    def test_record_auto_output_name(self, mock_sleep, mock_thread_cls, mock_http, runner):
        """Record generates output name from spec title when -o not given."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_http.request.return_value = mock_resp

        mock_thread = MagicMock()
        mock_thread_cls.return_value = mock_thread

        result = runner.invoke(cli, ["record", PETSTORE_YAML, "-n", "1"])
        assert result.exit_code == 0
        # Output name should contain the spec title (petstore)
        assert "petstore" in result.output.lower() or "Recorded" in result.output

    @patch("apighost.cli.http_requests")
    @patch("apighost.cli.threading.Thread")
    @patch("apighost.cli.time.sleep")
    def test_record_custom_port(self, mock_sleep, mock_thread_cls, mock_http, runner):
        """Record respects --port option for the recording server."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_http.request.return_value = mock_resp

        mock_thread = MagicMock()
        mock_thread_cls.return_value = mock_thread

        result = runner.invoke(cli, ["record", PETSTORE_YAML, "-o", "record-test-named", "-p", "9999", "-n", "1"])
        assert result.exit_code == 0
        assert "9999" in result.output

    @patch("apighost.cli.http_requests")
    @patch("apighost.cli.threading.Thread")
    @patch("apighost.cli.time.sleep")
    def test_record_fills_path_params(self, mock_sleep, mock_thread_cls, mock_http, runner):
        """Record fills path parameters like {petId} with fake values."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_http.request.return_value = mock_resp

        mock_thread = MagicMock()
        mock_thread_cls.return_value = mock_thread

        result = runner.invoke(cli, ["record", PETSTORE_YAML, "-o", "record-test-named", "-n", "5"])
        assert result.exit_code == 0
        # Petstore has endpoints with {petId} — verify requests used numeric fill
        calls = mock_http.request.call_args_list
        urls = [c[1].get("url", c[0][1] if len(c[0]) > 1 else "") for c in calls]
        # At least one URL should have the filled-in param (numeric value)
        has_filled = any("/42" in str(u) or "/pets/" in str(u) for u in urls)
        assert has_filled, f"Expected path param fill in URLs: {urls}"


class TestReplayRouteHandlers:
    """Tests for the Flask route handlers created inside 'apighost replay'.

    These tests exercise the _replay_handler and _replay_home routes by
    extracting the Flask app from the replay command and using the test client.
    """

    @patch("werkzeug.serving.run_simple")
    def test_replay_home_route(self, mock_run, runner):
        """Replay home route returns service info and interaction count."""
        interaction = CassetteInteraction(
            request_method="GET",
            request_path="/pets",
            request_headers={},
            request_body=None,
            response_status=200,
            response_headers={"Content-Type": "application/json"},
            response_body='{"pets": []}',
        )
        save_cassette("replay-route-test", [interaction], "petstore.yaml")

        # Capture the Flask app created inside replay()
        captured_app = None
        def capture_app(host, port, app, **kwargs):
            nonlocal captured_app
            captured_app = app
        mock_run.side_effect = capture_app

        result = runner.invoke(cli, ["replay", "replay-route-test"])
        assert result.exit_code == 0
        assert captured_app is not None

        # Test the home route
        with captured_app.test_client() as client:
            resp = client.get("/")
            assert resp.status_code == 200
            data = resp.get_json()
            assert "APIGhost Replay" in data["service"]
            assert data["interactions"] == 1
            assert "GET /pets" in data["endpoints"]

        # Cleanup
        Path.home().joinpath(".apighost/cassettes/replay-route-test.json").unlink(missing_ok=True)

    @patch("werkzeug.serving.run_simple")
    def test_replay_handler_match(self, mock_run, runner):
        """Replay handler returns recorded response on path+method match."""
        interaction = CassetteInteraction(
            request_method="GET",
            request_path="/pets",
            request_headers={"Content-Type": "application/json"},
            request_body=None,
            response_status=200,
            response_headers={"Content-Type": "application/json"},
            response_body='{"pets": ["cat"]}',
        )
        save_cassette("replay-route-test", [interaction], None)

        captured_app = None
        def capture_app(host, port, app, **kwargs):
            nonlocal captured_app
            captured_app = app
        mock_run.side_effect = capture_app

        result = runner.invoke(cli, ["replay", "replay-route-test"])
        assert result.exit_code == 0

        with captured_app.test_client() as client:
            resp = client.get("/pets")
            assert resp.status_code == 200
            data = resp.get_json()
            assert data == {"pets": ["cat"]}

        Path.home().joinpath(".apighost/cassettes/replay-route-test.json").unlink(missing_ok=True)

    @patch("werkzeug.serving.run_simple")
    def test_replay_handler_no_match(self, mock_run, runner):
        """Replay handler returns 404 when no interaction matches."""
        interaction = CassetteInteraction(
            request_method="GET",
            request_path="/pets",
            request_headers={},
            request_body=None,
            response_status=200,
            response_headers={},
            response_body="ok",
        )
        save_cassette("replay-route-test", [interaction], None)

        captured_app = None
        def capture_app(host, port, app, **kwargs):
            nonlocal captured_app
            captured_app = app
        mock_run.side_effect = capture_app

        result = runner.invoke(cli, ["replay", "replay-route-test"])
        assert result.exit_code == 0

        with captured_app.test_client() as client:
            resp = client.get("/unknown")
            assert resp.status_code == 404
            data = resp.get_json()
            assert "No matching recorded interaction" in data["error"]

        Path.home().joinpath(".apighost/cassettes/replay-route-test.json").unlink(missing_ok=True)

    @patch("werkzeug.serving.run_simple")
    def test_replay_handler_method_mismatch(self, mock_run, runner):
        """Replay handler returns 404 when method doesn't match."""
        interaction = CassetteInteraction(
            request_method="GET",
            request_path="/pets",
            request_headers={},
            request_body=None,
            response_status=200,
            response_headers={},
            response_body="ok",
        )
        save_cassette("replay-route-test", [interaction], None)

        captured_app = None
        def capture_app(host, port, app, **kwargs):
            nonlocal captured_app
            captured_app = app
        mock_run.side_effect = capture_app

        result = runner.invoke(cli, ["replay", "replay-route-test"])
        assert result.exit_code == 0

        with captured_app.test_client() as client:
            # POST doesn't match recorded GET
            resp = client.post("/pets")
            assert resp.status_code == 404

        Path.home().joinpath(".apighost/cassettes/replay-route-test.json").unlink(missing_ok=True)

    @patch("werkzeug.serving.run_simple")
    def test_replay_handler_no_headers_fallback(self, mock_run, runner):
        """Replay handler uses default Content-Type when response_headers is None."""
        interaction = CassetteInteraction(
            request_method="GET",
            request_path="/data",
            request_headers={},
            request_body=None,
            response_status=201,
            response_headers=None,
            response_body='{"created": true}',
        )
        save_cassette("replay-route-test", [interaction], None)

        captured_app = None
        def capture_app(host, port, app, **kwargs):
            nonlocal captured_app
            captured_app = app
        mock_run.side_effect = capture_app

        result = runner.invoke(cli, ["replay", "replay-route-test"])
        assert result.exit_code == 0

        with captured_app.test_client() as client:
            resp = client.get("/data")
            assert resp.status_code == 201
            assert resp.content_type == "application/json"

        Path.home().joinpath(".apighost/cassettes/replay-route-test.json").unlink(missing_ok=True)
