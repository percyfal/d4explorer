import multiprocessing  # noqa
from pathlib import Path  # noqa
from typing import Callable

import click
import daiquiri
import pandas as pd  # noqa
import panel as pn  # noqa
from click.decorators import FC

from d4explorer import (
    cache,  # noqa
    datastore,  # noqa
)
from d4explorer.cli import log_level  # noqa
from d4explorer.d4utils import commands as d4utils_cmd  # noqa
from d4explorer.model import d4  # noqa

from . import (
    __version__,  # noqa
    app,  # noqa
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


def cachedir_option() -> Callable[[FC], FC]:
    return click.option(
        "--cachedir",
        default=cache.CACHEDIR,
        expose_value=True,
        help="Set the cache dir",
    )


def path_argument(
    exists: bool = True, dir_okay: bool = False, nargs: int = 1
) -> Callable[[FC], FC]:
    return click.argument(
        "path", type=click.Path(exists=exists, dir_okay=dir_okay), nargs=nargs
    )


def region_argument(
    exists: bool = True, dir_okay: bool = False, nargs: int = 1
) -> Callable[[FC], FC]:
    return click.argument(
        "region",
        type=click.Path(exists=exists, dir_okay=dir_okay),
        nargs=nargs,
    )


def annotation_file_option(default: str = None) -> Callable[[FC], FC]:
    return click.option(
        "--annotation-file",
        default=default,
        type=click.Path(exists=True),
        help="Annotation file in gff format",
    )


def threads_option(default: int = 1) -> Callable[[FC], FC]:
    return click.option(
        "--threads",
        default=default,
        help="Number of threads per worker to use for pre-processing",
        type=click.IntRange(1, multiprocessing.cpu_count()),
    )


def workers_option(default: int = 1) -> Callable[[FC], FC]:
    return click.option(
        "--workers",
        default=default,
        help="Number of workers to use for pre-processing",
        type=click.IntRange(1, multiprocessing.cpu_count()),
    )


def threshold_option(default: int = 3) -> Callable[[FC], FC]:
    return click.option(
        "--threshold",
        default=default,
        help="Coverage threshold for calling a base as present",
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
@click.version_option(version=__version__)
def cli():
    """Command line interface for d4explorer."""


@cli.command()
@path_argument(nargs=-1)
@annotation_file_option()
@threads_option()
@workers_option()
@max_bins_option()
@log_filter_option()
@log_level(logger)
@cachedir_option()
def preprocess(path, annotation_file, threads, workers, max_bins, cachedir):
    """Preprocess data for the app"""
    d4cache = cache.D4ExplorerCache(cachedir)
    if len(path) == 0:
        logger.info("Provide a D4 file for processing")
        return
    if annotation_file is not None:
        annotation_file = Path(annotation_file)

    for p in path:
        p = Path(p)
        logger.info("Preprocessing %s", p)
        key = d4.D4AnnotatedHist.cache_key(
            p, max_bins=max_bins, annotation=annotation_file
        )

        if d4cache.has_key(key):
            logger.info("Preprocessing is cached: %s", key)
            continue

        data = datastore.preprocess(
            p,
            annotation=annotation_file,
            max_bins=max_bins,
            threads=threads,
            workers=workers,
        )
        cache_data, metadata = data.to_cache()
        for d, md in cache_data:
            d4cache.add(value=(md, d), key=md.get("id"))
        d4cache.add(value=(metadata, None), key=metadata.get("id"))


@cli.command(hidden=True)
@region_argument()
@path_argument(nargs=-1)
@threads_option()
@workers_option()
@threshold_option()
@log_filter_option()
@log_level(logger)
@cachedir_option()
def preprocess_feature_coverage(path, region, threads, workers, threshold, cachedir):
    """WIP: Preprocess feature coverage data.

    Classify features as present / absent based on an average coverage
    threshold.
    """
    d4cache = cache.D4ExplorerCache(cachedir)

    logger.info("Preprocessing feature coverage data.")
    plist = []
    cache_keys = []
    for p in path:
        p = Path(p)
        logger.info("Preprocessing %s", p)
        key = d4.D4FeatureCoverage.cache_key(p, Path(region), threshold=threshold)
        cache_keys.append(key)
        if d4cache.has_key(key):
            logger.info("Preprocessing is cached: %s", key)
            continue
        plist.append(p)

    if len(plist) == 0:
        logger.info("All feature coverage files cached; exiting")
        return

    data = datastore.preprocess_feature_coverage(
        plist,
        region=region,
        threshold=threshold,
        threads=threads,
        workers=workers,
    )
    for d in data:
        d4cache.add(d)
    result = d4.D4FeatureCoverageList(
        keylist=cache_keys, region=region, threshold=threshold
    )
    d4cache.add(result)


@cli.command()
@port_option()
@show_option()
@threads_option()
@log_filter_option()
@log_level(logger)
@cachedir_option()
@click.option("--summarize", is_flag=True, default=False, help="Run summarize analysis")
@click.option("--servable", is_flag=True, default=False, help="Make app servable")
def serve(port, show, threads, servable, cachedir, summarize):
    """Serve the app."""
    app.serve(
        port=port,
        show=show,
        threads=threads,
        servable=servable,
        cachedir=cachedir,
        verbose=False,
        summarize=summarize,
    )


# Commands defined in
cli.add_command(d4utils_cmd.sum)


if __name__ == "__main__":
    cli()
