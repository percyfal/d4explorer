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
def count_by_region(path, regions, threshold, output_file):
    """Count the number of accessible bases in predefined regions.

    Count the number of bases in predefined regions that have coverage
    above a given threshold. All intervals are summed and grouped by
    the region.

    Parameters:
        path (Path): Path to D4 file with columns seqid, begin, end and score.
        regions (Path): Path to BED file with regions. The BED file should consist
                        of four columns seqid, begin, end and name.
        threshold (int): Coverage threshold for calling a base as present.
        output_file (File): Output file in BED5 format.
    """
    row = namedtuple("row", ["seqid", "begin", "end", "name", "score"])

    def summarize_region(cov, ranges):
        bed = Bed(data=pd.DataFrame(cov))
        ft = Bed(data=pd.DataFrame(ranges))
        scores = []
        for name, group in bed.data.groupby("name"):
            presabs = (group["score"] > threshold).astype(np.int8)
            widths = group["end"] - group["start"]
            cov = presabs * widths
            scores.append(cov.sum())
        ft["score"] = scores
        ft.data.to_csv(output_file, sep="\t", header=None, index=None)

    logger.info("Summarizing coverage data")
    features = Bed(data=regions)
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
    ranges = []
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
            last = data.seqid
            first = False
        if data.seqid != last:
            summarize_region(cov, ranges)
            last = data.seqid
            cov = []
            ranges = []
        cov.append(list(data))

        if int(data.end) == current_feature["end"]:
            ranges.append(current_feature)
            findex = findex + 1
            try:
                current_feature = features.data.iloc[findex]
            except IndexError:
                # last row
                pass

    summarize_region(cov, ranges)
