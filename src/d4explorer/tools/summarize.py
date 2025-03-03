"""Summarize coverage data."""

import subprocess as sp
import sys

import click
import daiquiri
import numpy as np
import pandas as pd

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
            loggers = ["d4explorer-d4filter"]
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
def group(path, regions, threshold, output_file):
    """Summarize coverage data over regions.

    The input D4 file should consist of five columns (strand is
    excluded). Requires bedtools to run.
    """

    def summarize_region(cov, chrom):
        df = pd.DataFrame(
            cov,
            columns=["chrom", "start", "end", "score", "name"],
        )
        df = df.astype(
            {
                "chrom": str,
                "start": np.int64,
                "end": np.int64,
                "score": np.int32,
                "name": str,
            }
        )
        for name, group in df.groupby("name"):
            presabs = (group["score"] > threshold).astype(np.int8)
            widths = group["end"] - group["start"]
            cov = presabs * widths
            output_file.write(f"{name}\t{cov.sum()}\t{widths.sum()}\n")

    logger.info("Summarizing coverage data")
    with open(regions, "r") as fh:
        data = fh.readline().strip().split("\t")
        if len(data) != 4:
            raise ValueError("Region file must have four columns")
    last = None
    first = True
    cov = []
    d4view = sp.Popen(
        ["d4tools", "view", "-R", regions, path],
        stdout=sp.PIPE,
        bufsize=1,
        universal_newlines=True,
    )
    intersect = sp.Popen(
        ["bedtools", "intersect", "-a", "-", "-b", regions, "-wb"],
        stdin=d4view.stdout,
        stdout=sp.PIPE,
        bufsize=1,
        universal_newlines=True,
    )
    cut = sp.Popen(
        ["cut", "-f", "1,2,3,4,8"],
        stdin=intersect.stdout,
        stdout=sp.PIPE,
        bufsize=1,
        universal_newlines=True,
    )
    while True:
        line = cut.stdout.readline().strip()
        if line == "" and cut.poll() is not None:
            break
        if line:
            rname = line.strip().split("\t")[0]
            if first:
                last = rname
                first = False
        if rname != last:
            summarize_region(cov, last)
            last = rname
            cov = []
        else:
            cov.append(line.strip().split("\t"))
    summarize_region(cov, last)
