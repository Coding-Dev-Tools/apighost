"""Mock HTTP server generated from OpenAPI spec."""

from __future__ import annotations

import json
import logging
import random
import re
from typing import Any, Callable
from flask import Flask, Response, jsonify, request

from flask import Flask, Response, jsonify, request

from .faker_utils import generate_status_code, generate_value
from .parser import get_param_pattern
from .schema import ApiSpec, Endpoint, Scenario

logger = logging.getLogger(__name__)


def _extract_path_params(path_template: str, actual_path: str) -> dict[str, str]:
    """Extract path parameter values from an actual URL path.

    /users/{id} -> /users/42 -> {"id": "42"}
    """
    pattern = re.sub(r"\{(\w+)\}", r"(?P<\1>[^/]+)", path_template)
    match = re.match(f"^{pattern}/?$", actual_path)
    if match:
        return match.groupdict()
    return {}


def _make_response(status: int, body: Any, content_type: str = "application/json") -> Response:
    """Build a Flask Response."""
    if isinstance(body, str):
        return Response(body, status=status, content_type=content_type)
    response = jsonify(body)
    response.status_code = status
    return response


def _build_response_for_endpoint(endpoint: Endpoint,
                                 scenario: Scenario | None = None,
                                 params: dict[str, str] | None = None) -> tuple[Any, int]:
    """Build a realistic response for an endpoint, respecting scenario overrides."""
    key = f"{endpoint.method} {endpoint.path}"

    # Check scenario overrides
    if scenario and key in scenario.overrides:
        override = scenario.overrides[key]
        status = override.get("status", 200)
        body = override.get("body", {})
        return body, status

    # Generate realistic response
    status = generate_status_code(endpoint.responses)
    response_def = endpoint.responses.get(status) or endpoint.responses.get(200)

    if response_def and response_def.example:
        return response_def.example, status

    # Generate from schema
    if response_def and response_def.schema_ref:
        body = generate_value(response_def.schema_ref)
        return body, status

    # Fallback: make something up based on endpoint name
    return {"message": f"{endpoint.method} {endpoint.path} — mock response"}, status


def create_app(spec: ApiSpec, scenario: Scenario | None = None,
               recorder: Any = None, latency_range: tuple[float, float] = (0, 0)) -> Flask:
    """Create a Flask app from a parsed OpenAPI spec."""
    app = Flask(__name__)

    # Suppress Flask's default logging
    logging.getLogger("werkzeug").setLevel(logging.WARNING)

    # Track all registered routes for the home page
    routes: list[dict] = []

    @app.route("/")
    def _apighost_home():
        """Generated API home — list available routes."""
        return jsonify({
            "service": spec.title or "APIGhost Mock Server",
            "version": spec.version,
            "servers": spec.servers,
            "description": spec.description or "Mock API server generated from OpenAPI spec",
            "endpoints": routes,
            "scenario": scenario.name if scenario else "default",
        })

    @app.route("/_apighost/health")
    def _apighost_health():
        return jsonify({"status": "ok", "endpoints": len(spec.endpoints), "recording": recorder is not None})

    # Register each endpoint
    for ep in spec.endpoints:
        flask_route = get_param_pattern(ep.path)
        methods_list = [ep.method]
        route_info = {
            "path": ep.path,
            "method": ep.method,
            "operationId": ep.operation_id,
            "summary": ep.summary,
            "tags": ep.tags,
        }
        routes.append(route_info)

        def make_handler(endpoint: Endpoint, scenario: Scenario | None) -> Callable:
            def handler(**path_params):
                # Apply simulated latency if configured
                if latency_range[1] > 0:
                    delay = random.uniform(latency_range[0], latency_range[1])
                    time.sleep(delay)

                # Capture request info for recording
                req_method = request.method
                req_path = request.path
                req_headers = dict(request.headers)
                req_body = request.get_data(as_text=True)

                # Extract path params from actual URL
                params = _extract_path_params(endpoint.path, req_path)

                body, status = _build_response_for_endpoint(endpoint, scenario, params)

                resp_headers = {"Content-Type": "application/json"}

                # Record if recorder is active
                if recorder is not None:
                    resp_body = json.dumps(body) if not isinstance(body, str) else body
                    recorder.record(
                        request_method=req_method,
                        request_path=req_path,
                        request_headers=req_headers,
                        request_body=req_body,
                        response_status=status,
                        response_headers=resp_headers,
                        response_body=resp_body,
                    )

                return _make_response(status, body)
            return handler

        app.add_url_rule(
            flask_route,
            endpoint=f"{ep.method.lower()}_{ep.path}_{ep.operation_id or 'route'}",
            view_func=make_handler(ep, scenario),
            methods=methods_list,
        )

    return app
