"""Tests for cassette robustness: corrupt-cassette errors and shutdown-save wiring."""



from click.testing import CliRunner

from apighost.cli import cli


def _write_corrupt(tmp_path):
    p = tmp_path / "broken.json"
    p.write_text("{not valid json")
    return str(p)


def test_cassette_info_corrupt_json_friendly_error(tmp_path):
    result = CliRunner().invoke(cli, ["cassette", "info", _write_corrupt(tmp_path)])
    assert result.exit_code == 1
    assert "not a valid apighost cassette" in result.output


def test_replay_corrupt_json_friendly_error(tmp_path):
    result = CliRunner().invoke(cli, ["replay", _write_corrupt(tmp_path)])
    assert result.exit_code == 1
    assert "not a valid apighost cassette" in result.output


def test_replay_nonexistent_friendly_error():
    result = CliRunner().invoke(cli, ["replay", "/nonexistent/nope.json"])
    assert result.exit_code == 1
    assert "Error" in result.output
