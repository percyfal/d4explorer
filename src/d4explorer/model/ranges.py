import dataclasses
import os
from enum import Enum
from pathlib import Path
from tempfile import mkdtemp

import daiquiri
import numpy as np
import pandas as pd

from d4explorer.metadata import get_data_schema

from .metadata import MetadataBaseClass

logger = daiquiri.getLogger("d4explorer")


class BedType(Enum):
    BED3 = 3
    BED4 = 4
    BED5 = 5
    BED6 = 6


GFF3_COLUMNS = [
    "seqid",
    "source",
    "type",
    "start",
    "end",
    "score",
    "strand",
    "phase",
    "attributes",
]


def bed_columns(bt):
    columns = ["seqid", "start", "end", "name", "score", "strand"]
    return columns[: bt.value]


@dataclasses.dataclass(kw_only=True)
class Ranges(MetadataBaseClass):
    """Ranges object"""

    data: pd.DataFrame | Path | str
    name: str = None

    def __post_init__(self):
        if isinstance(self.data, Path) or isinstance(self.data, str):
            self.data = pd.read_csv(self.data, sep="\t", header=None)
        self.data.columns = ["seqid", "start", "end"]

    @property
    def temp_file(self):
        if not hasattr(self, "_temp_file"):
            temp_dir = mkdtemp()
            self._temp_file = Path(temp_dir) / f"{self.__class__.__name__}.bed"
        return self._temp_file

    @property
    def width(self):
        return np.sum(self.data["end"] - self.data["start"])

    @property
    def total(self):
        return self.width

    @property
    def shape(self):
        return self.data.shape

    def __len__(self):
        return self.width

    def write(self):
        logger.info("Writing regions to %s (%s)", self.temp_file, self.name)
        self.data.to_csv(self.temp_file, sep="\t", index=False)
        assert self.temp_file.exists(), f"Failed to write {self.temp_file}"


@dataclasses.dataclass(kw_only=True)
class Bed(Ranges):
    """Bed object"""

    data: pd.DataFrame | Path | str
    bedtype: BedType = None
    path: Path = None

    def __post_init__(self):
        self._columns = ["seqid", "start", "end", "name", "score", "strand"]
        self._types = ["str", "int64", "int64", "str", "int32", "str"]
        if isinstance(self.data, Path) or isinstance(self.data, str):
            self.path = Path(self.data)
            with open(self.path) as f:
                line = f.readline()
            self.bedtype = self.guess_bed_file_type(line.strip().split("\t"))
            self.data = pd.read_csv(self.path, sep="\t", header=None)
        elif isinstance(self.data, pd.DataFrame):
            self.bedtype = BedType(len(self.data.columns))
        else:
            raise ValueError("Unsupported data type")
        self.data.columns = self._columns[: self.bedtype.value]
        self.set_types()

    def set_types(self):
        self.data = self.data.astype(
            {k: v for k, v in zip(self._columns[: self.bedtype.value], self._types)}
        )

    @classmethod
    def guess_bed_file_type(cls, data):
        """Guess the bed file type based on the number of columns"""
        ncol = len(data)
        if ncol < 3:
            raise ValueError(f"Expected at least 3 columns in BED file, got {ncol}")
        if ncol > 6:
            raise ValueError(f"Expected at most 6 columns in BED file, got {ncol}")
        return BedType(ncol)

    def __setitem__(self, key, value):
        if key not in self.data.columns:
            assert key in self._columns, f"{key} not in allowed BED columns"
            self.data[key] = value
            self.bedtype = BedType(len(self.data.columns))
            self.set_types()
        else:
            self.data[key] = value

    def __getitem__(self, key):
        return self.data[key]


@dataclasses.dataclass(kw_only=True)
class GFF3(Ranges):
    """GFF3 dataclass."""

    data: pd.DataFrame | Path | str
    path: Path = None

    def __post_init__(self):
        if isinstance(self.data, Path) or isinstance(self.data, str):
            self.path = Path(self.data)
            self._read()
        assert self.data.shape[1] == 9, (
            "Data must have nine columns; saw shape %s" % str(self.data.shape)
        )
        self.data.columns = GFF3_COLUMNS
        self.metadata_schema = get_data_schema()

    def _read(self):
        self.data = pd.read_table(self.path, comment="#", header=None, sep="\t")

    def __getitem__(self, key):
        """Return annotation for specific feature type"""
        return GFF3(data=self.data[self.data["type"] == key], name=key)

    @property
    def feature_types(self):
        return self.data["type"].unique()

    @classmethod
    def generate_cache_key(cls, path: Path):
        if path is None:
            raise ValueError("Path is required to generate cache key")
        if isinstance(path, str):
            path = Path(path)
        size = path.stat().st_size
        absname = os.path.normpath(str(path.absolute()))
        return f"d4explorer:GFF3:{absname}:{size}"

    @property
    def cache_key(self):
        return self.generate_cache_key(self.path)

    @classmethod
    def load(cls, key: str, cache):
        cache_data = cache.get(key)
        if cache_data is None:
            logger.warning("GFF3: cache miss for %s", key)
            return None
        metadata, data = cache_data
        assert metadata["class"] == "GFF3", (
            f"incompatible class type {metadata['class']}"
        )
        return GFF3(data=data, metadata=metadata, path=metadata["path"])
