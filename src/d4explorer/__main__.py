import sys
from typing import Callable

import click
import daiquiri
from click.decorators import FC

daiquiri.setup(level="WARN")  # noqa
import panel as pn  # noqa
import pandas as pd  # noqa

from . import app  # noqa
from . import __version__  # noqa
from d4explorer import datastore  # noqa
from d4explorer import cache  # noqa
from .views import (  # noqa
    Histogram,
    BoxPlot,
    ViolinPlot,
    SummaryTable,
    Indicators,
    FeatureTable,
)

logger = daiquiri.getLogger("d4explorer")


def log_filter_option(expose_value: bool = False) -> Callable[[FC], FC]:
    """Setup logging filter"""
    return click.option(
        "--no-log-filter",
        default=False,
        is_flag=True,
        expose_value=expose_value,
        help="Do not filter the output log (advanced debugging only)",
    )


def log_level(expose_value: bool = False) -> Callable[[FC], FC]:
    """Setup logging"""

    def callback(ctx, param, value):
        no_log_filter = ctx.params.get("no_log_filter")
        if no_log_filter:
            logger = daiquiri.getLogger("root")
            logger.setLevel(value)
        else:
            loggers = ["d4explorer", "cache", "bokeh", "tornado"]
            for logname in loggers:
                logger = daiquiri.getLogger(logname)
                logger.setLevel(value)
            logger = daiquiri.getLogger("bokeh.server.protocol_handler")
            logger.setLevel("CRITICAL")
        return

    return click.option(
        "--log-level",
        default="INFO",
        help="Logging level",
        callback=callback,
        expose_value=expose_value,
        is_eager=False,
    )


def path_argument(
    exists: bool = True, dir_okay: bool = False, nargs: int = 1
) -> Callable[[FC], FC]:
    return click.argument(
        "path", type=click.Path(exists=exists, dir_okay=dir_okay), nargs=nargs
    )


def annotation_file_option(default: str = None) -> Callable[[FC], FC]:
    return click.option(
        "--annotation-file",
        default=default,
        help="Annotation file in gff format",
    )


def threads_option(default: int = 1) -> Callable[[FC], FC]:
    return click.option(
        "--threads",
        default=default,
        help="Number of threads to use for pre-processing",
    )


def max_bins_option(default: int = 1000) -> Callable[[FC], FC]:
    return click.option(
        "--max-bins", default=default, help="Maximum number of bins to display"
    )


def port_option(default: int = 8080) -> Callable[[FC], FC]:
    return click.option("--port", default=default, help="Port to serve on")


def show_option(default: bool = True) -> Callable[[FC], FC]:
    return click.option(
        "--show/--no-show",
        default=default,
        help="Launch a web-browser showing the app",
    )


def _serve(path, max_bins, servable=False, **kw):
    logger.info("Starting panel server")
    dlist = []

    def _load_coverage(p):
        logger.info("Loading coverage for %s", p)
        key = cache.cache_key(p, max_bins)

        if key not in cache.cache:
            logger.error("cache key not found")
            logger.error("Run `d4explorer preprocess %s` first", p)
            sys.exit(1)

        # TODO: make sure regions are identical for all datasets
        data, regions = cache.cache[key]
        return data, regions

    data, regions = _load_coverage(path)
    dlist.append(data)
    data = pd.concat(dlist)

    ds = datastore.DataStore(
        data=data, filters=["feature", "x"], regions=regions
    )
    app_ = app.App(
        datastore=ds,
        views={
            "indicators": Indicators,
            "summarytable": SummaryTable,
            "featuretable": FeatureTable,
            "histogram": Histogram,
            "boxplot": BoxPlot,
            "violinplot": ViolinPlot,
        },
        title=path,
    )
    if servable:
        return app_.view().servable()
    return pn.serve(app_.view(), **kw)


@click.group()
@click.version_option(version=__version__)
def cli():
    """Command line interface for d4explorer."""


@cli.command()
@path_argument()
@port_option()
@show_option()
@threads_option()
@max_bins_option()
@log_filter_option()
@log_level()
@click.option(
    "--servable", is_flag=True, default=False, help="Make app servable"
)
def serve(path, port, show, threads, max_bins, servable):
    """Serve the app"""
    _ = _serve(
        path, max_bins, servable=servable, port=port, show=show, verbose=False
    )


@cli.command()
@path_argument(nargs=-1)
@annotation_file_option()
@threads_option()
@max_bins_option()
@log_filter_option()
@log_level()
def preprocess(path, annotation_file, threads, max_bins):
    """Preprocess data for the app"""
    for p in path:
        logger.info("Preprocessing %s", p)
        key = cache.cache_key(p, max_bins)

        if key in cache.cache:
            logger.info("Preprocessing is cached")
            continue

        data, regions = datastore.preprocess(
            p, annotation=annotation_file, max_bins=max_bins, threads=threads
        )
        cache.cache[key] = data, regions


if __name__ == "__main__":
    cli()
