import sys
from typing import Callable

import click
import daiquiri
from click.decorators import FC

daiquiri.setup(level="WARN")  # noqa
import panel as pn  # noqa

from . import app  # noqa
import datastore  # noqa
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
    exists: bool = True, dir_okay: bool = False
) -> Callable[[FC], FC]:
    return click.argument(
        "path", type=click.Path(exists=exists, dir_okay=dir_okay)
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


@click.group()
def cli():
    """Command line interface for d4explorer."""


@cli.command()
@path_argument()
@port_option()
@annotation_file_option()
@show_option()
@threads_option()
@max_bins_option()
@log_filter_option()
@log_level()
def serve(path, port, annotation_file, show, threads, max_bins):
    """Serve the app"""
    logger.info("Starting panel server")
    key = datastore.cache_key(path, max_bins)

    if key not in pn.state.cache:
        logger.error("cache key not found")
        logger.error("Run d4explorer preprocess first")
        sys.exit(1)

    data, regions = pn.state.as_cached(
        key,
        datastore.preprocess,
        path,
        annotation=annotation_file,
        max_bins=max_bins,
        threads=threads,
    )

    app_ = app.App(
        datastore=datastore.DataStore(
            data=data, filters=["feature", "x"], regions=regions
        ),
        views={
            "indicators": Indicators,
            "summarytable": SummaryTable,
            "featuretable": FeatureTable,
            "histogram": Histogram,
            "boxplot": BoxPlot,
            "violinplot": ViolinPlot,
        },
        title=f"D4explorer: {path}",
    )
    pn.serve(app_.view(), port=port, show=show, verbose=False)


@cli.command()
@path_argument()
@annotation_file_option()
@threads_option()
@max_bins_option()
@log_filter_option()
@log_level()
def preprocess(path, annotation_file, threads, max_bins):
    key = datastore.cache_key(path, max_bins)
    if key in pn.state.cache:
        logger.info("Preprocessing is cached")
        sys.exit(0)

    data, regions = datastore.preprocess(
        path, annotation=annotation_file, max_bins=max_bins, threads=threads
    )
    pn.state.cache[key] = data, regions


if __name__ == "__main__":
    cli()
