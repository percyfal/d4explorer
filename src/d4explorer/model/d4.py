"""d4explorer data module."""

import dataclasses
import os
from enum import Enum
from pathlib import Path

import daiquiri
import numpy as np
import pandas as pd

from d4explorer.cache import D4ExplorerCache
from d4explorer.metadata import get_data_schema, get_datacollection_schema

from .feature import Feature
from .metadata import MetadataBaseClass
from .ranges import GFF3

logger = daiquiri.getLogger("d4explorer")


class DataTypes(Enum):
    """Enum for getter method data types."""

    LIST = "list"
    DATAFRAME = "df"
    BED = "bed"
    D4 = "d4"


@dataclasses.dataclass(kw_only=True)
class D4Hist(MetadataBaseClass):
    """Class that stores D4Hist data.

    This class is used to store data generated by d4tools stat.
    The optional feature parameter is used to store the feature that
    was used as input to d4tools stat.
    """

    data: pd.DataFrame
    feature: Feature = None
    path: Path = None
    mask: pd.Series = None
    genome_size: int = None

    def __post_init__(self):
        assert self.data.shape[1] == 2, (
            "Data must have two columns; saw shape %s" % str(self.data.shape)
        )
        if self.feature is not None:
            assert isinstance(self.feature, Feature), (
                "Feature must be of class Feature; saw %s" % type(self.feature)
            )
        self.data.columns = ["x", "counts"]
        self._original = self.data.copy()
        self.ltzero = pd.Series([False] * self.data.shape[0])
        self.gtzero = pd.Series([False] * self.data.shape[0])
        if self.data["x"].dtype == object:
            self.ltzero = self.data["x"].str.contains("<")
            self.gtzero = self.data["x"].str.contains(">")
        if self.ltzero.any():
            self.data.loc[self.ltzero, "x"] = -1
        if self.gtzero.any():
            self.data.loc[self.gtzero, "x"] = (
                self.data.loc[self.gtzero, "x"].str.replace(">", "").astype(int) + 1
            )
        self.data = self.data.astype(int)
        if self.mask is None:
            self.mask = pd.Series([True] * self.data.shape[0])
        self.metadata_schema = get_data_schema()

    def __getitem__(self, key):
        data = self.data[key]
        return D4Hist(data=data, mask=self.mask, genome_size=self.genome_size)

    @property
    def max_bin(self):
        return self.data["x"].values[-1] - 1

    @property
    def max_nonzero_x(self):
        j = max(np.nonzero(self.data["counts"])[0])
        return self.data["x"].iloc[j]

    @property
    def original(self):
        return self._original

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

        if n > total_size:
            if self.feature:
                logger.warning(
                    (
                        "Sample size (n=%i) is larger the data set (n=%i); "
                        "resampling values for feature %s"
                    ),
                    int(n),
                    int(total_size),
                    self.feature_type,
                )
            else:
                logger.warning(
                    (
                        "Sample size (n=%i) is larger the data set (n=%i); "
                        "resampling values"
                    ),
                    int(n),
                    int(total_size),
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

    @property
    def feature_type(self):
        if self.feature is not None:
            return self.feature.name
        return None

    @classmethod
    def generate_cache_key(cls, path: Path, max_bins: int, annotation: Path) -> str:
        """Generate a cache key for a given path, max_bins and annotation"""
        if isinstance(path, str):
            path = Path(path)
        if path is not None:
            size = path.stat().st_size
            absname = os.path.normpath(str(path.absolute()))
        else:
            size = "NA"
            absname = "None"
        return f"d4explorer:D4Hist:{absname}:{size}:{max_bins}:{annotation}"

    @property
    def cache_key(self):
        return self.generate_cache_key(self.path, self.max_bin, self.feature_type)

    def to_cache(self) -> tuple:
        """Convert to cacheable object.

        Returns: data, metadata tuple
        """
        if self.feature is not None:
            return (
                (self.data, self.metadata),
                (self.feature.data, self.feature.metadata),
            )
        return ((self.data, self.metadata),)

    @classmethod
    def load(cls, key: str, cache: D4ExplorerCache):
        """Load from cache"""
        cache_data = cache.get(key)
        if cache_data is None:
            logger.warning("D4Hist: cache miss for %s", key)
            return None
        metadata, data = cache_data
        print(metadata)
        assert metadata["class"] == "D4Hist", (
            "incompatible class type {metadata['class']}"
        )
        if "feature" in metadata["kwargs"]:
            feature = Feature.load(metadata["kwargs"]["feature"], cache)
        ret = D4Hist(
            data=data,
            feature=feature,
            genome_size=metadata["kwargs"]["genome_size"],
        )
        ret.metadata = metadata
        assert ret.genome_size is not None
        return ret


@dataclasses.dataclass(kw_only=True)
class D4AnnotatedHist(MetadataBaseClass):
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
            self._annotation_data = GFF3(data=self.annotation)
            self._annotation_data.metadata = {
                "id": self._annotation_data.cache_key,
                "version": "0.1",
                "parameters": "annotation",
                "software": "d4explorer",
                "class": "GFF3",
                "path": str(self.annotation),
            }
        self.metadata_schema = get_datacollection_schema()
        items = []
        try:
            items = [x.metadata["id"] for x in self.data]
            # Genome feature is always present
            items.extend([x.feature.metadata["id"] for x in self.data])
        except KeyError:
            logger.warning("Metadata not set on items")
        if self.annotation is not None:
            items.extend([self.annotation_data.metadata["id"]])

        self.metadata = {
            "id": self.cache_key(self.path, self.max_bins, self.annotation),
            "version": "0.1",
            "parameters": "preprocess",
            "software": "d4explorer",
            "class": "D4AnnotatedHist",
            "items": items,
            "kwargs": {
                "genome_size": self.genome_size,
                "max_bins": self.max_bins,
                "annotation": self.annotation,
            },
        }

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
        elif isinstance(key, int):
            data = self.data[key]
        else:
            raise TypeError("Invalid type for key")
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
        if path is not None:
            size = path.stat().st_size
            absname = os.path.normpath(str(path.absolute()))
        else:
            size = "NA"
            absname = "None"
        return f"d4explorer:D4AnnotatedHist:{absname}:{size}:{max_bins}:{annotation}"

    @classmethod
    def load(cls, key: str, cache: D4ExplorerCache):
        """Load from cache"""
        cache_data = cache.get(key)
        metadata, _ = cache_data
        assert metadata["class"] == "D4AnnotatedHist", (
            "incompatible class type {metadata['class']}"
        )

        items = []
        annotation_data = None
        for item in metadata["items"]:
            if item.startswith("d4explorer:D4Hist"):
                obj = D4Hist.load(item, cache)
                items.append(obj)
            elif item.startswith("d4explorer:GFF3"):
                annotation_data = GFF3.load(item, cache)
        d4h = D4AnnotatedHist(
            data=items,
            metadata=metadata,
            genome_size=metadata["kwargs"]["genome_size"],
            max_bins=metadata["kwargs"]["max_bins"],
            annotation=metadata["kwargs"]["annotation"],
        )
        d4h._annotation_data = annotation_data
        return d4h

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

    def to_cache(self) -> tuple:
        """Convert to cacheable object"""
        data = []
        for x in self.data:
            for y in x.to_cache():
                data.append(y)
        if self.annotation is not None:
            data.append((self.annotation_data.data, self.annotation_data.metadata))
        return data, self.metadata
