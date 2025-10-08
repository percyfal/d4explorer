"""Module for handling JSONSchema metadata validation."""

from __future__ import annotations

import copy
import json
import os
import pprint
from typing import Any, Mapping

import jsonschema

from d4explorer.logging import app_logger as logger

D4ExplorerMetadataSchemaValidator = jsonschema.validators.extend(
    jsonschema.validators.Draft202012Validator
)


# Allow null schema; from tskit.metadata
def validate_bytes(data: bytes | None) -> None:
    """Validate that data is bytes."""
    if data is not None and not isinstance(data, bytes):
        raise TypeError(
            f"If no encoding is set metadata should be bytes, found {type(data)}"
        )


class Schema:
    """Class for storing configuration schema.

    NB: The parser cannot resolve references meaning only the
    properties sections will be populated.

    :param dict schema: A dict containing a JSONSchema object.

    """

    def __init__(self, schema: Mapping[str, Any] | None) -> None:
        self._schema = schema
        if schema is None:
            self._string = ""
            self._validate_row = validate_bytes
            self.empty_value = b""
        else:
            try:
                D4ExplorerMetadataSchemaValidator(schema)
            except jsonschema.exceptions.SchemaError as ve:
                logger.error(ve)
                raise
            self._string = json.dumps(schema, sort_keys=True, separators=(",", ":"))
            self._validate_row = D4ExplorerMetadataSchemaValidator(schema).validate
            if "type" in schema and "null" in schema["type"]:
                self.empty_value = None
            else:
                self.empty_value = {}

    def __repr__(self) -> str:
        return self._string

    def __str__(self) -> str:
        return pprint.pformat(self._schema)

    @property
    def schema(self):
        """Return a copy of the schema."""
        return copy.deepcopy(self._schema)

    def asdict(self) -> Mapping[str, Any] | None:
        """Return the schema as a dictionary."""
        return self.schema

    def validate(self, row: Any) -> dict:
        """Validate a configuration row (dict) against this schema."""
        try:
            self._validate_row(row)
        except jsonschema.exceptions.SchemaError as ve:
            logger.error(ve)
            raise
        return row


def get_data_schema():
    base = os.path.dirname(__file__)
    schema_file = os.path.join(base, "schema", "data.schema.json")
    with open(schema_file) as f:
        schema = json.load(f)
    return dict(schema)


def get_datacollection_schema():
    base = os.path.dirname(__file__)
    schema_file = os.path.join(base, "schema", "datacollection.schema.json")
    with open(schema_file) as f:
        schema = json.load(f)
    return dict(schema)
