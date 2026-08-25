"""Tests for serve --watch spec hot-reload (SpecReloader)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from apighost.cli import SpecReloader, cli


def _write_spec(path: Path, title: str, n_paths: int = 1) -> None:
    paths = {f"/thing{i}": {"get": {"responses": {"200": {"description": "ok"}}}} for i in range(n_paths)}
    path.write_text(
        yaml.safe_dump(
            {
                "openapi": "3.0.0",
                "info": {"title": title, "version": "1.0.0"},
                "paths": paths,
            }
        ),
        encoding="utf-8",
    )


class _FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture()
def spec_file(tmp_path: Path) -> Path:
    p = tmp_path / "spec.yaml"
    _write_spec(p, "T")
    return p


def test_poll_rebuilds_on_mtime_change(spec_file: Path) -> None:
    builds = []

    def build():
        builds.append(1)
        return {"endpoints": len(builds)}

    clock = _FakeClock()
    r = SpecReloader(str(spec_file), build, interval=1.0, clock=clock)
    assert r.app == {"endpoints": 1}

    # within interval: no rebuild even though mtime changed
    _write_spec(spec_file, "T2", n_paths=2)
    clock.now += 0.5
    assert r.poll() is False

    # after interval: rebuild happens
    clock.now += 1.0
    assert r.poll() is True
    # app identity changed (rebuilt by create_app equivalent)
    assert r.app != {"endpoints": 1}


def test_poll_ignores_same_mtime(spec_file: Path) -> None:
    clock = _FakeClock()
    calls = []
    r = SpecReloader(str(spec_file), lambda: calls.append(1), interval=0.0, clock=clock)
    before = len(calls)
    clock.now += 10
    assert r.poll() is False  # unchanged mtime
    assert len(calls) == before


def test_poll_keeps_old_app_when_new_spec_is_broken(spec_file: Path) -> None:
    from apighost.parser import parse_spec

    good = object()

    def build():
        return good if parse_spec(str(spec_file)) else None

    clock = _FakeClock()
    r = SpecReloader(str(spec_file), build, interval=0.0, clock=clock)

    spec_file.write_text("{ this is not yaml: [", encoding="utf-8")
    clock.now += 10
    assert r.poll() is False
    assert r.app is good  # previous version keeps serving


def test_poll_survives_missing_spec_file(spec_file: Path, tmp_path: Path) -> None:
    gone = tmp_path / "deleted.yaml"
    clock = _FakeClock()
    r = SpecReloader(str(gone), lambda: object(), interval=0.0, clock=clock,
                     stat=lambda: (_ for _ in ()).throw(FileNotFoundError("gone")))
    clock.now += 10
    assert r.poll() is False


def test_serve_watch_wires_reloader(monkeypatch, tmp_path: Path) -> None:
    """serve --watch must engage SpecReloader instead of silently ignoring the flag."""
    spec = tmp_path / "s.yaml"
    _write_spec(spec, "Watched")

    created = {}
    real_cls = SpecReloader

    class Spy(real_cls):
        def __init__(self, *a, **k):
            created["init"] = True
            super().__init__(*a, **k)

    monkeypatch.setattr("apighost.cli.SpecReloader", Spy)

    import apighost.cli as c

    def fake_run_simple(host, port, app, **kw):  # never actually serve
        assert callable(app)
        fake_run_simple.called_with = (host, port)
        raise KeyboardInterrupt()

    monkeypatch.setattr(c, "run_simple", fake_run_simple, raising=False)
    # run_simple is imported inside serve(); patch werkzeug source too
    import werkzeug.serving as ws

    monkeypatch.setattr(ws, "run_simple", fake_run_simple)

    runner = CliRunner()
    runner.invoke(cli, ["serve", str(spec), "--watch", "--port", "5987"])
    assert created.get("init"), "SpecReloader was not constructed for --watch"
    assert getattr(fake_run_simple, "called_with", ("", 0))[1] == 5987
