"""Targeted edge-case and packaging config tests for APIGhost.

Covers uncovered paths and packaging config parity.
"""

from __future__ import annotations

import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[import-not-found]
from click.testing import CliRunner

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
        assert any(k in pkg_data for k in ("apighost", "*")), (
            "Expected [tool.setuptools.package-data] section for 'apighost' or '*'"
        )
        # The key may be "apighost" or "*" — check whichever exists
        pkg_key = next(k for k in ("apighost", "*") if k in pkg_data)
        assert "py.typed" in pkg_data[pkg_key], (
            f"Expected 'py.typed' in package-data, got {pkg_data[pkg_key]}"
        )

    def test_ruff_known_first_party(self):
        """ruff known-first-party should be ['apighost'], not ['*']."""
        pyproject = Path(__file__).parent.parent / "pyproject.toml"
        with open(pyproject, "rb") as f:
            data = tomllib.load(f)
        isort_cfg = (
            data.get("tool", {}).get("ruff", {}).get("lint", {}).get("isort", {})
        )
        kfp = isort_cfg.get("known-first-party", [])
        assert kfp == ["apighost"], (
            f"known-first-party should be ['apighost'], got {kfp}"
        )
