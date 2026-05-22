"""Tests for 'apighost serve' and 'apighost replay' command paths.

These tests cover the CLI setup/parsing logic for serve and replay
without requiring a live server. The werkzeug run_simple is mocked
so server startup is skipped after all setup logic executes.
"""

import pytest
from apighost.cli import _on_shutdown, cli
from apighost.scenario import save_scenario
from apighost.schema import CassetteInteraction
from apighost.vcr import save_cassette
from click.testing import CliRunner
from pathlib import Path
from unittest.mock import MagicMock, patch

from . import PETSTORE_YAML


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture(autouse=True)
def cleanup_test_data():
    """Remove any test cassettes/scenarios created during tests."""
    yield
    for name in ["serve-test-cassette", "replay-serve-test"]:
        p = Path.home() / ".apighost" / "cassettes" / f"{name}.json"
        p.unlink(missing_ok=True)
    for name in ["serve-scenario-test", "serve-scenario-missing-test"]:
        p = Path.home() / ".apighost" / "scenarios" / f"{name}.json"
        p.unlink(missing_ok=True)


class TestServeSetup:
    """Tests for 'apighost serve' command setup phase (mocked server)."""

    @patch("werkzeug.serving.run_simple")
    def test_serve_parses_spec_and_starts(self, mock_run, runner):
        """Serve parses spec, prints endpoint count, and calls run_simple."""
        result = runner.invoke(cli, ["serve", PETSTORE_YAML])
        assert result.exit_code == 0
        assert "APIGhost" in result.output
        assert "Endpoints: 5" in result.output
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        # Default host and port
        assert call_args[0][0] == "127.0.0.1"
        assert call_args[0][1] == 8080

    @patch("werkzeug.serving.run_simple")
    def test_serve_custom_host_port(self, mock_run, runner):
        """Serve respects --host and --port options."""
        result = runner.invoke(cli, ["serve", PETSTORE_YAML, "--host", "0.0.0.0", "-p", "9999"])
        assert result.exit_code == 0
        call_args = mock_run.call_args
        assert call_args[0][0] == "0.0.0.0"
        assert call_args[0][1] == 9999

    @patch("werkzeug.serving.run_simple")
    def test_serve_with_scenario(self, mock_run, runner):
        """Serve loads a scenario and shows override count."""
        save_scenario("serve-scenario-test", "Test", {"GET /pets": {"status": 200, "body": {}}})
        result = runner.invoke(cli, ["serve", PETSTORE_YAML, "--scenario", "serve-scenario-test"])
        assert result.exit_code == 0
        assert "Scenario: serve-scenario-test" in result.output
        assert "1 overrides" in result.output

    @patch("werkzeug.serving.run_simple")
    def test_serve_scenario_not_found(self, mock_run, runner):
        """Serve prints warning when scenario doesn't exist."""
        result = runner.invoke(cli, ["serve", PETSTORE_YAML, "--scenario", "serve-scenario-missing-test"])
        assert result.exit_code == 0
        assert "not found" in result.output.lower()

    @patch("werkzeug.serving.run_simple")
    def test_serve_with_record(self, mock_run, runner):
        """Serve with --record sets up recorder and prints cassette name."""
        result = runner.invoke(cli, ["serve", PETSTORE_YAML, "--record"])
        assert result.exit_code == 0
        assert "Recording to cassette" in result.output

    @patch("werkzeug.serving.run_simple")
    def test_serve_with_record_custom_cassette_name(self, mock_run, runner):
        """Serve with --record --cassette-name uses custom name."""
        result = runner.invoke(cli, ["serve", PETSTORE_YAML, "--record", "--cassette-name", "my-rec"])
        assert result.exit_code == 0
        assert "my-rec" in result.output

    @patch("werkzeug.serving.run_simple")
    def test_serve_with_latency(self, mock_run, runner):
        """Serve with --latency creates app with latency range."""
        result = runner.invoke(cli, ["serve", PETSTORE_YAML, "--latency", "0.5"])
        assert result.exit_code == 0
        # The create_app call includes latency_range — verified by no crash

    @patch("werkzeug.serving.run_simple", side_effect=KeyboardInterrupt)
    def test_serve_keyboard_interrupt_shutdown(self, mock_run, runner):
        """Serve handles Ctrl+C gracefully (no recording to save)."""
        result = runner.invoke(cli, ["serve", PETSTORE_YAML])
        assert result.exit_code == 0
        assert "Server stopped" in result.output

    @patch("werkzeug.serving.run_simple", side_effect=RuntimeError("port in use"))
    def test_serve_server_error(self, mock_run, runner):
        """Serve handles server errors gracefully."""
        result = runner.invoke(cli, ["serve", PETSTORE_YAML])
        assert result.exit_code == 0
        assert "Server error" in result.output


class TestServeOnShutdown:
    """Tests for _on_shutdown helper."""

    def test_shutdown_no_recorder(self):
        """Shutdown with no recorder just prints stopped."""
        _on_shutdown(None, None, "test.yaml")  # Should not raise

    def test_shutdown_with_recorder_no_interactions(self):
        """Shutdown with recorder but 0 interactions doesn't save."""
        mock_recorder = MagicMock()
        mock_recorder.count = 0
        _on_shutdown(mock_recorder, "test-cassette", "test.yaml")
        mock_recorder.save.assert_not_called()

    def test_shutdown_with_recorder_saves(self):
        """Shutdown with recorded interactions saves the cassette."""
        mock_recorder = MagicMock()
        mock_recorder.count = 3
        mock_recorder.save.return_value = "/tmp/test-cassette.json"
        _on_shutdown(mock_recorder, "test-cassette", "test.yaml")
        mock_recorder.save.assert_called_once_with("test-cassette", "test.yaml")


class TestReplaySetup:
    """Tests for 'apighost replay' command setup phase."""

    @patch("werkzeug.serving.run_simple")
    def test_replay_with_real_cassette(self, mock_run, runner):
        """Replay loads cassette and sets up Flask app."""
        interaction = CassetteInteraction(
            request_method="GET",
            request_path="/test",
            request_headers={},
            request_body=None,
            response_status=200,
            response_headers={"Content-Type": "application/json"},
            response_body='{"ok": true}',
        )
        save_cassette("replay-serve-test", [interaction], "test.yaml")

        result = runner.invoke(cli, ["replay", "replay-serve-test"])
        assert result.exit_code == 0
        assert "replaying cassette" in result.output
        assert "Interactions: 1" in result.output
        mock_run.assert_called_once()

    @patch("werkzeug.serving.run_simple")
    def test_replay_custom_host_port(self, mock_run, runner):
        """Replay respects --host and --port options."""
        interaction = CassetteInteraction(
            request_method="GET",
            request_path="/test",
            request_headers={},
            request_body=None,
            response_status=200,
            response_headers={},
            response_body="ok",
        )
        save_cassette("replay-serve-test", [interaction], None)

        result = runner.invoke(cli, ["replay", "replay-serve-test", "-p", "9090", "--host", "0.0.0.0"])
        assert result.exit_code == 0
        call_args = mock_run.call_args
        assert call_args[0][0] == "0.0.0.0"
        assert call_args[0][1] == 9090

    @patch("werkzeug.serving.run_simple", side_effect=KeyboardInterrupt)
    def test_replay_keyboard_interrupt(self, mock_run, runner):
        """Replay handles Ctrl+C gracefully."""
        interaction = CassetteInteraction(
            request_method="GET",
            request_path="/test",
            request_headers={},
            request_body=None,
            response_status=200,
            response_headers={},
            response_body="ok",
        )
        save_cassette("replay-serve-test", [interaction], None)

        result = runner.invoke(cli, ["replay", "replay-serve-test"])
        assert result.exit_code == 0
        assert "Replay server stopped" in result.output

    def test_replay_missing_cassette(self, runner):
        """Replay with nonexistent cassette exits with error."""
        result = runner.invoke(cli, ["replay", "no-such-cassette-xyz-abc"])
        assert result.exit_code != 0
        assert "Error" in result.output or "not found" in result.output.lower()

    @patch("werkzeug.serving.run_simple")
    def test_replay_shows_spec_path(self, mock_run, runner):
        """Replay displays original spec path if available."""
        interaction = CassetteInteraction(
            request_method="GET",
            request_path="/test",
            request_headers={},
            request_body=None,
            response_status=200,
            response_headers={},
            response_body="ok",
        )
        save_cassette("replay-serve-test", [interaction], "my-spec.yaml")

        result = runner.invoke(cli, ["replay", "replay-serve-test"])
        assert result.exit_code == 0
        assert "my-spec.yaml" in result.output


class TestCassetteListEmpty:
    """Tests for cassette list when empty."""

    def test_cassette_list_no_cassettes(self, runner, monkeypatch):
        """Cassette list shows 'No cassettes found' when empty."""
        monkeypatch.setattr("apighost.cli.list_cassettes", lambda: [])
        result = runner.invoke(cli, ["cassette", "list"])
        assert result.exit_code == 0
        assert "No cassettes found" in result.output


class TestScenarioListEmpty:
    """Tests for scenario list when empty."""

    def test_scenario_list_no_scenarios(self, runner, monkeypatch):
        """Scenario list shows message when empty."""
        monkeypatch.setattr("apighost.cli.list_scenarios", lambda: [])
        result = runner.invoke(cli, ["scenario", "list"])
        assert result.exit_code == 0
        assert "No scenarios found" in result.output
