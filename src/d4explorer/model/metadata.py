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


@dataclasses.dataclass(kw_only=True)
class MetadataBaseClass:
    """Base class for class that has metadata"""

    metadata_schema: dict = dataclasses.field(default_factory=dict)
    metadata: dict = dataclasses.field(default_factory=dict)
    _metadata: dict = dataclasses.field(default_factory=dict, repr=False)

    @property
    def metadata(self):  # noqa
        return self._metadata

    @metadata.setter
    def metadata(self, value):
        self._metadata = value
        self.validate()

    def validate(self):
        """Validate metadata"""
        validate(self.metadata_schema, self.metadata)
