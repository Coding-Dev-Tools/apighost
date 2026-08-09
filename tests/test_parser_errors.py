"""Tests for parser error handling with actionable messages."""

from __future__ import annotations

import re

import pytest

from apighost.parser import load_spec, parse_spec


def test_load_spec_missing_file_raises_file_not_found(tmp_path):
    """Missing spec file raises FileNotFoundError with path in message."""
    missing = tmp_path / "nonexistent.yaml"
    with pytest.raises(FileNotFoundError, match=re.escape(missing.name)):
        load_spec(missing)


def test_load_spec_invalid_yaml_raises_value_error(tmp_path):
    """Malformed YAML raises ValueError with filename context."""
    bad = tmp_path / "bad.yaml"
    bad.write_text("key: [unclosed\n", encoding="utf-8")
    with pytest.raises(ValueError, match=re.escape(bad.name)):
        load_spec(bad)


def test_load_spec_invalid_json_raises_value_error(tmp_path):
    """Malformed JSON raises ValueError with filename context."""
    bad = tmp_path / "bad.json"
    bad.write_text('{"key": invalid}', encoding="utf-8")
    with pytest.raises(ValueError, match=re.escape(bad.name)):
        load_spec(bad)


def test_parse_spec_missing_info_defaults(tmp_path):
    """Spec without info block uses safe defaults instead of crashing."""
    minimal = tmp_path / "minimal.yaml"
    minimal.write_text("paths: {}\n", encoding="utf-8")
    spec = parse_spec(minimal)
    assert spec.title == "Untitled API"
    assert spec.version == "0.0.0"
