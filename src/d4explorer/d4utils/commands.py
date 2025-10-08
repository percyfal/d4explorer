import click
import numpy as np
import pandas as pd

from d4explorer.logging import cli_logger as logger
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
        raise NotImplementedError("Regions option is disabled due to bug in pyd4.")
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


@click.command(help=__doc__)
@click.argument("path", nargs=-1, type=click.Path(exists=True))
@click.argument("outfile", type=click.Path(exists=False))
@click.option("--chunk-size", help="region chunk size", default=1000000)
@click.option("--min-coverage", help="minimum coverage", default=0, type=int)
@click.option("--max-coverage", help="maximum coverage", type=int)
@click.option("--regions", "-R", help="region bed file")
@log_level()
def count(path, outfile, chunk_size, min_coverage, max_coverage, regions):
    """Count coverage in input that falls within a specified range.

    The input files are summarized by counting the number of positions
    where the coverage lies within the specified range.

    Example:

        d4explorer count input1.d4input2.d4 output.d4 --min-coverage 5 --max-coverage 20

    Parameters:
        path (list): List of input D4 files.
        outfile (str): Output D4 file.
        chunk_size (int): Region chunk size.
        min_coverage (int): Minimum coverage to count (inclusive).
        max_coverage (int): Maximum coverage to count (inclusive)
        regions (str): Optional region bed file to limit the summarization.
    """
    logger.info("Running d4explorer sum")
    check_outfile(outfile)

    bed = None
    if regions is not None:
        raise NotImplementedError("Regions option is disabled due to bug in pyd4.")
        bed = pd.read_table(
            regions,
            names=["chrom", "begin", "end"],
            usecols=[0, 1, 2],
            header=None,
        )

    if max_coverage is None:
        max_coverage = np.inf
    d4fh = D4Iterator(path, chunk_size=chunk_size, regions=bed)
    d4fh.writer = outfile
    for chrom_name, begin, end in d4fh.iter_chroms():
        y = d4fh.count(chrom_name, begin, end, lower=min_coverage, upper=max_coverage)
        d4fh.writer.write_np_array(chrom_name, 0, y)
    d4fh.writer.close()


@click.command(
    help=__doc__,
)
@click.argument("path", type=click.Path(exists=True))
@click.argument("outfile", type=click.Path(exists=False))
@click.option("--chunk-size", help="region chunk size", default=1000000)
@click.option("--lower", help="lower bound", default=0, type=int)
@click.option("--upper", help="upper bound", type=int)
@click.option("--regions", "-R", help="region bed file")
@log_level()
def filter(path, outfile, chunk_size, lower, upper, regions):  # noqa: A001
    """Filter d4 file on value range and output in BED format.

    Example:

        d4explorer filter input.d4 output.d4 --lower 5 --upper 20

    Parameters:
        path (str): Input D4 file.
        outfile (str): Output BED file.
        chunk_size (int): Region chunk size.
        lower (int): Lower bound (inclusive).
        upper (int): Upper bound (inclusive).
        regions (str): Optional region bed file to limit the filtering.
    """
    logger.info("Running d4explorer filter")

    bed = None
    if regions is not None:
        raise NotImplementedError("Regions option is disabled due to bug in pyd4.")
        bed = pd.read_table(
            regions,
            names=["chrom", "begin", "end"],
            usecols=[0, 1, 2],
            header=None,
        )

    if upper is None:
        upper = np.inf
    d4fh = D4Iterator(path, chunk_size=chunk_size, regions=bed)
    with open(outfile, "w") as outfh:
        for chrom_name, begin, end in d4fh.iter_chroms():
            y = d4fh.filter(chrom_name, begin, end, lower=lower, upper=upper)
            x = np.where(y > 0)[0]
            df = pd.DataFrame(
                {
                    "chrom": chrom_name,
                    "begin": x + begin,
                    "end": x + begin + 1,
                    "name": "d4explorer-filter",
                    "value": y[y > 0],
                }
            )
            df.to_csv(outfh, sep="\t", index=False, header=False)
