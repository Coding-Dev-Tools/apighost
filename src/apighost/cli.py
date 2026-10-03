"""APIGhost CLI entry point - OpenAPI spec to mock server."""

from __future__ import annotations

import atexit
import contextlib
import json
import re
import signal
import sys
import threading
import time
from pathlib import Path
from typing import Any

import click
import requests as http_requests

from . import __version__
from .faker_utils import generate_value
from .parser import parse_spec
from .scenario import delete_scenario, list_scenarios, load_scenario, save_scenario
from .server import create_app
from .vcr import Recorder, list_cassettes, load_cassette

try:
    from revenueholdings_license import require_license
except ImportError:

    def require_license(tool) -> Any:
        def decorator(func) -> Any:
            return func

        return decorator


# Global recorder reference for signal handler
_current_recorder: Recorder | None = None
_current_server_thread = None


class SpecReloader:
    """Watches an OpenAPI spec file and rebuilds the mock app on change.

    Used by ``serve --watch`` so editing the spec takes effect without
    restarting the server. If a modified spec fails to parse, the previously
    loaded app keeps serving and the error is reported instead of crashing.
    """

    def __init__(
        self,
        spec_path: str,
        build_app: Any,
        interval: float = 1.0,
        clock: Any = time.monotonic,
        stat: Any = None,
    ) -> None:
        self.spec_path = str(spec_path)
        self._build_app = build_app
        self.interval = interval
        self._clock = clock
        self._stat = stat or Path(self.spec_path).stat
        self.app = build_app()
        self.last_poll = self._clock()
        try:
            self._mtime: float | None = self._stat().st_mtime
        except OSError:
            self._mtime = None

    def poll(self) -> bool:
        """Check the spec once; rebuild the app if its mtime changed.

        Returns True when the app was rebuilt, False otherwise.
        """
        now = self._clock()
        if now - self.last_poll < self.interval:
            return False
        self.last_poll = now
        try:
            mtime = self._stat().st_mtime
        except OSError as e:
            click.echo(f" Watch: cannot stat spec ({e}) - keeping current app", err=True)
            return False
        if mtime == self._mtime:
            return False
        self._mtime = mtime
        try:
            self.app = self._build_app()
        except Exception as e:
            click.echo(
                f" Watch: spec changed but failed to load ({e}) - keeping previous version",
                err=True,
            )
            return False
        click.echo(" Watch: spec changed - app reloaded", err=True)
        return True

    def loop_forever(self) -> None:
        while True:
            self.poll()
            time.sleep(min(self.interval, 0.5))





@click.group()
@click.version_option(__version__, prog_name="apighost")
def cli() -> None:
    """APIGhost - OpenAPI spec to mock server with VCR recording.

    Turn any OpenAPI 3.0/3.1 spec into a running mock server
    with realistic fake data and VCR-style recording/replay.
    """


@cli.command()
@click.argument("spec", type=click.Path(exists=True))
@click.option("--port", "-p", default=8080, help="Port to run the server on")
@click.option("--host", default="127.0.0.1", help="Host to bind to")
@click.option("--scenario", "-s", default=None, help="Scenario to use for responses")
@click.option("--record", "-r", is_flag=True, help="Record interactions to a cassette")
@click.option("--cassette-name", default=None, help="Name for the recorded cassette")
@click.option("--latency", type=float, default=0.0, help="Simulated latency in seconds")
@click.option("--watch", is_flag=True, help="Watch spec file for changes (auto-reload)")
def serve(spec, port, host, scenario, record, cassette_name, latency, watch) -> None:
    """Start a mock server from an OpenAPI spec file.

    \b
    Examples:
        apighost serve petstore.yaml
        apighost serve api.json -p 3000
        apighost serve spec.yaml --scenario error_400
        apighost serve spec.yaml --record --cassette-name my-test
    """
    click.echo(f" APIGhost v{__version__} - loading spec...")
    click.echo(f"   Spec: {spec}")

    try:
        api_spec = parse_spec(spec)
    except Exception as e:
        click.echo(f" Error parsing spec: {e}", err=True)
        sys.exit(1)

    click.echo(f"   API: {api_spec.title} v{api_spec.version}")
    click.echo(f"   Endpoints: {len(api_spec.endpoints)}")

    # Load scenario if specified
    scenario_obj = None
    if scenario:
        try:
            scenario_obj = load_scenario(scenario)
            click.echo(
                f"   Scenario: {scenario_obj.name} ({len(scenario_obj.overrides)} overrides)"
            )
        except FileNotFoundError:
            click.echo(f" Scenario '{scenario}' not found. Using default.", err=True)

    # Setup recorder
    recorder = Recorder() if record else None
    global _current_recorder
    _current_recorder = recorder

    if record:
        name = cassette_name or f"recording-{int(time.time())}"
        click.echo(f"   Recording to cassette: {name}")
    else:
        name = None

    # Latency
    latency_range = (latency, latency) if latency > 0 else (0, 0)

    # Create the Flask app (--watch swaps in a rebuilt app on spec changes)
    def _build_app() -> Any:
        # Re-parse from disk every time: --watch exists so edits to the spec
        # file are picked up, so a cached parse would make watch useless.
        fresh_spec = parse_spec(spec)
        current_scenario = None
        if scenario:
            try:
                current_scenario = load_scenario(scenario)
            except FileNotFoundError:
                current_scenario = None
        return create_app(fresh_spec, current_scenario, recorder, latency_range)

    watcher: SpecReloader | None = None
    if watch:
        watcher = SpecReloader(spec, _build_app)

        def _dispatch(environ, start_response):  # type: ignore[no-untyped-def]
            # Read through the reloader each request so a rebuilt app is
            # actually served, not the snapshot from startup.
            return watcher.app(environ, start_response)

        app: Any = _dispatch
        threading.Thread(target=watcher.loop_forever, daemon=True).start()
        click.echo("   Watch enabled: spec changes are picked up automatically")
    else:
        app = create_app(api_spec, scenario_obj, recorder, latency_range)


    click.echo(f"\n Mock server running at http://{host}:{port}")
    click.echo(f"   Health: http://{host}:{port}/_apighost/health")
    click.echo("   Press Ctrl+C to stop\n")

    # Save the cassette on ANY shutdown path. Previously only a clean
    # KeyboardInterrupt triggered a save: SIGTERM (docker stop, kill, CI
    # timeouts) killed the process and silently discarded the whole recording.
    saved = {"done": False}

    def _save_once() -> None:
        if saved["done"]:
            return
        saved["done"] = True
        _on_shutdown(recorder, name, spec)

    # atexit fires on sys.exit (including from signal handlers) and on normal
    # interpreter shutdown, so SIGTERM no longer discards the recording.
    atexit.register(_save_once)

    def _handle_signal(signum, frame) -> None:
        sys.exit(0)

    for sig_name in ("SIGTERM", "SIGINT", "SIGHUP"):
        sig = getattr(signal, sig_name, None)
        if sig is not None:
            with contextlib.suppress(ValueError, OSError):
                # signal() only works in the main thread
                signal.signal(sig, _handle_signal)

    # Run with WSGI
    try:
        from werkzeug.serving import run_simple

        run_simple(host, port, app, use_reloader=False, threaded=True)
    except KeyboardInterrupt:
        _save_once()
    except SystemExit:
        raise
    except Exception as e:
        click.echo(f" Server error: {e}", err=True)
        _save_once()


def _on_shutdown(recorder, cassette_name, spec_path) -> None:
    """Handle server shutdown - save cassette if recording."""
    if recorder and recorder.count > 0:
        path = recorder.save(
            cassette_name or f"recording-{int(time.time())}", spec_path
        )
        click.echo(f"\n Recorded {recorder.count} interactions → {path}")
    click.echo("\n Server stopped.")


@cli.command()
@click.argument("spec", type=click.Path(exists=True))
@click.option(
    "--output", "-o", default=None, help="Output file for cassette (default: auto)"
)
@click.option("--port", "-p", default=8081, help="Port for the recording server")
@click.option("--requests", "-n", default=5, help="Number of sample requests to make")
def record(spec, output, port, requests) -> Any:
    """Start server, make sample requests, and record them to a cassette.

    This fires sample requests against the mock server to capture
    realistic interactions for later replay.
    """
    api_spec = parse_spec(spec)
    recorder = Recorder()
    app = create_app(api_spec, recorder=recorder)

    # Start server in background
    from werkzeug.serving import run_simple

    thread = threading.Thread(
        target=lambda: run_simple("127.0.0.1", port, app, use_reloader=False),
        daemon=True,
    )
    thread.start()
    time.sleep(0.5)

    click.echo(f" Recording server at http://127.0.0.1:{port}")
    click.echo(f" Making up to {requests} sample requests...\n")

    # Make requests to each endpoint
    count = 0
    for ep in api_spec.endpoints:
        if count >= requests:
            break
        # Fill path params with fake values
        filled_path = ep.path
        for match in re.finditer(r"\{(\w+)\}", ep.path):
            param_name = match.group(1)
            filled_path = filled_path.replace(f"{{{param_name}}}", str(42))
        url = f"http://127.0.0.1:{port}{filled_path}"

        try:
            resp = http_requests.request(ep.method, url, timeout=3)
            click.echo(f"   {ep.method:>6} {resp.status_code} {filled_path}")
            count += 1
        except Exception as e:
            click.echo(f"   {ep.method:>6} ERROR {filled_path} - {e}")

    # Determine output
    if not output:
        output = (
            f"cassette-{api_spec.title.replace(' ', '-').lower()}-{int(time.time())}"
        )

    path = recorder.save(output, spec)
    click.echo(f"\n Recorded {recorder.count} interactions → {path}")
    return path


@cli.command()
@click.argument("cassette", type=click.Path())
@click.option("--port", "-p", default=8082, help="Port for the replay server")
@click.option("--host", default="127.0.0.1", help="Host to bind to")
def replay(cassette, port, host) -> Any:
    """Replay a recorded cassette as a mock server.

    Exact recorded responses will be served matching request paths.
    Useful for deterministic testing without live dependencies.
    """
    try:
        cassette_data = load_cassette(cassette)
    except FileNotFoundError as e:
        click.echo(f" Error: {e}", err=True)
        sys.exit(1)
    except (ValueError, KeyError, TypeError) as e:
        click.echo(
            f" Error: cassette '{cassette}' is not a valid apighost cassette ({e}).",
            err=True,
        )
        sys.exit(1)

    click.echo(f" APIGhost - replaying cassette: {cassette_data.name}")
    click.echo(f"   Interactions: {len(cassette_data.interactions)}")
    if cassette_data.spec_path:
        click.echo(f"   Original spec: {cassette_data.spec_path}")

    from flask import Flask, jsonify
    from flask import request as flask_request

    app = Flask(__name__)

    @app.route("/<path:path>", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
    def _replay_handler(path) -> Any:
        full_path = "/" + path
        for interaction in cassette_data.interactions:
            req_path = interaction.request_path.rstrip("/")
            if (
                interaction.request_method == flask_request.method
                and req_path == full_path.rstrip("/")
            ):
                return (
                    interaction.response_body,
                    interaction.response_status,
                    interaction.response_headers
                    or {"Content-Type": "application/json"},
                )

        return jsonify(
            {"error": "No matching recorded interaction", "path": full_path}
        ), 404

    @app.route("/")
    def _replay_home() -> Any:
        return jsonify(
            {
                "service": f"APIGhost Replay - {cassette_data.name}",
                "interactions": len(cassette_data.interactions),
                "endpoints": list(
                    set(
                        f"{i.request_method} {i.request_path}"
                        for i in cassette_data.interactions
                    )
                ),
            }
        )

    click.echo(f"\n Replay server at http://{host}:{port}")
    click.echo("   Press Ctrl+C to stop\n")

    from werkzeug.serving import run_simple

    try:
        run_simple(host, port, app, use_reloader=False, threaded=True)
    except KeyboardInterrupt:
        click.echo("\n Replay server stopped.")


@cli.group()
def cassette() -> None:
    """Manage recorded cassettes."""


@cassette.command("list")
def cassette_list() -> None:
    """List all recorded cassettes."""
    cassettes = list_cassettes()
    if not cassettes:
        click.echo("No cassettes found.")
        return

    click.echo(f"{'Name':<30} {'Interactions':<14} {'Size':<10}")
    click.echo("-" * 60)
    for c in cassettes:
        click.echo(f"{c['name']:<30} {c['interactions']:<14} {c['size']:<10}")


@cassette.command("info")
@click.argument("name")
def cassette_info(name) -> None:
    """Show details of a recorded cassette."""
    try:
        data = load_cassette(name)
    except FileNotFoundError as e:
        click.echo(f" Error: {e}", err=True)
        sys.exit(1)
    except (ValueError, KeyError, TypeError) as e:
        click.echo(
            f" Error: cassette '{name}' is not a valid apighost cassette ({e}).",
            err=True,
        )
        sys.exit(1)

    click.echo(f"Name: {data.name}")
    click.echo(f"Spec: {data.spec_path or 'N/A'}")
    click.echo(f"Interactions: {len(data.interactions)}")
    click.echo()
    for i, interaction in enumerate(data.interactions, 1):
        click.echo(f"  {i}. {interaction.request_method} {interaction.request_path}")
        click.echo(f"     → {interaction.response_status}")


@cli.group()
def scenario() -> None:
    """Manage response scenarios."""


@scenario.command("list")
def scenario_list() -> None:
    """List all saved scenarios."""
    scenarios = list_scenarios()
    if not scenarios:
        click.echo("No scenarios found. Create one with 'apighost scenario create'")
        return

    click.echo(f"{'Name':<25} {'Overrides':<12} {'Description'}")
    click.echo("-" * 60)
    for s in scenarios:
        click.echo(f"{s['name']:<25} {s['overrides']:<12} {s['description']}")


@scenario.command("create")
@click.argument("name")
@click.option("--description", "-d", default="", help="Scenario description")
def scenario_create(name, description) -> None:
    """Create a new empty scenario."""
    path = save_scenario(name, description)
    click.echo(f" Created scenario '{name}' → {path}")


@scenario.command("edit")
@click.argument("name")
@click.argument("route")  # e.g. "GET /users/{id}"
@click.option("--status", type=int, default=200, help="Response status code")
@click.option("--body", default=None, help="Response body JSON")
def scenario_edit(name, route, status, body) -> None:
    """Add/edit a route override in a scenario.

    ROUTE format: "GET /users/{id}" or "POST /items"
    """
    try:
        sc = load_scenario(name)
    except FileNotFoundError:
        click.echo(f" Scenario '{name}' not found. Create it first.", err=True)
        sys.exit(1)

    parsed_body = None
    if body:
        try:
            parsed_body = json.loads(body)
        except json.JSONDecodeError:
            parsed_body = body

    sc.overrides[route] = {"status": status, "body": parsed_body}
    save_scenario(sc.name, sc.description, sc.overrides)
    click.echo(f" Updated scenario '{name}' - overrides: {len(sc.overrides)}")


@scenario.command("delete")
@click.argument("name")
def scenario_delete(name) -> None:
    """Delete a scenario."""
    if delete_scenario(name):
        click.echo(f" Deleted scenario '{name}'")
    else:
        click.echo(f" Scenario '{name}' not found.", err=True)


@cli.command()
@click.argument("spec", type=click.Path(exists=True))
@click.option(
    "--output", "-o", default=None, help="Output path for the generated scenario"
)
@click.option("--name", "-n", default=None, help="Scenario name")
@click.option("--max-endpoints", "-m", type=int, default=0, help="Maximum number of endpoints to process (0 = all)")
def generate(spec, output, name, max_endpoints) -> None:
    """Generate sample data and create a scenario from an OpenAPI spec."""
    api_spec = parse_spec(spec)
    scenario_name = name or f"generated-{api_spec.title.replace(' ', '-').lower()}"

    endpoints = api_spec.endpoints
    total = len(endpoints)
    if max_endpoints and max_endpoints > 0:
        endpoints = endpoints[:max_endpoints]
        if max_endpoints < total:
            click.echo(f" (limiting to {max_endpoints}/{total} endpoints)")

    overrides = {}
    click.echo(f" Generating scenarios from {api_spec.title} v{api_spec.version}")
    click.echo()

    for ep in endpoints:
        key = f"{ep.method} {ep.path}"
        body = generate_value(
            next(iter(ep.responses.values())).schema_ref if ep.responses else None
        ) or {"message": f"Auto-generated response for {key}"}
        overrides[key] = {"status": 200, "body": body}
        click.echo(f"   {ep.method:<6} {ep.path}")

    path = save_scenario(
        scenario_name, f"Auto-generated from {spec}", overrides, output_path=output
    )
    click.echo(f"\n Generated {len(overrides)} endpoint responses → {path}")


@cli.command()
def info() -> None:
    """Show APIGhost configuration and storage info."""
    click.echo(f"APIGhost v{__version__}")
    click.echo(f"Cassettes: {Path.home() / '.apighost' / 'cassettes'}")
    click.echo(f"Scenarios: {Path.home() / '.apighost' / 'scenarios'}")
    click.echo()

    cassettes = list_cassettes()
    scenarios = list_scenarios()
    click.echo(f"Cassettes: {len(cassettes)}")
    click.echo(f"Scenarios: {len(scenarios)}")


if __name__ == "__main__":
    cli()
