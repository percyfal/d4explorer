import dataclasses
from enum import Enum
from pathlib import Path
from tempfile import mkdtemp

import daiquiri
import numpy as np
import pandas as pd

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


@dataclasses.dataclass
class Ranges:
    """Ranges object"""

    data: pd.DataFrame | Path | str
    name: str = None

    def __post_init__(self):
        if isinstance(self.data, Path) or isinstance(self.data, str):
            self.data = pd.read_csv(self.data, sep="\t", header=None)
        self.data.columns = ["seqid", "start", "end"]

    @property
    def temp_file(self):
        temp_dir = mkdtemp()
        return Path(temp_dir) / f"{self.__class__.__name__}.bed"

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


@dataclasses.dataclass
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
            {
                k: v
                for k, v in zip(
                    self._columns[: self.bedtype.value], self._types
                )
            }
        )

    @classmethod
    def guess_bed_file_type(cls, data):
        """Guess the bed file type based on the number of columns"""
        ncol = len(data)
        if ncol < 3:
            raise ValueError(
                f"Expected at least 3 columns in BED file, got {ncol}"
            )
        if ncol > 6:
            raise ValueError(
                f"Expected at most 6 columns in BED file, got {ncol}"
            )
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


@dataclasses.dataclass
class GFF3(Ranges):
    """GFF3 dataclass."""

    data: pd.DataFrame | Path | str
    label: str = None

    def __post_init__(self):
        if isinstance(self.data, Path) or isinstance(self.data, str):
            self._read()
        assert self.data.shape[1] == 9, (
            "Data must have nine columns; saw shape %s" % str(self.data.shape)
        )
        self.data.columns = GFF3_COLUMNS

    def _read(self):
        self.data = pd.read_table(
            self.data, comment="#", header=None, sep="\t"
        )

    def __getitem__(self, key):
        """Return annotation for specific feature type"""
        return GFF3(self.data[self.data["type"] == key], label=key)

    @property
    def feature_types(self):
        return self.data["type"].unique()
