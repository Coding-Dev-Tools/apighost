"""Tests for fake data generation."""

from apighost.faker_utils import generate_status_code, generate_value


def test_generate_string():
    """Test generating a string value."""
    val = generate_value({"type": "string"})
    assert isinstance(val, str)
    assert len(val) > 0


def test_generate_integer():
    """Test generating an integer value."""
    val = generate_value({"type": "integer"})
    assert isinstance(val, int)


def test_generate_boolean():
    """Test generating a boolean value."""
    val = generate_value({"type": "boolean"})
    assert isinstance(val, bool)


def test_generate_array():
    """Test generating an array."""
    val = generate_value({"type": "array", "items": {"type": "string"}})
    assert isinstance(val, list)
    assert len(val) >= 1
    assert all(isinstance(v, str) for v in val)


def test_generate_object():
    """Test generating an object from properties."""
    val = generate_value({
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
        }
    })
    assert isinstance(val, dict)
    assert "name" in val
    assert "age" in val
    assert isinstance(val["name"], str)
    assert isinstance(val["age"], int)


def test_generate_enum():
    """Test generating from an enum."""
    val = generate_value({"type": "string", "enum": ["red", "green", "blue"]})
    assert val in ("red", "green", "blue")


def test_generate_with_example():
    """Test that example takes priority."""
    val = generate_value({"type": "string", "example": "hello-world"})
    assert val == "hello-world"


def test_generate_with_format():
    """Test format-based generation."""
    val = generate_value({"type": "string", "format": "email"})
    assert isinstance(val, str)
    assert "@" in val


def test_generate_by_property_name():
    """Test property name hints."""
    val = generate_value({"type": "string"}, property_name="email")
    assert "@" in val


def test_generate_nested():
    """Test nested object generation."""
    val = generate_value({
        "type": "object",
        "properties": {
            "user": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "contacts": {
                        "type": "array",
                        "items": {"type": "string", "format": "email"},
                    }
                }
            }
        }
    })
    assert isinstance(val["user"]["name"], str)
    assert isinstance(val["user"]["contacts"], list)
    assert "@" in val["user"]["contacts"][0]


def test_generate_status_code_happy():
    """Test happy path status code selection."""
    responses = {200: None, 201: None, 400: None, 500: None}
    code = generate_status_code(responses, "happy")
    assert code == 200


def test_generate_status_code_error():
    """Test error scenario status code selection."""
    responses = {200: None, 400: None, 404: None}
    code = generate_status_code(responses, "error_400")
    assert code in (400, 404)


def test_generate_status_code_empty():
    """Test fallback status code."""
    code = generate_status_code({}, "happy")
    assert code == 200


def test_generate_with_bounds():
    """Test integer with min/max."""
    val = generate_value({"type": "integer", "minimum": 10, "maximum": 20})
    assert 10 <= val <= 20
