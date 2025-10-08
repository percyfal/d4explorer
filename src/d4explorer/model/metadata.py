"""Metadata base class and validation functions."""

import dataclasses

from d4explorer.metadata import Schema


def validate(schema, data):
    """Validate data"""
    if schema is None:
        return
    try:
        Schema(schema).validate(data)
    except Exception as e:
        raise ValueError(f"Error validating metadata: {e}")


# FIXME: setting items in metadata will not throw an error
@dataclasses.dataclass(kw_only=True)
class MetadataBaseClass:
    """Base class for class that has metadata"""

    metadata_schema: dict = dataclasses.field(default_factory=dict)
    metadata: dict = dataclasses.field(default_factory=dict)
    _metadata: dict = dataclasses.field(default_factory=dict, repr=False, init=False)

    def __post_init__(self):
        assert isinstance(self._metadata, dict)

    @property
    def metadata(self):  # noqa
        if self._metadata:
            self.validate(self._metadata)
        return self._metadata

    @metadata.setter
    def metadata(self, value):
        self._metadata = value

    def validate(self, value):
        """Validate metadata"""
        validate(self.metadata_schema, value)

    @classmethod
    def generate_cache_key(cls, *args, **kwargs):
        """Generate and return cache key"""
        raise NotImplementedError

    @property
    def cache_key(self):
        """Return cache key"""
        raise NotImplementedError
