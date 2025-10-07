"""Sum the first track from multiple d4 files over a chromosome region"""

import click
import pandas as pd

from d4explorer.logging import app_logger as logger
from d4explorer.logging import log_level

from .d4iter import D4Iterator, check_outfile


@click.command(
    help=__doc__,
)
@click.argument("path", nargs=-1, type=click.Path(exists=True))
@click.argument("outfile", type=click.Path(exists=False))
@click.option("--chunk-size", help="region chunk size", default=1000000, type=int)
@click.option("--regions", "-R", help="region bed file")
@log_level()
def sum(  # noqa: A001
    path,
    outfile,
    chunk_size,
    regions,
):
    """Sum first track from multiple d4 files to a single-track file.

    The input files are summarized by summing the values at each position.
    The output file is created in the same format as the input files.

    Example:

        d4explorer sum input1.d4 input2.d4 output.d4

    Parameters:
        path (list): List of input D4 files.
        outfile (str): Output D4 file.
        chunk_size (int): Region chunk size.
        regions (str): Optional region bed file to limit the summarization.
    """
    logger.info("Running d4explorer sum")
    check_outfile(outfile)

    bed = None
    if regions is not None:
        bed = pd.read_table(
            regions,
            names=["chrom", "begin", "end"],
            usecols=[0, 1, 2],
            header=None,
        )

    d4fh = D4Iterator(path, chunk_size=chunk_size, regions=bed)
    logger.debug(d4fh)
    d4fh.writer = outfile
    for chrom_name, begin, end in d4fh.iter_chroms():
        y = d4fh.sum(chrom_name, begin, end)
        d4fh.writer.write_np_array(chrom_name, 0, y)
    d4fh.writer.close()
