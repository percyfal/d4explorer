import dataclasses
from enum import Enum
from pathlib import Path
from tempfile import mkdtemp

import pandas as pd


class BedType(Enum):
    BED3 = 3
    BED4 = 4
    BED5 = 5
    BED6 = 6


def bed_columns(bt):
    columns = ["chrom", "start", "end", "name", "score", "strand"]
    return columns[: bt.value]


@dataclasses.dataclass
class Ranges:
    """Ranges object"""

    @property
    def temp_file(self):
        temp_dir = mkdtemp()
        return Path(temp_dir) / "ranges.bed"


@dataclasses.dataclass
class Bed:
    """Bed object"""

    data: pd.DataFrame | Path | str
    bedtype: BedType = None
    path: Path = None

    def __post_init__(self):
        self._columns = ["chrom", "start", "end", "name", "score", "strand"]
        self._types = ["str", "int64", "int64", "str", "int32", "str"]
        if isinstance(self.data, Path) or isinstance(self.data, str):
            self.path = Path(self.data)
            with open(self.path) as f:
                line = f.readline()
            self.bedtype = self.guess_bed_file_type(line.strip().split("\t"))
            self.data = pd.read_csv(self.path, sep="\t", header=None)
        else:
            self.bedtype = BedType(len(self.data.columns))
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
