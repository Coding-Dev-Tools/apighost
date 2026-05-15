"""Tests for CLI commands."""

from click.testing import CliRunner
import pytest

from apighost.cli import cli
from . import PETSTORE_YAML


@pytest.fixture
def runner():
    return CliRunner()


def test_cli_version(runner):
    """Test --version flag."""
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "apighost" in result.output


def test_cli_info(runner):
    """Test 'apighost info' command."""
    result = runner.invoke(cli, ["info"])
    assert result.exit_code == 0
    assert "APIGhost" in result.output


def test_cli_generate(runner):
    """Test 'apighost generate' command."""
    result = runner.invoke(cli, ["generate", PETSTORE_YAML])
    assert result.exit_code == 0
    assert "Generated" in result.output


def test_cli_scenario_list(runner):
    """Test 'apighost scenario list' command."""
    result = runner.invoke(cli, ["scenario", "list"])
    assert result.exit_code == 0


def test_cli_scenario_create(runner):
    """Test 'apighost scenario create' command."""
    result = runner.invoke(cli, ["scenario", "create", "cli-test-scenario", "-d", "CLI test"])
    assert result.exit_code == 0
    assert "cli-test-scenario" in result.output


def test_cli_scenario_edit(runner):
    """Test 'apighost scenario edit' command."""
    result = runner.invoke(cli, [
        "scenario", "edit", "cli-test-scenario",
        "GET /pets", "--status", "404",
        "--body", '{"error":"not found"}',
    ])
    assert result.exit_code == 0
    assert "cli-test-scenario" in result.output


def test_cli_scenario_delete(runner):
    """Test 'apighost scenario delete' command."""
    result = runner.invoke(cli, ["scenario", "delete", "cli-test-scenario"])
    assert result.exit_code == 0


def test_cli_cassette_list(runner):
    """Test 'apighost cassette list' command."""
    result = runner.invoke(cli, ["cassette", "list"])
    assert result.exit_code == 0


def test_cli_serve_help(runner):
    """Test 'apighost serve --help'."""
    result = runner.invoke(cli, ["serve", "--help"])
    assert result.exit_code == 0
    assert "OpenAPI" in result.output
