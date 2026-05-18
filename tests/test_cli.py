"""Tests for CLI commands."""

import pytest
from apighost.cli import cli
from click.testing import CliRunner

from . import PETSTORE_YAML


@pytest.fixture
def runner():
    return CliRunner()


class TestVersion:
    """Tests for --version flag."""

    def test_cli_version(self, runner):
        """Test --version flag."""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "apighost" in result.output


class TestHelp:
    """Tests for --help on various commands."""

    def test_cli_help(self, runner):
        """Test main --help."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "serve" in result.output
        assert "record" in result.output
        assert "replay" in result.output
        assert "scenario" in result.output
        assert "cassette" in result.output
        assert "generate" in result.output
        assert "info" in result.output

    def test_cli_serve_help(self, runner):
        """Test 'apighost serve --help'."""
        result = runner.invoke(cli, ["serve", "--help"])
        assert result.exit_code == 0
        assert "OpenAPI" in result.output

    def test_cli_record_help(self, runner):
        """Test 'apighost record --help'."""
        result = runner.invoke(cli, ["record", "--help"])
        assert result.exit_code == 0
        assert "record" in result.output.lower()

    def test_cli_replay_help(self, runner):
        """Test 'apighost replay --help'."""
        result = runner.invoke(cli, ["replay", "--help"])
        assert result.exit_code == 0
        assert "Replay" in result.output

    def test_cli_generate_help(self, runner):
        """Test 'apighost generate --help'."""
        result = runner.invoke(cli, ["generate", "--help"])
        assert result.exit_code == 0
        assert "Generate" in result.output or "generate" in result.output

    def test_cli_scenario_help(self, runner):
        """Test 'apighost scenario --help'."""
        result = runner.invoke(cli, ["scenario", "--help"])
        assert result.exit_code == 0
        assert "create" in result.output
        assert "list" in result.output
        assert "edit" in result.output
        assert "delete" in result.output

    def test_cli_cassette_help(self, runner):
        """Test 'apighost cassette --help'."""
        result = runner.invoke(cli, ["cassette", "--help"])
        assert result.exit_code == 0
        assert "list" in result.output
        assert "info" in result.output


class TestInfo:
    """Tests for 'apighost info' command."""

    def test_cli_info(self, runner):
        """Test 'apighost info' command."""
        result = runner.invoke(cli, ["info"])
        assert result.exit_code == 0
        assert "APIGhost" in result.output
        assert "Cassettes" in result.output
        assert "Scenarios" in result.output


class TestGenerate:
    """Tests for 'apighost generate' command."""

    def test_cli_generate(self, runner):
        """Test 'apighost generate' with valid spec."""
        result = runner.invoke(cli, ["generate", PETSTORE_YAML])
        assert result.exit_code == 0
        assert "Generated" in result.output

    def test_cli_generate_missing_file(self, runner):
        """Test 'apighost generate' with missing file."""
        result = runner.invoke(cli, ["generate", "nonexistent.yaml"])
        assert result.exit_code != 0
        # Click should report the error about path not existing
        assert "does not exist" in result.output.lower() or "Error" in result.output

    def test_cli_generate_with_name(self, runner):
        """Test 'apighost generate' with custom name."""
        result = runner.invoke(cli, ["generate", PETSTORE_YAML, "-n", "my-gen-scenario"])
        assert result.exit_code == 0
        assert "my-gen-scenario" in result.output


class TestRecord:
    """Tests for 'apighost record' command."""

    def test_cli_record_missing_file(self, runner):
        """Test 'apighost record' with missing file."""
        result = runner.invoke(cli, ["record", "nonexistent.yaml"])
        assert result.exit_code != 0
        assert "does not exist" in result.output.lower() or "Error" in result.output


class TestReplay:
    """Tests for 'apighost replay' command."""

    def test_cli_replay_missing_cassette(self, runner):
        """Test 'apighost replay' with missing cassette."""
        result = runner.invoke(cli, ["replay", "nonexistent-cassette"])
        assert result.exit_code != 0
        # Should error about cassette not found
        assert "Error" in result.output or "not found" in result.output.lower()


class TestScenario:
    """Tests for 'apighost scenario *' commands."""

    SCENARIO_NAME = "cli-test-scenario"

    def test_cli_scenario_list(self, runner):
        """Test 'apighost scenario list'."""
        result = runner.invoke(cli, ["scenario", "list"])
        assert result.exit_code == 0

    def test_cli_scenario_create(self, runner):
        """Test 'apighost scenario create'."""
        result = runner.invoke(cli, ["scenario", "create", self.SCENARIO_NAME, "-d", "CLI test"])
        assert result.exit_code == 0
        assert self.SCENARIO_NAME in result.output

    def test_cli_scenario_create_no_description(self, runner):
        """Test 'apighost scenario create' without description."""
        result = runner.invoke(cli, ["scenario", "create", "no-desc-scenario"])
        assert result.exit_code == 0
        assert "no-desc-scenario" in result.output

    def test_cli_scenario_edit(self, runner):
        """Test 'apighost scenario edit'."""
        result = runner.invoke(cli, [
            "scenario", "edit", self.SCENARIO_NAME,
            "GET /pets", "--status", "404",
            "--body", '{"error":"not found"}',
        ])
        assert result.exit_code == 0
        assert self.SCENARIO_NAME in result.output

    def test_cli_scenario_edit_missing(self, runner):
        """Test 'apighost scenario edit' with nonexistent scenario."""
        result = runner.invoke(cli, [
            "scenario", "edit", "nonexistent-scenario-xyz",
            "GET /test", "--status", "200",
        ])
        assert result.exit_code != 0
        assert "not found" in result.output.lower()

    def test_cli_scenario_delete(self, runner):
        """Test 'apighost scenario delete'."""
        result = runner.invoke(cli, ["scenario", "delete", self.SCENARIO_NAME])
        assert result.exit_code == 0

    def test_cli_scenario_delete_nonexistent(self, runner):
        """Test 'apighost scenario delete' with nonexistent scenario."""
        result = runner.invoke(cli, ["scenario", "delete", "nonexistent-scenario-xyz"])
        assert result.exit_code == 0
        assert "not found" in result.output


class TestCassette:
    """Tests for 'apighost cassette *' commands."""

    def test_cli_cassette_list(self, runner):
        """Test 'apighost cassette list'."""
        result = runner.invoke(cli, ["cassette", "list"])
        assert result.exit_code == 0

    def test_cli_cassette_info_missing(self, runner):
        """Test 'apighost cassette info' with nonexistent cassette."""
        result = runner.invoke(cli, ["cassette", "info", "nonexistent-cassette-xyz"])
        assert result.exit_code != 0
        assert "Error" in result.output or "not found" in result.output.lower()


class TestServe:
    """Tests for 'apighost serve' command."""

    def test_cli_serve_missing_file(self, runner):
        """Test 'apighost serve' with missing file."""
        result = runner.invoke(cli, ["serve", "nonexistent.yaml"])
        assert result.exit_code != 0
        assert "does not exist" in result.output.lower() or "Error" in result.output

    def test_cli_serve_invalid_spec(self, runner, tmp_path):
        """Test 'apighost serve' with invalid spec content."""
        invalid_file = tmp_path / "invalid.yaml"
        invalid_file.write_text("not: valid: openapi: spec: broken")
        result = runner.invoke(cli, ["serve", str(invalid_file)])
        assert result.exit_code != 0
        assert "Error" in result.output or "error" in result.output.lower()
