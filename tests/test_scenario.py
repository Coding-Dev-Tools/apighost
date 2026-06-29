"""Tests for scenario management."""

import pytest

from apighost.scenario import (
    delete_scenario,
    list_scenarios,
    load_scenario,
    save_scenario,
)


def test_save_and_load_scenario():
    """Test roundtrip save/load scenario."""
    path = save_scenario(
        "test-scenario",
        "A test scenario",
        {
            "GET /users": {"status": 404, "body": {"error": "not found"}},
        },
    )
    assert path is not None

    sc = load_scenario("test-scenario")
    assert sc.name == "test-scenario"
    assert sc.description == "A test scenario"
    assert "GET /users" in sc.overrides
    assert sc.overrides["GET /users"]["status"] == 404


def test_list_scenarios():
    """Test listing scenarios."""
    save_scenario("list-test-1", "First")
    save_scenario("list-test-2", "Second")
    scenarios = list_scenarios()
    names = [s["name"] for s in scenarios]
    assert "list-test-1" in names
    assert "list-test-2" in names


def test_delete_scenario():
    """Test deleting a scenario."""
    save_scenario("delete-me", "To be deleted")
    assert delete_scenario("delete-me") is True
    assert delete_scenario("delete-me") is False  # already gone


def test_load_nonexistent_scenario():
    """Test loading nonexistent scenario raises."""
    with pytest.raises(FileNotFoundError):
        load_scenario("nonexistent-scenario-xyz")


def test_list_scenarios_skips_corrupted_json():
    """list_scenarios skips files with invalid JSON (covers lines 31-32)."""
    from apighost.scenario import SCENARIO_DIR

    save_scenario("good-scenario", "valid")
    # Write corrupted JSON
    bad_file = SCENARIO_DIR / "corrupted.json"
    bad_file.write_text("this is not json {{{")
    scenarios = list_scenarios()
    names = [s["name"] for s in scenarios]
    assert "good-scenario" in names
    assert "corrupted" not in names
    bad_file.unlink(missing_ok=True)
