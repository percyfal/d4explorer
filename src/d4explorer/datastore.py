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
from param.reactive import rx
from pyd4 import D4File
from tqdm import tqdm

from d4explorer import cache, config
from d4explorer.model.coverage import D4FeatureCoverage
from d4explorer.model.d4 import (
    D4AnnotatedHist,
    D4Hist,
)
from d4explorer.model.feature import Feature
from d4explorer.model.ranges import GFF3
from d4explorer.views.d4 import (
    D4BoxPlotView,
    D4HistogramView,
    D4IndicatorView,
    D4ViolinPlotView,
)

logger = daiquiri.getLogger("d4explorer")

CARD_STYLE = """
:host {{
  box-shadow: rgba(50, 50, 93, 0.25) 0px 6px 12px -2px, rgba(0, 0, 0, 0.3) 0px 3px 7px -3px;
  padding: {padding};
}} """  # noqa


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
    path, regions, max_bins, threads = args
    regions.merge()
    regions.write()
    software = "d4tools"
    parameters = [
        "stat",
        "--stat",
        "hist",
        "--max-bin",
        str(max_bins),
        str(path),
    ]
    parameters_nopickle = [
        "--threads",
        str(threads),
        "--region",
        str(regions.temp_file),
    ]
    cmd = [software] + parameters + parameters_nopickle
    logger.info("Running %s", " ".join(cmd))
    try:
        res = sp.run(
            cmd,
            capture_output=True,
        )
    except sp.CalledProcessError as e:
        logger.error(e)
    data = D4Hist(
        data=pd.DataFrame(
            [x.split() for x in res.stdout.decode("utf-8").split("\n") if x],
            columns=["x", "counts"],
        ),
        feature=regions,
    )
    data.metadata = {
        "id": data.cache_key(path, max_bins, regions.name),
        "path": str(path),
        "version": "0.1",
        "parameters": " ".join(parameters),
        "software": software,
        "class": "D4Hist",
    }
    data.feature.metadata = {
        "id": data.feature.cache_key(data.feature.path, data.feature.name),
        "path": str(data.feature.path),
        "version": "0.1",
        "parameters": "",
        "software": "d4explorer",
        "class": "Feature",
    }
    return data


def d4explorer_summarize_regions(args):
    """Summarize coverages over regions"""
    path, regions, threshold = args
    try:
        res = sp.run(
            [
                "d4explorer-summarize",
                "group",
                path,
                regions,
                "--threshold",
                str(threshold),
            ],
            capture_output=True,
        )
    except sp.CalledProcessError as e:
        logger.error(e)
    data = D4FeatureCoverage(
        pd.DataFrame(
            [x.split() for x in res.stdout.decode("utf-8").split("\n") if x],
            columns=["feature", "coverage"],
        ),
        feature=Feature(Path(regions)),
        path=path,
        threshold=threshold,
    )
    return data


def make_regions(path: Path, annotation: Path = None):
    d4 = D4File(str(path))

    genome = Feature(
        data=pd.DataFrame([(x[0], 0, x[1]) for x in d4.chroms()]),
        name="genome",
        path=annotation,
    )
    retval = {"genome": genome}
    if annotation is None:
        return d4, retval
    # Assume gff3 for now
    logger.info("Reading annotation")
    annot = GFF3(data=Path(annotation))
    for ft in annot.feature_types:
        retval[ft] = Feature(data=annot[ft], path=annot.path)
    logger.info("Made annotation regions")
    return d4, retval


def preprocess(
    path: Path,
    *,
    annotation: Path = None,
    max_bins: int = 1_000,
    threads: int = 1,
    workers: int = 1,
) -> D4AnnotatedHist:
    d4, regions = make_regions(path, annotation)
    futures = []
    pool = MaxQueuePool(
        concurrent.futures.ProcessPoolExecutor,
        max_workers=threads,
        max_queue_size=int(workers),
    )

    def _make_processes():
        for reg in regions.values():
            yield path, reg, max_bins, threads

    generator = _make_processes()

    for args in generator:
        futures.append(pool.submit(d4hist, args))

    d4list = []
    for x in tqdm(
        concurrent.futures.as_completed(futures), total=len(futures)
    ):
        data = x.result()
        data.genome_size = len(regions["genome"])
        d4list.append(data)

    logger.info("Computed summary dataframe")
    data = D4AnnotatedHist(
        path=path,
        max_bins=max_bins,
        data=d4list,
        annotation=annotation,
        genome_size=len(regions["genome"]),
    )
    return data


def preprocess_feature_coverage(
    path: list[Path],
    region: Path,
    threshold: int = 3,
    threads: int = 1,
    workers: int = 1,
) -> list:
    futures = []
    pool = MaxQueuePool(
        concurrent.futures.ProcessPoolExecutor,
        max_workers=threads,
        max_queue_size=int(workers),
    )

    def _make_processes():
        for p in path:
            yield p, region, threshold

    generator = _make_processes()

    for args in generator:
        futures.append(pool.submit(d4explorer_summarize_regions, args))

    plist = []
    for x in tqdm(
        concurrent.futures.as_completed(futures), total=len(futures)
    ):
        data = x.result()
        plist.append(data)

    logger.info("Computed feature coverages for %i files", len(plist))
    return plist


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

    slider = pn.widgets.IntRangeSlider(name="Coverage range", start=0)

    features = pn.widgets.MultiChoice(name="Feature list")

    def __init__(self, **params):
        super().__init__(**params)
        self.title = "D4 Explorer"
        self.cache = cache.D4ExplorerCache(self.cachedir)
        self.data = None
        self.dataset.options = [
            x
            for x in self.cache.keys
            if x.startswith("d4explorer:D4AnnotatedHist")
        ]
        if len(self.dataset.options) > 0:
            self.dataset.value = self.dataset.options[0]
        self.dfx = None
        self.load_data()
        if self.data is not None:
            self.features.options = self.data.features
            self.features.value = []
        else:
            logger.warn("No data in cache! Run d4explorer preprocess")

    def _setup_data(self):
        """Setup reactive components here"""
        if self.data is None:
            return
        self.dfx = rx(self.data)
        self.slider.end = self.dfx.max()
        self.slider.value = (0, self.dfx.max())
        condition = self.dfx.between(*self.slider.rx())
        self.dfx = self.dfx[condition]
        self.dfx = self.dfx[self.features]

    def _setup_fix_data(self):
        self.fix_data = {}
        if self.data is None:
            return
        logger.info("Sampling fix data-wide estimates...")
        data = []
        for d4h in self.data.data:
            logger.info(
                "Sampling 1e6 points feature type %s", d4h.feature_type
            )
            x = d4h.sample(n=1_000_000)
            mean_coverage = np.round(np.mean(x), 2)
            median_coverage = np.round(np.median(x), 2)
            std_coverage = np.round(np.std(x), 2)
            pct_60_coverage = np.round(mean_coverage * 0.6, 2)
            pct_70_coverage = np.round(mean_coverage * 0.7, 2)
            pct_80_coverage = np.round(mean_coverage * 0.8, 2)
            pct_90_coverage = np.round(mean_coverage * 0.9, 2)
            median_plus_1sd = np.round(median_coverage + std_coverage, 2)
            median_plus_2sd = np.round(median_coverage + 2 * std_coverage, 2)
            data.append(
                {
                    "feature": d4h.feature_type,
                    "mean_coverage": mean_coverage,
                    "median_coverage": median_coverage,
                    "std_coverage": std_coverage,
                    "pct_60_coverage": pct_60_coverage,
                    "pct_70_coverage": pct_70_coverage,
                    "pct_80_coverage": pct_80_coverage,
                    "pct_90_coverage": pct_90_coverage,
                    "median_plus_1sd": median_plus_1sd,
                    "median_plus_2sd": median_plus_2sd,
                }
            )
        self.fix_data = pd.DataFrame(data).set_index("feature", inplace=False)

    @pn.depends("dataset")
    def load_data(self):
        if self.dataset.value is None:
            return
        logger.info("Loading data for dataset %s", self.dataset.value)
        self.data = self.cache.get(self.dataset.value)
        self._setup_data()
        self._setup_fix_data()

    def add_data(self, data):
        """Add data to the cache."""
        self.cache.add(value=data)

    @pn.depends("dataset")
    def shape(self):
        if self.data is None:
            return pn.Column("### Shape", "No data loaded")
        return pn.Column("### Shape", self.data.shape, self.dataset.value)

    @pn.depends(
        "dataset",
        "load_data_button.value",
        "slider.value_throttled",
        "features.value",
    )
    def __panel__(self):
        if self.load_data_button.value:
            self.load_data()
        if self.data is None:
            return pn.pane.Alert("No data in cache", alert_type="warning")
        indicator = D4IndicatorView(
            data=self.dfx.rx.value, fulldata=self.fix_data
        )
        hv = D4HistogramView(
            data=self.dfx.rx.value,
            xmin=self.slider.rx.value[0],
            xmax=self.slider.rx.value[1],
        )

        boxplot = D4BoxPlotView(data=self.dfx.rx.value)
        violinplot = D4ViolinPlotView(data=self.dfx.rx.value)

        return pn.Column(*[indicator, hv, pn.Row(*[boxplot, violinplot])])

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
            pn.Card(
                self.slider,
                self.features,
                title="Filters",
                collapsed=False,
                header_background=config.SIDEBAR_BACKGROUND,
                active_header_background=config.SIDEBAR_BACKGROUND,
                styles=config.VCARD_STYLE,
            ),
        )


class DataStoreSummarize(Viewer):
    """Class representing the main data store for summary analyses.

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

    # slider = pn.widgets.IntRangeSlider(name="Coverage range", start=0)

    # features = pn.widgets.MultiChoice(name="Feature list")

    def __init__(self, **params):
        super().__init__(**params)
        self.title = "D4 Explorer Summarize"
        self.cache = cache.D4ExplorerCache(self.cachedir)
        self.data = None
        self.dataset.options = [
            x
            for x in self.cache.keys
            if x.startswith("d4explorer-summarize:D4FeatureCoverageList")
        ]
        if len(self.dataset.options) > 0:
            self.dataset.value = self.dataset.options[0]
        self.dfx = None
        self.load_data()

    def _setup_data(self):
        """Setup reactive components here"""
        pass
        # self.dfx = rx(self.data)
        # condition = self.dfx.between(*self.slider.rx())
        # self.dfx = self.dfx[condition]
        # self.dfx = self.dfx[self.features]

    @pn.depends("dataset")
    def load_data(self):
        if self.dataset.value is None:
            return
        logger.info("Loading data for dataset %s", self.dataset.value)
        data = self.cache.get(self.dataset.value)
        self.data = data.load()
        self._setup_data()

    def add_data(self, data):
        """Add data to the cache."""
        self.cache.add(data)

    @pn.depends("dataset")
    def shape(self):
        if self.data is None:
            return pn.Column("### Shape", "No data loaded")
        return pn.Column("### Shape", self.data.shape, self.dataset.value)

    @pn.depends(
        "dataset",
        "load_data_button.value",
    )
    def __panel__(self):
        if self.load_data_button.value:
            self.load_data()

        return pn.Column(*[])

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
            pn.Card(
                title="Filters",
                collapsed=False,
                header_background=config.SIDEBAR_BACKGROUND,
                active_header_background=config.SIDEBAR_BACKGROUND,
                styles=config.VCARD_STYLE,
            ),
        )
