"""Fake data generation from OpenAPI schemas using Faker."""

from __future__ import annotations

import random
from collections.abc import Callable
from faker import Faker
from typing import Any

from faker import Faker

_faker = Faker()

# Map OpenAPI format strings to Faker providers
FORMAT_TO_FAKER: dict[str, Callable[[], Any]] = {
    "email": lambda: _faker.email(),
    "uri": lambda: _faker.url(),
    "url": lambda: _faker.url(),
    "uuid": lambda: str(_faker.uuid4()),
    "date": lambda: _faker.date(),
    "date-time": lambda: _faker.iso8601(),
    "time": lambda: _faker.time(),
    "ipv4": lambda: _faker.ipv4(),
    "ipv6": lambda: _faker.ipv6(),
    "hostname": lambda: _faker.hostname(),
    "phone": lambda: _faker.phone_number(),
    "int64": lambda: _faker.random_int(min=0, max=10**12),
    "int32": lambda: _faker.random_int(min=0, max=2**31 - 1),
    "float": lambda: round(_faker.pyfloat(min_value=-10**6, max_value=10**6), 2),
    "double": lambda: _faker.pyfloat(min_value=-10**12, max_value=10**12),
    "binary": lambda: _faker.binary(16).hex(),
    "byte": lambda: _faker.binary(8).hex(),
    "password": lambda: _faker.password(),
}

# Property name -> realistic value generators
PROPERTY_HINTS: dict[str, Callable[[], Any]] = {
    "username": lambda: _faker.user_name(),
    "name": lambda: _faker.name(),
    "first_name": lambda: _faker.first_name(),
    "last_name": lambda: _faker.last_name(),
    "email": lambda: _faker.email(),
    "phone": lambda: _faker.phone_number(),
    "address": lambda: _faker.address().replace("\n", ", "),
    "city": lambda: _faker.city(),
    "state": lambda: _faker.state(),
    "country": lambda: _faker.country(),
    "zip": lambda: _faker.zipcode(),
    "postal": lambda: _faker.zipcode(),
    "title": lambda: _faker.catch_phrase(),
    "description": lambda: _faker.text(max_nb_chars=120),
    "summary": lambda: _faker.sentence(),
    "content": lambda: _faker.paragraph(nb_sentences=4),
    "body": lambda: _faker.paragraph(nb_sentences=4),
    "message": lambda: _faker.sentence(),
    "error": lambda: _faker.sentence(),
    "status": lambda: random.choice(["active", "inactive", "pending", "archived"]),
    "type": lambda: random.choice(["user", "admin", "moderator", "guest"]),
    "role": lambda: random.choice(["admin", "editor", "viewer", "contributor"]),
    "slug": lambda: _faker.slug(),
    "avatar": lambda: f"https://api.dicebear.com/7.x/avataaars/svg?seed={_faker.user_name()}",
    "image": lambda: f"https://picsum.photos/seed/{_faker.random_int()}/400/300",
    "url": lambda: _faker.url(),
    "website": lambda: _faker.url(),
    "company": lambda: _faker.company(),
    "department": lambda: _faker.bs(),
    "job": lambda: _faker.job(),
    "color": lambda: _faker.safe_color_name(),
    "language": lambda: _faker.language_name(),
    "tag": lambda: _faker.word(),
    "id": lambda: _faker.random_int(min=1, max=99999),
    "created_at": lambda: _faker.iso8601(),
    "updated_at": lambda: _faker.iso8601(),
    "timestamp": lambda: _faker.iso8601(),
}


def generate_value(schema: dict | None, property_name: str = "") -> Any:
    """Generate a realistic fake value from a JSON Schema."""
    if not schema:
        if property_name:
            hint = PROPERTY_HINTS.get(property_name.lower())
            if hint:
                return hint()
        return _faker.word()

    # Example takes priority
    if "example" in schema:
        return schema["example"]

    # Use format hint
    fmt = schema.get("format", "")
    if fmt and fmt in FORMAT_TO_FAKER:
        return FORMAT_TO_FAKER[fmt]()

    # Use property name hints
    if property_name:
        hint = PROPERTY_HINTS.get(property_name.lower())
        if hint:
            return hint()

    schema_type = schema.get("type", "string")
    enum = schema.get("enum")

    if enum:
        return random.choice(enum)

    if schema_type == "string":
        if "minLength" in schema and "maxLength" in schema:
            return _faker.pystr(min_chars=schema["minLength"], max_chars=schema["maxLength"])
        if schema.get("pattern"):
            return _faker.pystr(min_chars=8, max_chars=16)
        return _faker.word()

    if schema_type == "integer":
        minimum = schema.get("minimum", 0)
        maximum = schema.get("maximum", 99999)
        return _faker.random_int(min=minimum, max=maximum)

    if schema_type == "number":
        return round(_faker.pyfloat(min_value=-10**6, max_value=10**6), 2)

    if schema_type == "boolean":
        return _faker.boolean()

    if schema_type == "array":
        items = schema.get("items", {})
        count = max(1, min(schema.get("minItems", 1), schema.get("maxItems", 5) or 3))
        return [generate_value(items) for _ in range(count)]

    if schema_type == "object":
        result = {}
        required = set(schema.get("required", []))
        properties = schema.get("properties", {})
        for prop_name, prop_schema in properties.items():
            result[prop_name] = generate_value(prop_schema, prop_name)
        # Fill in any required props not in properties
        for req in required:
            if req not in result:
                result[req] = _faker.word()
        return result

    return _faker.word()


def generate_status_code(responses: dict[int, Any], scenario: str = "happy") -> int:
    """Pick a response status code based on scenario."""
    if not responses:
        return 200

    if scenario == "happy":
        for code in (200, 201, 204, 302):
            if code in responses:
                return code
        return next(iter(responses.keys())) if responses else 200

    if scenario in ("error", "error_400"):
        for code in (400, 422, 404, 403, 401):
            if code in responses:
                return code
        return 400

    if scenario == "server_error":
        for code in (500, 502, 503, 504):
            if code in responses:
                return code
        return 500

    # Default: pick the most common success code, or 200
    return 200
