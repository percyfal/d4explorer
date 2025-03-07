import dataclasses
import os
from pathlib import Path
from tempfile import mkdtemp

import daiquiri
import numpy as np
import pandas as pd

logger = daiquiri.getLogger("d4explorer")


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


def convert_to_si_suffix(number):
    """Convert a number to a string with an SI suffix."""
    suffixes = [" ", "kbp", "Mbp", "Gbp", "Tbp"]
    power = len(str(int(number))) // 3
    return f"{number / 1000 ** power:.1f} {suffixes[power]}"


@dataclasses.dataclass
class GFF3Annotation:
    """GFF3 annotation dataclass."""

    data: pd.DataFrame | Path
    feature_type: str = "genome"

    def __post_init__(self):
        if isinstance(self.data, Path):
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
        return GFF3Annotation(
            self.data[self.data["type"] == key], feature_type=key
        )

    @property
    def shape(self):
        return self.data.shape

    @property
    def feature_types(self):
        return self.data["type"].unique()


@dataclasses.dataclass
class Feature:
    data: pd.DataFrame | GFF3Annotation | Path
    name: str = None
    path: str = None

    def __post_init__(self):
        if isinstance(self.data, Path):
            self.path = self.data
            self.data = pd.read_table(self.data, header=None, sep="\t")
            if self.data.shape[1] == 3:
                self.data.columns = ["seqid", "start", "end"]
            elif self.data.shape[1] == 4:
                self.data.columns = ["seqid", "start", "end", "name"]
            else:
                logger.error("Unsupported BED format")
                raise
        else:
            if isinstance(self.data, GFF3Annotation):
                if self.name is None:
                    self.name = self.data.feature_type
                self.data = self.data.data[["seqid", "start", "end", "type"]]
            else:
                if self.data.shape[1] == 3:
                    assert all(
                        self.data.columns.values == ["seqid", "start", "end"]
                    )
                elif self.data.shape[1] == 4:
                    assert all(
                        self.data.columns.values
                        == ["seqid", "start", "end", "name"]
                    )
        temp_dir = mkdtemp()
        self._temp_file = os.path.join(temp_dir, "regions.bed")

    @property
    def total(self):
        return np.sum(self.data["end"] - self.data["start"])

    @property
    def temp_file(self):
        return self._temp_file

    def write(self):
        logger.info("Writing regions to %s", self.temp_file)
        self.data.to_csv(self.temp_file, sep="\t", index=False)

    def format(self):
        return convert_to_si_suffix(self.total)

    @property
    def width(self):
        return self.data["end"] - self.data["start"]

    def __len__(self):
        return self.total

    def merge(self):
        if self.data.shape[0] == 0:
            return

        dflist = []
        for g, data in self.data.groupby("seqid"):
            data.sort_values(by=["start"], inplace=True)
            first = True
            for _, row in data.iterrows():
                if first:
                    merged_intervals = [row]
                    first = False
                    continue
                last_merged = merged_intervals[-1]
                if row.start <= last_merged.end:
                    last_merged.end = max(last_merged.end, row.end)
                else:
                    merged_intervals.append(row)
            df = pd.DataFrame(merged_intervals)
            df.sort_values(by=["start"], inplace=True)
            dflist.append(df)

        self.data = pd.concat(dflist)
