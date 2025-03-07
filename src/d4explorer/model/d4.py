"""d4explorer data module."""

import dataclasses
import os
from enum import Enum
from pathlib import Path

import daiquiri
import numpy as np
import pandas as pd

from .feature import Feature, GFF3Annotation

logger = daiquiri.getLogger("d4explorer")


class DataTypes(Enum):
    """Enum for getter method data types."""

    LIST = "list"
    DATAFRAME = "df"
    BED = "bed"
    D4 = "d4"


@dataclasses.dataclass
class D4Hist:
    data: pd.DataFrame
    feature: Feature
    genome_size: int = None
    mask: pd.Series = None

    def __post_init__(self):
        assert self.data.shape[1] == 2, (
            "Data must have two columns; saw shape %s" % str(self.data.shape)
        )
        assert isinstance(self.feature, Feature), (
            "Feature must be of class Feature; saw %s" % type(self.feature)
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
        if self.mask is None:
            self.mask = pd.Series([True] * self.data.shape[0])

    def __getitem__(self, key):
        data = self.data[key]
        return D4Hist(data, feature=self.feature, genome_size=self.genome_size)

    @property
    def feature_type(self):
        return self.feature.name

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
        data = self.data["counts"] * self.data["x"]
        data.values[0] = self.data["counts"].values[0]
        return data

    @property
    def coverage(self):
        if self.genome_size is None:
            raise TypeError("Genome size must be set to compute coverage")
        return self.nbases / self.genome_size

    def sample(self, n, random_seed=None):
        if random_seed is not None:
            np.random.seed(random_seed)
        total_size = np.sum(self.data["counts"][self.mask.values])
        print(total_size)
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
                self.data["x"][self.mask.values],
                size=n,
                replace=True,
                p=self.data["counts"][self.mask.values] / total_size,
            )
        except ValueError:
            logger.warning("Resampling failed; returning zeros vector")
            y = np.zeros(n)
        return y


@dataclasses.dataclass
class D4AnnotatedHist:
    data: list[D4Hist] = dataclasses.field(default_factory=list)
    annotation: Path = None
    genome_size: int = None
    path: Path = None
    max_bins: int = 1_000

    def __post_init__(self):
        assert all(isinstance(x, D4Hist) for x in self.data)
        assert isinstance(self.genome_size, int)
        if self.annotation is not None:
            assert isinstance(self.annotation, Path)
            self._annotation_data = GFF3Annotation(self.annotation)

    @property
    def annotation_data(self):
        return self._annotation_data

    def between(self, pmin, pmax):
        return self.data[0].data["x"].between(pmin, pmax)

    def __getitem__(self, key):
        """Allow slicing with boolean Series or list of strings for features"""
        if isinstance(key, pd.Series):
            data = self.data
            for x in data:
                x.mask = key
        elif isinstance(key, list):
            data = [x for x in self.data if x.feature_type in key]
        return D4AnnotatedHist(
            data=data,
            annotation=self.annotation,
            genome_size=self.genome_size,
            path=self.path,
            max_bins=self.max_bins,
        )

    @classmethod
    def cache_key(cls, path: Path, max_bins: int, annotation: Path) -> str:
        """Generate a cache key for a given path, max_bins and annotation"""
        if isinstance(path, str):
            path = Path(path)
        size = path.stat().st_size
        absname = os.path.normpath(str(path.absolute()))
        return (
            f"d4explorer:D4AnnotatedHist:{absname}:{size}"
            f":{max_bins}:{annotation}"
        )

    @property
    def key(self):
        return self.cache_key(self.path, self.max_bins, self.annotation)

    def min(self):
        return self.data[0].data["x"].min()

    def max(self):
        return self.data[0].data["x"].max()

    @property
    def shape(self):
        return self.data[0].shape

    def df(self) -> pd.DataFrame:
        """Return dataframe representation"""
        if len(self.data) == 0:
            return pd.DataFrame()
        dflist = []
        for d4h in self.data:
            df = d4h.data.copy()
            df["feature"] = d4h.feature_type
            df["nbases"] = d4h.nbases
            df["coverage"] = d4h.coverage
            df["mask"] = d4h.mask
            dflist.append(df)
        return pd.concat(dflist)

    @property
    def features(self):
        return [x.feature_type for x in self.data]

    def __len__(self):
        return len(self.data)
