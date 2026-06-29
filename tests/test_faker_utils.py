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
    val = generate_value(
        {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
            },
        }
    )
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
    val = generate_value(
        {
            "type": "object",
            "properties": {
                "user": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "contacts": {
                            "type": "array",
                            "items": {"type": "string", "format": "email"},
                        },
                    },
                }
            },
        }
    )
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


def test_generate_string_with_minmax_length():
    """Test string generation with minLength/maxLength constraints."""
    val = generate_value({"type": "string", "minLength": 8, "maxLength": 12})
    assert isinstance(val, str)
    assert 8 <= len(val) <= 12


def test_generate_string_with_pattern():
    """Test string generation with pattern constraint (falls back to pystr)."""
    val = generate_value({"type": "string", "pattern": "^[a-z]+$"})
    assert isinstance(val, str)
    assert len(val) > 0


def test_generate_number():
    """Test number type generation."""
    val = generate_value({"type": "number"})
    assert isinstance(val, float)


def test_generate_array_with_bounds():
    """Test array with minItems/maxItems constraints."""
    val = generate_value({"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 4})
    assert isinstance(val, list)
    assert 2 <= len(val) <= 4
    assert all(isinstance(v, str) for v in val)


def test_generate_object_required_not_in_properties():
    """Test object where required field is not listed in properties."""
    val = generate_value(
        {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
            },
            "required": ["name", "extra_field"],
        }
    )
    assert isinstance(val, dict)
    assert "name" in val
    assert "extra_field" in val


def test_generate_value_empty_schema():
    """Test generate_value with None schema."""
    val = generate_value(None)
    assert isinstance(val, str)
    assert len(val) > 0


def test_generate_value_empty_schema_with_property_hint():
    """Test generate_value with None schema but matching property hint."""
    val = generate_value(None, property_name="email")
    assert isinstance(val, str)
    assert "@" in val


def test_generate_value_none_schema_no_hint():
    """Test generate_value with None schema and unknown property name."""
    val = generate_value(None, property_name="nonexistent_prop_xyz")
    assert isinstance(val, str)
    assert len(val) > 0


def test_generate_with_null_type():
    """Test generation with unknown type falls back to faker word."""
    val = generate_value({"type": "null"})
    assert isinstance(val, str)


class TestGenerateStatusCode:
    """Extended coverage for generate_status_code."""

    def test_server_error_scenario(self):
        """Test server_error scenario selects 5xx codes."""
        responses = {200: None, 500: None, 502: None}
        code = generate_status_code(responses, "server_error")
        assert code in (500, 502)

    def test_server_error_scenario_fallback(self):
        """Test server_error scenario fallback when no 5xx present."""
        code = generate_status_code({200: None, 400: None}, "server_error")
        assert code == 500

    def test_error_scenario_fallback(self):
        """Test error scenario fallback when no 4xx present."""
        code = generate_status_code({200: None, 500: None}, "error")
        assert code == 400

    def test_happy_path_prefers_201(self):
        """Test happy path prefers 201 over 204."""
        responses = {201: None, 204: None, 302: None}
        code = generate_status_code(responses, "happy")
        assert code == 201

    def test_happy_path_no_2xx(self):
        """Test happy path falls back to first response key."""
        responses = {302: None, 404: None}
        code = generate_status_code(responses, "happy")
        assert code == 302


def test_generate_status_code_happy_with_non_standard_status():
    """Happy path with non-standard status codes returns first key (covers line 152)."""
    code = generate_status_code({301: None, 418: None}, "happy")
    assert code == 301


def test_generate_status_code_unknown_scenario():
    """Unknown scenario name with non-empty responses defaults to 200 (covers line 167)."""
    code = generate_status_code({200: None, 500: None}, "unknown_scenario_name")
    assert code == 200
