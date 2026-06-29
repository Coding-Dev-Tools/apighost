"""Tests for VCR cassette module."""

import pytest

from apighost.vcr import CassetteInteraction, Recorder, load_cassette


def test_recorder_basic():
    """Test basic recording."""
    r = Recorder()
    r.record("GET", "/api/users", {}, None, 200, {}, '[{"id":1}]')
    assert r.count == 1
    assert r.interactions[0].request_method == "GET"
    assert r.interactions[0].response_status == 200


def test_recorder_multiple():
    """Test recording multiple interactions."""
    r = Recorder()
    r.record("GET", "/users", {}, None, 200, {}, "[]")
    r.record("POST", "/users", {}, '{"name":"test"}', 201, {}, '{"id":1}')
    r.record("DELETE", "/users/1", {}, None, 204, {}, "")
    assert r.count == 3


def test_recorder_clear():
    """Test clearing a recorder."""
    r = Recorder()
    r.record("GET", "/test", {}, None, 200, {}, "")
    assert r.count == 1
    r.clear()
    assert r.count == 0


def test_recorder_strips_sensitive_headers():
    """Test that sensitive headers are stripped from recording."""
    r = Recorder()
    r.record(
        "GET",
        "/secure",
        {"Authorization": "Bearer xxx", "X-Custom": "ok"},
        None,
        200,
        {},
        "",
    )
    recorded = r.interactions[0]
    assert "authorization" not in recorded.request_headers
    assert "Authorization" not in recorded.request_headers
    assert recorded.request_headers.get("X-Custom") == "ok"


def test_save_and_load_cassette():
    """Test roundtrip save/load cassette."""
    r = Recorder()
    r.record("GET", "/test", {}, None, 200, {}, '"ok"')
    path = r.save("test-cassette", "/path/to/spec.yaml")
    assert path is not None

    loaded = load_cassette("test-cassette")
    assert loaded.name == "test-cassette"
    assert len(loaded.interactions) == 1
    assert loaded.interactions[0].request_method == "GET"
    assert loaded.interactions[0].response_body == '"ok"'


def test_load_nonexistent_cassette():
    """Test loading a nonexistent cassette raises."""
    with pytest.raises(FileNotFoundError):
        load_cassette("nonexistent-cassette-12345")


def test_cassette_interaction_dataclass():
    """Test CassetteInteraction data class."""
    ci = CassetteInteraction(
        request_method="POST",
        request_path="/items",
        request_headers={"Content-Type": "application/json"},
        request_body='{"name":"test"}',
        response_status=201,
        response_headers={"Location": "/items/1"},
        response_body='{"id":1}',
    )
    assert ci.request_method == "POST"
    assert ci.response_status == 201


def test_save_and_load_cassette_with_name():
    """Test saving and loading a named cassette via list_cassettes."""
    from apighost.vcr import Recorder, list_cassettes, load_cassette, save_cassette

    r = Recorder()
    r.record("GET", "/named", {}, None, 200, {}, '"named"')
    path = save_cassette("named-cassette", r.interactions, "/path/to/spec.yaml")
    assert path is not None

    cassettes = list_cassettes()
    names = [c["name"] for c in cassettes]
    assert "named-cassette" in names

    loaded = load_cassette("named-cassette")
    assert loaded.name == "named-cassette"


def test_list_cassettes_skips_corrupted_json():
    """list_cassettes skips files with invalid JSON (covers lines 34-35)."""
    from apighost.vcr import (
        CASSETTE_DIR,
        CassetteInteraction,
        list_cassettes,
        save_cassette,
    )

    # Save a valid cassette
    ci = CassetteInteraction("GET", "/valid", {}, None, 200, {}, '"ok"')
    save_cassette("valid-cassette", [ci], "")
    # Write corrupted JSON
    bad_file = CASSETTE_DIR / "corrupted.json"
    bad_file.write_text("this is not json {{{")
    cassettes = list_cassettes()
    names = [c["name"] for c in cassettes]
    assert "valid-cassette" in names
    assert "corrupted" not in names
    bad_file.unlink(missing_ok=True)
