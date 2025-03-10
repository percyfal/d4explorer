import dataclasses
from pathlib import Path

import daiquiri
import pandas as pd

from .ranges import GFF3, Bed

logger = daiquiri.getLogger("d4explorer")


def convert_to_si_suffix(number):
    """Convert a number to a string with an SI suffix."""
    suffixes = [" ", "kbp", "Mbp", "Gbp", "Tbp"]
    power = len(str(int(number))) // 3
    return f"{number / 1000 ** power:.1f} {suffixes[power]}"


@dataclasses.dataclass
class Feature(Bed):
    """BED4 representation of a feature"""

    data: pd.DataFrame | Bed | GFF3 | Path | str
    path: str = None

    def __post_init__(self):
        if isinstance(self.data, Path) or isinstance(self.data, str):
            self.path = self.data
            try:
                self.data = Bed(self.data).data
            except ValueError:
                self.data = GFF3(self.data)
                self.data = self.data.data[["seqid", "start", "end", "type"]]
        else:
            if isinstance(self.data, GFF3):
                if self.name is None:
                    self.name = self.data.label
                self.data = self.data.data[["seqid", "start", "end", "type"]]
            elif isinstance(self.data, Bed):
                self.data = self.data.data
            elif isinstance(self.data, pd.DataFrame):
                pass
            else:
                raise ValueError("Unsupported data type")
        super().__post_init__()

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
