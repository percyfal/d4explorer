import pytest

from d4explorer.metadata import (
    Schema,
    get_data_schema,
    get_datacollection_schema,
)
from d4explorer.model.metadata import MetadataBaseClass


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


@pytest.fixture
def datacollection():
    return {
        "id": "123",
        "name": "test",
        "version": "1.0",
        "parameters": "test",
        "software": "test",
        "class": "test",
        "members": ["123", "234", "345"],
    }


@pytest.fixture
def data_schema():
    return get_data_schema()


@pytest.fixture
def datacollection_schema():
    return get_datacollection_schema()


def test_null_schema():
    schema = Schema(None)
    assert schema.empty_value == b""


def test_empty_dict_schema():
    schema = Schema({"type": "object"})
    assert schema.empty_value == {}
    assert schema.validate({}) == {}


def test_data_schema(data, data_schema):
    schema = Schema(data_schema)
    schema.validate(data)
    data["id"] = 123
    with pytest.raises(Exception):
        schema.validate(data)


def test_datacollection_schema(datacollection, datacollection_schema):
    schema = Schema(datacollection_schema)
    schema.validate(datacollection)
    datacollection["members"] = [123, 234, "345"]
    with pytest.raises(Exception):
        schema.validate(datacollection)


def test_mbc():
    mbc = MetadataBaseClass()
    assert mbc.metadata == {}
    assert mbc.metadata_schema == {}
    mbc.metadata = {"id": "123"}
    assert mbc.metadata == {"id": "123"}
    mbc.metadata_schema = {"type": "object"}
    mbc.metadata = {"id": "12"}
    mbc.metadata_schema = {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
        },
    }
    mbc.metadata = {"id": "123"}
    with pytest.raises(Exception):
        mbc.metadata = {"id": 123}
