import concurrent.futures
import os
import subprocess as sp
from dataclasses import dataclass
from tempfile import mkdtemp
from threading import BoundedSemaphore

import daiquiri
import numpy as np
import pandas as pd
import panel as pn
import param
from panel.viewable import Viewer
from pyd4 import D4File
from tqdm import tqdm

from d4explorer import cache

logger = daiquiri.getLogger("d4explorer")

CARD_STYLE = """
:host {{
  box-shadow: rgba(50, 50, 93, 0.25) 0px 6px 12px -2px, rgba(0, 0, 0, 0.3) 0px 3px 7px -3px;
  padding: {padding};
}} """  # noqa

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

KNOWN_FEATURES = [
    "genome",
    "intergenic",
    "gene",
    "mRNA",
    "CDS",
    "exon",
    "UTR",
    "five_prime_UTR",
    "three_prime_UTR",
]


def order_features(values):
    order = []
    if isinstance(values, np.ndarray):
        values = values.tolist()
    for ft in KNOWN_FEATURES:
        if ft in values:
            order.append(ft)
            values.remove(ft)
    if len(values) > 0:
        order.extend(values)
    return order


def convert_to_si_suffix(number):
    """Convert a number to a string with an SI suffix."""
    suffixes = [" ", "kbp", "Mbp", "Gbp", "Tbp"]
    power = len(str(int(number))) // 3
    return f"{number / 1000 ** power:.1f} {suffixes[power]}"


class MaxQueuePool:
    """This Class wraps a concurrent.futures.Executor limiting the
    size of its task queue.

    If `max_queue_size` tasks are submitted, the next call to submit
    will block until a previously submitted one is completed.

    cf https://gist.github.com/noxdafox/4150eff0059ea43f6adbdd66e5d5e87e
    """

    def __init__(self, executor, *, max_queue_size, max_workers=None):
        logger.info(
            "Initializing queue with %i queue slots, %i workers",
            max_queue_size,
            max_workers,
        )
        self.pool = executor(max_workers=max_workers)
        self.pool_queue = BoundedSemaphore(max_queue_size)

    def submit(self, fn, *args, **kwargs):
        """Submit a new task to the pool. This will block if the queue
        is full"""
        self.pool_queue.acquire()  # pylint: disable=consider-using-with
        future = self.pool.submit(fn, *args, **kwargs)
        future.add_done_callback(self.pool_queue_callback)

        return future

    def pool_queue_callback(self, _):
        """Called when a future is done. Releases one queue slot."""
        self.pool_queue.release()


def d4hist(args):
    """Compute histogram from d4. Call d4tools as the pyd4 interface
    is not working properly."""
    path, regions, max_bins = args
    try:
        res = sp.run(
            [
                "d4tools",
                "stat",
                "-s",
                "hist",
                "-r",
                str(regions.temp_file),
                "--max-bin",
                str(max_bins),
                path,
            ],
            capture_output=True,
        )
    except sp.CalledProcessError as e:
        logger.error(e)
    data = pd.DataFrame(
        [x.split() for x in res.stdout.decode("utf-8").split("\n") if x],
        columns=["x", "counts"],
    )
    data.drop([0, data.shape[0] - 1], inplace=True)
    data["x"] = data["x"].astype(int)
    data["counts"] = data["counts"].astype(int)
    return data, regions


def make_vector(df, sample_size):
    """Make vector from dataframe."""
    n = np.sum(df["counts"])
    try:
        data = np.random.choice(
            df["x"].rx.value,
            size=min(int(sample_size), n.rx.value),
            p=df["counts"].rx.value / n.rx.value,
        )
    except ValueError:
        data = None
    return data


def make_regions(path, annotation=None):
    columns = ["seqid", "start", "end"]
    d4 = D4File(path)

    genome = Feature(
        "genome",
        pd.DataFrame([(x[0], 0, x[1]) for x in d4.chroms()], columns=columns),
    )
    retval = {"genome": genome}
    if annotation is None:
        return d4, retval
    # Assume gff3 for now
    logger.info("Reading annotation")
    df_annot = pd.read_table(
        annotation, names=GFF3_COLUMNS, comment="#", header=None, sep="\t"
    )
    for ft, reg in df_annot.groupby("type"):
        retval[ft] = Feature(ft, reg[columns])
    logger.info("Made annotation regions")
    return d4, retval


def preprocess(path, *, annotation=None, max_bins=1_000, threads=1):
    d4, regions = make_regions(path, annotation)
    dflist = []
    genome_size = np.sum(x[1] for x in d4.chroms())
    futures = []
    pool = MaxQueuePool(
        concurrent.futures.ProcessPoolExecutor,
        max_workers=threads,
        max_queue_size=int(2 * threads),
    )

    def _make_processes():
        for reg in regions.values():
            yield path, reg, max_bins

    generator = _make_processes()

    for args in generator:
        futures.append(pool.submit(d4hist, args))

    dflist = []
    for x in tqdm(futures):
        data, reg = x.result()
        d = pd.DataFrame(
            {
                "path": path,
                "feature": reg.name,
                "x": data["x"],
                "counts": data["counts"],
            }
        )
        d["nbases"] = d["counts"] * d["x"]
        d["coverage"] = d["nbases"] / genome_size
        dflist.append(d)

    df = pd.concat(dflist)
    logger.info("Computed summary dataframe")
    return df, regions


@dataclass
class Feature:
    name: str
    data: pd.DataFrame

    def __post_init__(self):
        assert all(self.data.columns.values == ["seqid", "start", "end"])
        self._total = np.sum(self.data["end"] - self.data["start"])
        temp_dir = mkdtemp()
        self._temp_file = os.path.join(temp_dir, "regions.bed")
        self.write()

    @property
    def total(self):
        return self._total

    @property
    def temp_file(self):
        return self._temp_file

    def write(self):
        logger.info("Writing regions to %s", self.temp_file)
        self.data.to_csv(self.temp_file, sep="\t", index=False)

    def format(self):
        return convert_to_si_suffix(self.total)


class DataStore(Viewer):
    keys = cache.get_keys()

    data = param.DataFrame()

    filters = param.List(constant=True)

    regions = param.Dict(constant=True)

    dataset = param.Selector(objects=keys)

    def __init__(self, **params):
        super().__init__(**params)
        dfx = self.param.data.rx()
        datax = self.param.data.rx()
        self._paths = datax.rx.value["path"].unique().tolist()
        widgets = []
        for filt in self.filters:
            dtype = self.data.dtypes[filt]
            if dtype.kind == "i":
                widget = pn.widgets.RangeSlider(
                    name=filt,
                    start=dfx[filt].min(),
                    end=dfx[filt].max(),
                    value=(dfx[filt].min(), dfx[filt].max()),
                    step=1,
                )
                condition = dfx[filt].between(*widget.rx())
            else:
                try:
                    options = dfx[filt].unique().tolist()
                except AttributeError:
                    options = dfx[filt].cat.categories.to_list()
                value = []
                widget = pn.widgets.MultiChoice(
                    name=filt, options=options, value=value
                )
                condition = dfx[filt].isin(
                    widget.rx().rx.where(widget, options)
                )
                if filt == "feature":
                    datax = datax[condition]
                if filt == "path":
                    i = dfx[filt].isin(
                        widget.rx().rx.where(widget, [options[0]])
                    )
                    datax = datax[i]
            dfx = dfx[condition]
            widgets.append(widget)
        self.filtered = dfx
        self.count = dfx.rx.len()
        self.feature_data = datax
        self._widgets = widgets
        # self.shape = pn.bind(self.dataset, self.load_coverage)

    @param.depends("dataset")
    def load_coverage(self, key):
        print("loading data from key ", key)
        logger.info("loading data from key ", key)
        data, regions = cache.cache[key]
        return data.shape

    @property
    def paths(self):
        return self._paths

    def __panel__(self):
        params = pn.Column(
            "## Parameters",
            pn.Param(
                self.param,
                parameters=["dataset"],
                widgets={"dataset": pn.widgets.Select},
            ),
        )
        filters = pn.Column(
            "## Filters",
            *self._widgets,
            stylesheets=[CARD_STYLE.format(padding="5px 10px")],
            margin=10,
        )
        return pn.Column(params, filters)
