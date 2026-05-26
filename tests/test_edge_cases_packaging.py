"""Targeted edge-case and packaging config tests for APIGhost.

Covers uncovered paths and packaging config parity.
"""

from __future__ import annotations

import tomllib

from click.testing import CliRunner
from pathlib import Path

from apighost.cli import cli


class TestCLIEdgeCases:
    """Tests for CLI edge cases."""

    def test_cli_help(self):
        """CLI help exits 0."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0


class TestPackagingQuality:
    """Tests for py.typed packaging config."""

    def test_package_data_includes_py_typed(self):
        """pyproject.toml should have package-data config for py.typed."""
        pyproject = Path(__file__).parent.parent / "pyproject.toml"
        with open(pyproject, "rb") as f:
            data = tomllib.load(f)
        pkg_data = data.get("tool", {}).get("setuptools", {}).get("package-data", {})
        assert "apighost" in pkg_data, \
            "Expected [tool.setuptools.package-data] section for 'apighost'"
        assert "py.typed" in pkg_data["apighost"], \
            f"Expected 'py.typed' in package-data, got {pkg_data['apighost']}"

    def test_ruff_known_first_party(self):
        """ruff known-first-party should be ['apighost'], not ['*']."""
        pyproject = Path(__file__).parent.parent / "pyproject.toml"
        with open(pyproject, "rb") as f:
            data = tomllib.load(f)
        isort_cfg = data.get("tool", {}).get("ruff", {}).get("lint", {}).get("isort", {})
        kfp = isort_cfg.get("known-first-party", [])
        assert kfp == ["apighost"], f"known-first-party should be ['apighost'], got {kfp}"
