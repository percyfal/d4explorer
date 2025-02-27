"""d4explorer data module."""

import dataclasses
from enum import Enum
from pathlib import Path

import daiquiri
import numpy as np
import pandas as pd

logger = daiquiri.getLogger("d4explorer")


class DataTypes(Enum):
    """Enum for getter method data types."""

    LIST = "list"
    DATAFRAME = "df"
    BED = "bed"
    D4 = "d4"


@dataclasses.dataclass
class GFF3Annotation:
    """GFF3 annotation dataclass."""

    data: pd.DataFrame

    def __post_init__(self):
        assert self.data.shape[1] == 9, (
            "Data must have nine columns; saw shape %s" % str(self.data.shape)
        )
        self.data.columns = [
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

    def __getitem__(self, key):
        """Return annotation for specific feature type"""
        return GFF3Annotation(self.data[self.data["type"] == key])

    @property
    def shape(self):
        return self.data.shape


@dataclasses.dataclass
class D4Hist:
    data: pd.DataFrame
    genome_size: int = None
    feature_type: str = "genome"
    annotation: GFF3Annotation = None

    def __post_init__(self):
        assert self.data.shape[1] == 2, (
            "Data must have two columns; saw shape %s" % str(self.data.shape)
        )
        self.data.columns = ["x", "counts"]
        self.ltzero = pd.Series([False] * self.data.shape[0])
        self.gtzero = pd.Series([False] * self.data.shape[0])
        if self.data["x"].dtype == object:
            self.ltzero = self.data["x"].str.contains("<")
            self.gtzero = self.data["x"].str.contains(">")
        if self.ltzero.any():
            self.data.loc[self.ltzero, "x"] = -1
        if self.gtzero.any():
            self.data.loc[self.gtzero, "x"] = (
                self.data.loc[self.gtzero, "x"]
                .str.replace(">", "")
                .astype(int)
                + 1
            )
        self.data = self.data.astype(int)

    def __getitem__(self, key):
        print("Calling getitem with ", key)
        data = self.data[key]
        return D4Hist(data)

    @property
    def shape(self):
        return self.data.shape

    @property
    def max_bin(self):
        return self.data["x"].values[-1] - 1

    @property
    def max_nonzero_x(self):
        j = max(np.nonzero(self.data["counts"])[0])
        return self.data["x"].iloc[j]

    @property
    def original(self):
        data = self.data.copy()
        if self.ltzero.any():
            data.loc[0, "x"] = "<0"
        if self.gtzero.any():
            data.loc[data.shape[0] - 1, "x"] = f">{self.max_bin}"
        data.astype({"x": int})
        return data

    @property
    def nbases(self):
        return self.data["counts"] * self.data["x"]

    @property
    def coverage(self):
        if self.genome_size is None:
            raise TypeError("Genome size must be set to compute coverage")
        return self.nbases / self.genome_size

    def sample(self, n, random_seed=None):
        if random_seed is not None:
            np.random.seed(random_seed)
        total_size = np.sum(self.data["counts"])
        if n > total_size:
            logger.warning(
                (
                    "Sample size (n=%i) is larger the data set (n=%i); "
                    "resampling values for feature %s"
                ),
                int(n),
                int(total_size),
                self.feature_type,
            )
        try:
            y = np.random.choice(
                self.data["x"],
                size=n,
                replace=True,
                p=self.data["counts"] / total_size,
            )
        except ValueError:
            logger.warning("Resampling failed; returning zeros vector")
            y = np.zeros(n)
        return y


@dataclasses.dataclass
class D4Data:
    name: Path


@dataclasses.dataclass
class D4HistOld:
    data: pd.DataFrame

    _columns = ["x", "counts", "nbases", "coverage"]

    def __post_init__(self):
        assert self.data.shape[1] == 4, (
            "Data must have four columns; saw shape %s" % str(self.data.shape)
        )
        if not all([x == y for x, y in zip(self.data.columns, self._columns)]):
            self.data.columns = self._columns

    # def __getitem__(self, key):
    #     print("CAlling getitem with ", key)
    #     return self.data[key]

    def between(self, minval, maxval):
        condition = self.data["x"].between(minval, maxval)
        return D4Hist(self.data[condition])
