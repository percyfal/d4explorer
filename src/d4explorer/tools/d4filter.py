"""Filter d4 file on value range and output in BED format."""

import sys

import click
import numpy as np
import pandas as pd
from pyd4 import D4File
from tqdm import tqdm

from d4explorer.logging import cli_logger as logger
from d4explorer.logging import log_level


@click.command()
@click.argument("path", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "--min", "min_value", default=0, help="Minimum value (inclusive)", type=int
)
@click.option(
    "--max",
    "max_value",
    default=10,
    help="Maximum value (inclusive)",
    type=int,
)
@log_level()
def cli(path, min_value, max_value):
    """Command line interface for d4filter. Prints filtered results in
    BED5 format to stdout.

    Parameters:
        path (str): Input D4 file.
        min_value (int): Minimum value (inclusive).
        max_value (int): Maximum value (inclusive).
    """
    logger.info("Running d4filter")
    d4 = D4File(path)
    dflist = []
    for chrom, chromlen in tqdm(d4.chroms()):
        logger.debug(f"Chromosome: {chrom}")
        vals = d4[chrom]
        flags = (vals >= min_value) & (vals <= max_value)
        pos = np.where(flags)[0]
        df = pd.DataFrame(
            {
                "chrom": chrom,
                "begin": pos,
                "end": pos + 1,
                "name": "d4explorer-d4filter",
                "value": vals[flags],
            }
        )
        dflist.append(df)
    df = pd.concat(dflist)
    df.to_csv(sys.stdout, sep="\t", index=False, header=False)
