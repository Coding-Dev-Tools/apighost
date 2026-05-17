"""Data models for parsed OpenAPI endpoints and scenarios."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Parameter:
    """An API parameter (path, query, header, cookie)."""
    name: str
    location: str  # path, query, header, cookie
    required: bool = False
    schema_ref: dict | None = None
    example: Any = None


@dataclass
class Response:
    """An API response definition."""
    status_code: int
    content_type: str = "application/json"
    schema_ref: dict | None = None
    example: Any = None
    description: str = ""


@dataclass
class Endpoint:
    """A single API endpoint parsed from an OpenAPI spec."""
    path: str
    method: str  # GET, POST, PUT, DELETE, PATCH
    operation_id: str = ""
    summary: str = ""
    description: str = ""
    parameters: list[Parameter] = field(default_factory=list)
    request_body_schema: dict | None = None
    responses: dict[int, Response] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    security: list[dict] | None = None
    deprecated: bool = False


@dataclass
class ApiSpec:
    """Top-level parsed OpenAPI specification."""
    title: str = ""
    version: str = ""
    description: str = ""
    endpoints: list[Endpoint] = field(default_factory=list)
    servers: list[str] = field(default_factory=list)
    components: dict = field(default_factory=dict)
    raw: dict = field(default_factory=dict)


@dataclass
class CassetteInteraction:
    """A single recorded HTTP interaction."""
    request_method: str
    request_path: str
    request_headers: dict
    request_body: str | None
    response_status: int
    response_headers: dict
    response_body: str


@dataclass
class Cassette:
    """VCR-style cassette of recorded interactions."""
    name: str
    interactions: list[CassetteInteraction] = field(default_factory=list)
    spec_path: str = ""


@dataclass
class Scenario:
    """A named scenario with preset responses."""
    name: str
    description: str = ""
    overrides: dict[str, dict] = field(default_factory=dict)
    # key: "GET /users/{id}" -> {"status": 404, "body": {"error": "not found"}}
