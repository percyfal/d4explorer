import dataclasses
import os
from pathlib import Path

import daiquiri
import pandas as pd

from d4explorer.cache import D4ExplorerCache
from d4explorer.metadata import get_data_schema

from .ranges import GFF3, Bed

logger = daiquiri.getLogger("d4explorer")


def convert_to_si_suffix(number):
    """Convert a number to a string with an SI suffix."""
    suffixes = [" ", "kbp", "Mbp", "Gbp", "Tbp"]
    power = len(str(int(number))) // 3
    return f"{number / 1000**power:.1f} {suffixes[power]}"


@dataclasses.dataclass
class Feature(Bed):
    """BED4 representation of a feature"""

    data: pd.DataFrame | Bed | GFF3 | Path | str
    path: str = None

    def __post_init__(self, *args, **kwargs):
        if isinstance(self.data, Path) or isinstance(self.data, str):
            self.path = self.data
            try:
                self.data = Bed(data=self.data).data
            except ValueError:
                self.data = GFF3(data=self.data)
                self.data = self.data.data[["seqid", "start", "end", "type"]]
        else:
            if isinstance(self.data, GFF3):
                if self.name is None:
                    self.name = self.data.name
                self.data = self.data.data[["seqid", "start", "end", "type"]]

            elif isinstance(self.data, Bed):
                self.data = self.data.data
            elif isinstance(self.data, pd.DataFrame):
                pass
            else:
                raise ValueError("Unsupported data type")
        self.metadata_schema = get_data_schema()
        super().__post_init__(*args, **kwargs)

    def format(self):
        return convert_to_si_suffix(self.total)

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

    @classmethod
    def generate_cache_key(cls, path: Path, name: str):
        if isinstance(path, str):
            path = Path(path)
        if path is not None:
            size = path.stat().st_size
            absname = os.path.normpath(str(path.absolute()))
        else:
            size = "NA"
            absname = "None"
        return f"d4explorer:Feature:{absname}:{size}:{name}"

    @property
    def cache_key(self):
        return self.generate_cache_key(self.path, self.name)

    @classmethod
    def load(cls, key: str, cache: D4ExplorerCache):
        cache_data = cache.get(key)
        if cache_data is None:
            logger.warning("Feature: cache miss for %s", key)
            return None
        data, metadata = cache_data
        assert metadata["class"] == "Feature", (
            f"incompatible class type {metadata['class']}"
        )
        ret = Feature(
            data=data,
            path=metadata["kwargs"]["path"],
            name=metadata["kwargs"]["name"],
        )
        ret.metadata = metadata
        return ret
