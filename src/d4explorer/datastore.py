import concurrent.futures
import subprocess as sp
from pathlib import Path
from threading import BoundedSemaphore

import daiquiri
import numpy as np
import pandas as pd
import panel as pn
import param
from panel.viewable import Viewer
from pyd4 import D4File
from tqdm import tqdm

from d4explorer import cache, config
from d4explorer.model import D4AnnotatedHist, D4Hist, Feature, GFF3Annotation

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
    data = D4Hist(
        pd.DataFrame(
            [x.split() for x in res.stdout.decode("utf-8").split("\n") if x],
            columns=["x", "counts"],
        ),
        feature=regions,
    )
    return data


def make_regions(path: Path, annotation: Path = None):
    columns = ["seqid", "start", "end"]
    d4 = D4File(str(path))

    genome = Feature(
        pd.DataFrame([(x[0], 0, x[1]) for x in d4.chroms()], columns=columns),
        name="genome",
    )
    retval = {"genome": genome}
    if annotation is None:
        return d4, retval
    # Assume gff3 for now
    logger.info("Reading annotation")
    annot = GFF3Annotation(annotation)
    for ft in annot.feature_types:
        retval[ft] = Feature(annot[ft])
    logger.info("Made annotation regions")
    return d4, retval


def preprocess(
    path: Path,
    *,
    annotation: Path = None,
    max_bins: int = 1_000,
    threads: int = 1,
) -> D4AnnotatedHist:
    d4, regions = make_regions(path, annotation)
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

    d4list = []
    for x in tqdm(futures):
        data = x.result()
        data.genome_size = len(regions["genome"])
        d4list.append(data)

    logger.info("Computed summary dataframe")
    if annotation is not None:
        annotation = GFF3Annotation(annotation)
    data = D4AnnotatedHist(
        path=path,
        max_bins=max_bins,
        data=d4list,
        annotation=annotation,
        genome_size=len(regions["genome"]),
    )
    return data


class DataStore(Viewer):
    """Class representing the main data store.

    Load data from cache and respond to filters to create views of the
    data.
    """

    dataset = pn.widgets.Select(name="Dataset")

    load_data_button = pn.widgets.Button(
        name="Load Data",
        button_type="success",
        margin=(10, 10),
        description="Load data from selected dataset.",
    )

    cachedir = param.Path(
        default=cache.CACHEDIR,
        doc="Path to cache directory",
        allow_None=True,
    )

    def __init__(self, **params):
        super().__init__(**params)
        self.cache = cache.D4ExplorerCache(self.cachedir)
        self.data = None
        self.dataset.options = self.cache.keys
        self.dataset.value = None

    def _setup_data(self):
        pass

    @pn.depends("dataset")
    def load_data(self):
        if self.dataset.value is None:
            return
        logger.info("Loading data for dataset %s", self.dataset.value)
        self.data = self.cache.get(self.dataset.value)
        print(type(self.data))

    def add_data(self, data):
        """Add data to the cache."""
        self.cache.add(data)

    @pn.depends("dataset")
    def shape(self):
        if self.data is None:
            return pn.Column("### Shape", "No data loaded")
        return pn.Column(
            "### Shape", self.data.data.data.shape, self.dataset.value
        )

    @pn.depends("dataset", "load_data_button.value")
    def __panel__(self):
        self.load_data()
        # if self.data is not None:
        #     cdhist = CDHistogram(data=self.data)
        # else:
        #     print("No data loaded")
        #     cdhist = pn.Column("Nope data loaded")
        # return pn.Column(self.shape, cdhist)
        return pn.Column(self.shape)

    def sidebar(self) -> pn.Card:
        return pn.Column(
            pn.Card(
                self.dataset,
                self.load_data_button,
                collapsed=False,
                title="Dataset options",
                header_background=config.SIDEBAR_BACKGROUND,
                active_header_background=config.SIDEBAR_BACKGROUND,
                styles=config.VCARD_STYLE,
            ),
        )
