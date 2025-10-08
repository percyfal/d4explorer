"""Data classes for storing coverage information for a feature."""

import dataclasses
import os
from pathlib import Path

import pandas as pd

from .feature import Feature


@dataclasses.dataclass
class D4FeatureCoverage:
    data: pd.DataFrame
    feature: Feature
    path: Path
    threshold: int

    @property
    def feature_type(self):
        return self.feature.feature_type

    @classmethod
    def generate_cache_key(cls, path: Path, region: Path, threshold: int) -> str:
        """Generate a cache key for a given d4 path, feature region,
        and threshold for presence / absence."""
        if isinstance(path, str):
            path = Path(path)
        size = path.stat().st_size
        absname = os.path.normpath(str(path.absolute()))
        return (
            f"d4explorer-summarize:D4FeatureCoverage:{absname}:"
            f"{size}:{threshold}:{region.name}"
        )

    @property
    def cache_key(self):
        return self.generate_cache_key(self.path, self.feature.path, self.threshold)


@dataclasses.dataclass
class D4FeatureCoverageList:
    keylist: list[str]
    region: Path
    threshold: int
    label: str = None

    def __len__(self):
        return len(self.keylist)

    def load(self, cache):
        data = []
        for k in self.keylist:
            data.append(cache.get(k))

    @classmethod
    def generate_cache_key(cls, region: Path, keylist: list, threshold: int):
        if isinstance(region, str):
            region = Path(region)
        size = region.stat().st_size
        absname = os.path.normpath(str(region.absolute()))
        return (
            f"d4explorer-summarize:D4FeatureCoverageList:{absname}:"
            f"{size}:{threshold}:{len(keylist)}"
        )

    @property
    def cache_key(self):
        return self.cache_key(
            region=Path(self.region),
            threshold=self.threshold,
            keylist=self.keylist,
        )

    # FIXME: add function to load keylist and convert to matrix


# FIXME: same as conifer.presabs.Coverage
@dataclasses.dataclass
class D4FeatureCoverageMatrix:
    data: pd.DataFrame
