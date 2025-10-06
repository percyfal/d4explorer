"""Class for iterating over multiple d4 files."""

import logging
import pathlib
import re
import sys

import numpy as np
import pyd4
from tqdm import tqdm

__shortname__ = __name__.split(".")[-1]

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s [%(name)s:%(funcName)s]: %(message)s",
)

pat = re.compile(r"[ \t]+")


def make_chunks(begin, end, size):
    pos = np.arange(begin, end, size)
    begin_list = pos
    end_list = pos[1 : len(pos)]  # noqa: E203
    end_list = np.append(end_list, end)
    for begin, end in zip(begin_list, end_list):
        yield begin, end


def make_pos(begin, end):
    return np.arange(begin, end) + 1


def check_outfile(outfile):
    if pathlib.Path(outfile).exists():
        logger.error(
            f"{outfile} exists! Make sure to provide a non-existing output file name"
        )
        sys.exit()


def to_str(array):
    """Convert array of arrays to string"""
    return "\n".join("\t".join(list(map(str, x))) for x in array)


def parse_region(region):
    m = re.match(r"^(?P<chrom>[\w]+):?(?P<begin>\d+)?-?(?P<end>\d+)?", region)
    if m is None:
        logger.error(f"Malformatted regions string: {region}")
        sys.exit(1)

    return m.groups()


class D4Iterator:
    """Iterate over multiple d4 paths"""

    def __init__(self, path, chunk_size=10000, regions=None, concat=False):
        self._fh = [pyd4.D4File(x) for x in tqdm(path)]
        self._index = len(self._fh)
        self._chunk_size = chunk_size
        if regions is None:
            if concat:
                self._chroms = [x for fh in self._fh for x in fh.chroms()]
            else:
                self._chroms = self._fh[0].chroms()
        else:
            self._chroms = []
            for chrom_name, end in self._fh[0].chroms():
                reg = [str(chrom_name), 0, end]
                if regions.T.isin(reg).all().any():
                    self._chroms.append((chrom_name, end))

    @property
    def chroms(self):
        return self._chroms

    @property
    def chunk_size(self):
        return self._chunk_size

    @property
    def writer(self):
        return self._writer

    @writer.setter
    def writer(self, fn):
        self._writer = pyd4.D4Builder(str(fn)).add_chroms(self.chroms).get_writer()

    def __iter__(self):
        return self

    def __next__(self):
        if self._index == 0:
            self._index = len(self._fh)
            raise StopIteration
        self._index = self._index - 1
        return self._fh[self._index]

    def iter_chroms(self):
        for chrom_name, end in (pbar := tqdm(self.chroms)):
            pbar.set_description(f"processing chromosome {chrom_name}")
            yield chrom_name, 0, end

    def iter_chunks(self, chrom_name, begin, end):
        for rbegin, rend in (pbar := tqdm(make_chunks(begin, end, self.chunk_size))):
            rname = f"{chrom_name}:{rbegin}-{rend}"
            pbar.set_description(f"processing region {rname}")
            yield rname

    def process_region_chunk(self, rname):
        for i, track in (pbar := tqdm(enumerate(self))):
            pbar.set_description(f"processing track {i}")
            yield i, track.load_to_np(rname)

    def sum(self, chrom_name, begin, end):  # noqa: A003
        """Sum tracks over a chromosome region"""

        def _sum_region_chunk(rname):
            for i, y in self.process_region_chunk(rname):
                if i == 0:
                    x = y
                else:
                    x = x + y
            return x

        for j, rname in enumerate(self.iter_chunks(chrom_name, begin, end)):
            if j == 0:
                y = _sum_region_chunk(rname)
            else:
                y = np.append(y, _sum_region_chunk(rname))
        return y

    def count(self, chrom_name, begin, end, *, lower=0, upper=np.inf):
        """Count tracks whose values lie in a given range over a given
        region"""

        def _count_region_chunk(rname):
            for i, y in self.process_region_chunk(rname):
                if i == 0:
                    x = ((y > lower) & (y < upper)).astype(int)
                else:
                    x = x + ((y > lower) & (y < upper)).astype(int)
            return x

        for j, rname in enumerate(self.iter_chunks(chrom_name, begin, end)):
            if j == 0:
                y = _count_region_chunk(rname)
            else:
                y = np.append(y, _count_region_chunk(rname))
        return y
