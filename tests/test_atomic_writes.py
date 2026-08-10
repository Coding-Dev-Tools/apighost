"""Regression tests for atomic write behavior in save_cassette and save_scenario.

Hardening change: these functions should use tempfile + os.replace to prevent
corruption on interrupted writes. The observable outcomes are:
1. File exists and contains valid JSON after save
2. No temporary files are left behind
3. Concurrent saves don't produce partial/corrupt data
"""

from __future__ import annotations

import json
from pathlib import Path

from apighost.scenario import save_scenario
from apighost.vcr import CassetteInteraction, save_cassette


class TestSaveCassetteAtomic:
    """Verify save_cassette produces valid output with no temp file residue."""

    def test_save_cassette_produces_valid_json(self, tmp_path: Path) -> None:
        """Saved cassette must be parseable JSON with expected structure."""
        interactions = [
            CassetteInteraction(
                request_method="GET",
                request_path="/api/users",
                request_headers={"Accept": "application/json"},
                request_body=None,
                response_status=200,
                response_headers={"Content-Type": "application/json"},
                response_body='{"users": []}',
            )
        ]
        # Monkeypatch CASSETTE_DIR to tmp_path so we don't pollute real dir
        import apighost.vcr as vcr_module
        original_dir = vcr_module.CASSETTE_DIR
        vcr_module.CASSETTE_DIR = tmp_path
        try:
            result_path = save_cassette("atomic-test", interactions, "test-spec.yaml")
        finally:
            vcr_module.CASSETTE_DIR = original_dir

        saved = Path(result_path)
        assert saved.exists(), "Cassette file must exist after save"
        data = json.loads(saved.read_text(encoding="utf-8"))
        assert data["name"] == "atomic-test"
        assert len(data["interactions"]) == 1
        assert data["interactions"][0]["request"]["method"] == "GET"

    def test_save_cassette_no_temp_files_left(self, tmp_path: Path) -> None:
        """No .tmp or partial files should remain after a successful save."""
        interactions = [
            CassetteInteraction(
                request_method="POST",
                request_path="/api/items",
                request_headers={},
                request_body='{"item": "test"}',
                response_status=201,
                response_headers={},
                response_body='{"id": 1}',
            )
        ]
        import apighost.vcr as vcr_module
        original_dir = vcr_module.CASSETTE_DIR
        vcr_module.CASSETTE_DIR = tmp_path
        try:
            save_cassette("no-temp-test", interactions, "spec.yaml")
        finally:
            vcr_module.CASSETTE_DIR = original_dir

        # Only the final .json file should exist — no .tmp, .bak, or partial files
        all_files = list(tmp_path.iterdir())
        assert len(all_files) == 1, f"Expected exactly 1 file, found: {[f.name for f in all_files]}"
        assert all_files[0].suffix == ".json"


class TestSaveScenarioAtomic:
    """Verify save_scenario produces valid output with no temp file residue."""

    def test_save_scenario_produces_valid_json(self, tmp_path: Path) -> None:
        """Saved scenario must be parseable JSON with expected structure."""
        overrides = {
            "GET /api/health": {"status": 503, "body": {"error": "unavailable"}}
        }
        output_path = tmp_path / "custom-scenario.json"
        result_path = save_scenario(
            name="atomic-scenario",
            description="Test atomic write",
            overrides=overrides,
            output_path=str(output_path),
        )

        saved = Path(result_path)
        assert saved.exists(), "Scenario file must exist after save"
        data = json.loads(saved.read_text(encoding="utf-8"))
        assert data["name"] == "atomic-scenario"
        assert data["description"] == "Test atomic write"
        assert "GET /api/health" in data["overrides"]

    def test_save_scenario_no_temp_files_left(self, tmp_path: Path) -> None:
        """No .tmp or partial files should remain after a successful save."""
        output_path = tmp_path / "clean-scenario.json"
        save_scenario(
            name="clean-test",
            description="No temp residue",
            overrides={},
            output_path=str(output_path),
        )

        all_files = list(tmp_path.iterdir())
        assert len(all_files) == 1, f"Expected exactly 1 file, found: {[f.name for f in all_files]}"
        assert all_files[0].suffix == ".json"

    def test_save_scenario_default_dir_no_temp_files(self, tmp_path: Path) -> None:
        """When using default SCENARIO_DIR, no temp files should remain."""
        import apighost.scenario as scenario_module
        original_dir = scenario_module.SCENARIO_DIR
        scenario_module.SCENARIO_DIR = tmp_path
        try:
            save_scenario(name="default-dir-test", description="Testing default dir")
        finally:
            scenario_module.SCENARIO_DIR = original_dir

        all_files = list(tmp_path.iterdir())
        assert len(all_files) == 1, f"Expected exactly 1 file, found: {[f.name for f in all_files]}"
        assert all_files[0].suffix == ".json"
