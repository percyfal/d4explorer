import pytest

from d4explorer.metadata import Schema


@pytest.fixture
def data():
    return {
        "id": "123",
        "name": "test",
        "path": "file:///tmp/test",
        "version": "1.0",
        "parameters": "test",
        "software": "test",
        "class": "test",
    }


def test_null_schema():
    schema = Schema(None)
    assert schema.empty_value == b""


def test_empty_dict_schema():
    schema = Schema({"type": "object"})
    assert schema.empty_value == {}
    assert schema.validate({}) == {}


def test_data_schema(data):
    schema = Schema(
        {
            "type": "object",
            "codec": "json",
            "properties": {
                "id": {"type": "string"},
                "name": {"type": "string"},
                "path": {"format": "uri-reference", "type": "string"},
                "version": {"type": "string"},
                "parameters": {"type": "string"},
                "software": {"type": "string"},
                "class": {"type": "string"},
            },
            "required:": [
                "id",
                "name",
                "path",
                "version",
                "parameters",
                "software",
                "class",
            ],
            "additionalProperties": True,
        }
    )
    schema.validate(data)
    data["id"] = 123
    with pytest.raises(Exception):
        schema.validate(data)
