"""Tests for OpenAPI spec parser."""

import json
import tempfile
from apighost.parser import _infer_type, get_param_pattern, parse_spec
from pathlib import Path

from . import PETSTORE_YAML


def test_load_yaml():
    """Test loading a YAML spec."""
    spec = parse_spec(PETSTORE_YAML)
    assert spec.title == "Petstore API"
    assert spec.version == "1.0.0"
    assert len(spec.servers) == 1
    assert spec.servers[0] == "https://api.petstore.com/v1"


def test_parse_endpoints():
    """Test endpoint parsing from petstore spec."""
    spec = parse_spec(PETSTORE_YAML)
    assert len(spec.endpoints) == 5

    methods = {(ep.method, ep.path) for ep in spec.endpoints}
    assert ("GET", "/pets") in methods
    assert ("POST", "/pets") in methods
    assert ("GET", "/pets/{petId}") in methods
    assert ("DELETE", "/pets/{petId}") in methods
    assert ("GET", "/pets/{petId}/photos") in methods


def test_parse_endpoint_details():
    """Test endpoint details."""
    spec = parse_spec(PETSTORE_YAML)
    list_pets = [ep for ep in spec.endpoints if ep.operation_id == "listPets"][0]
    assert list_pets.method == "GET"
    assert list_pets.path == "/pets"
    assert list_pets.summary == "List all pets"
    assert len(list_pets.parameters) == 1
    assert list_pets.parameters[0].name == "limit"
    assert list_pets.parameters[0].location == "query"
    assert list_pets.parameters[0].required is False


def test_parse_path_params():
    """Test path parameter resolution."""
    spec = parse_spec(PETSTORE_YAML)
    get_pet = [ep for ep in spec.endpoints if ep.operation_id == "getPetById"][0]
    assert len(get_pet.parameters) == 1
    assert get_pet.parameters[0].name == "petId"
    assert get_pet.parameters[0].required is True


def test_parse_responses():
    """Test response parsing."""
    spec = parse_spec(PETSTORE_YAML)
    get_pet = [ep for ep in spec.endpoints if ep.operation_id == "getPetById"][0]
    assert 200 in get_pet.responses
    assert 404 in get_pet.responses
    assert get_pet.responses[200].description == "A single pet"


def test_parse_post_request_body():
    """Test request body parsing."""
    spec = parse_spec(PETSTORE_YAML)
    create = [ep for ep in spec.endpoints if ep.operation_id == "createPet"][0]
    assert create.request_body_schema is not None
    assert "properties" in create.request_body_schema
    assert "name" in create.request_body_schema["properties"]


def test_parse_json_spec():
    """Test parsing a JSON-formatted OpenAPI spec."""
    spec_dict = {
        "openapi": "3.0.0",
        "info": {"title": "JSON Test API", "version": "1.0.0"},
        "paths": {"/items": {"get": {"operationId": "listItems", "responses": {"200": {"description": "OK"}}}}},
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(spec_dict, f)
        tmp_path = f.name

    try:
        spec = parse_spec(tmp_path)
        assert spec.title == "JSON Test API"
        assert len(spec.endpoints) == 1
        assert spec.endpoints[0].method == "GET"
    finally:
        Path(tmp_path).unlink()


def test_get_param_pattern():
    """Test path parameter conversion for Flask."""
    assert get_param_pattern("/users/{id}") == "/users/<id>"
    assert get_param_pattern("/users/{userId}/posts/{postId}") == "/users/<userId>/posts/<postId>"
    assert get_param_pattern("/items") == "/items"


def test_infer_type():
    """Test schema type inference."""
    assert _infer_type({"type": "string"}) == "string"
    assert _infer_type({"type": "integer"}) == "integer"
    assert _infer_type({"$ref": "#/components/schemas/Pet"}) == "object"
    assert _infer_type(None) == "string"
    assert _infer_type({}) == "string"
