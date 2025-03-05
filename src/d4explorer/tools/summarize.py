"""Summarize coverage data."""

import subprocess as sp
import sys
from collections import namedtuple

import click
import daiquiri
import numpy as np
import pandas as pd

from d4explorer.model.ranges import Bed

from .. import __version__

daiquiri.setup(level="WARN")  # noqa

logger = daiquiri.getLogger("d4explorer-summarize")


def log_level(expose_value=False):
    """Setup logging"""

    def callback(ctx, param, value):
        no_log_filter = ctx.params.get("no_log_filter")
        if no_log_filter:
            logger = daiquiri.getLogger("root")
            logger.setLevel(value)
        else:
            loggers = ["d4explorer-summarize"]
            for logname in loggers:
                logger = daiquiri.getLogger(logname)
                logger.setLevel(value)
        return

    return click.option(
        "--log-level",
        default="INFO",
        help="Logging level",
        callback=callback,
        expose_value=expose_value,
        is_eager=False,
    )


@click.group(help=__doc__, name="d4explorer-summarize")
@click.version_option(version=__version__)
def cli():
    """Summarize coverage data."""
    pass


@cli.command()
@click.argument("path", type=click.Path(exists=True, dir_okay=False))
@click.argument("regions", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "--threshold",
    "-t",
    help="coverage threshold for calling a base as present",
    default=3,
)
@click.option(
    "--output-file",
    "-o",
    help="output file",
    default=sys.stdout,
    type=click.File("w"),
)
@log_level()
def group(path, regions, threshold, output_file):
    """Summarize coverage data over regions.

    The input D4 file should consist of five columns (strand is
    excluded). Requires bedtools to run.
    """
    row = namedtuple("row", ["chrom", "begin", "end", "name", "score"])

    def summarize_region(cov, regions):
        bed = Bed(pd.DataFrame(cov))
        ft = Bed(pd.DataFrame(regions))
        scores = []
        for name, group in bed.data.groupby("name"):
            presabs = (group["score"] > threshold).astype(np.int8)
            widths = group["end"] - group["start"]
            cov = presabs * widths
            scores.append(cov.sum())
        ft["score"] = scores
        ft.data.to_csv(output_file, sep="\t", header=None, index=None)

    logger.info("Summarizing coverage data")
    features = Bed(regions)
    last = None
    first = True
    cov = []
    d4view_cmd = ["d4tools", "view", "-R", regions, path]
    d4view = sp.Popen(
        d4view_cmd,
        stdout=sp.PIPE,
        bufsize=1,
        universal_newlines=True,
    )
    findex = 0
    current_feature = features.data.iloc[findex]
    chrom = []
    i = 0
    while True:
        line = d4view.stdout.readline().strip()
        i = i + 1
        if line == "" and d4view.poll() is not None:
            break
        data = line.strip().split("\t")
        data.insert(3, current_feature["name"])
        data = row(*data)
        if first:
            last = data.chrom
            first = False
        if data.chrom != last:
            summarize_region(cov, chrom)
            last = data.chrom
            cov = []
            chrom = []
        cov.append(list(data))

        if int(data.end) == current_feature["end"]:
            chrom.append(current_feature)
            findex = findex + 1
            try:
                current_feature = features.data.iloc[findex]
            except IndexError:
                # last row
                pass

    summarize_region(cov, chrom)
