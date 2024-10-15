import sys
import click
import daiquiri
import numpy as np
import pandas as pd
from pyd4 import D4File
from tqdm import tqdm

daiquiri.setup(level="WARN")  # noqa

logger = daiquiri.getLogger("coveda-d4filter")


def log_level(expose_value=False):
    """Setup logging"""

    def callback(ctx, param, value):
        no_log_filter = ctx.params.get("no_log_filter")
        if no_log_filter:
            logger = daiquiri.getLogger("root")
            logger.setLevel(value)
        else:
            loggers = ["coveda-d4filter"]
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
    """Command line interface for d4filter. Prints filtered results in BED format to stdout."""
    logger.info("Running d4filter")
    d4 = D4File(path)
    dflist = []
    for chrom, chromlen in tqdm(d4.chroms()):
        logger.debug(f"Chromosome: {chrom}")
        vals = d4[chrom]
        flags = (vals >= min_value) & (vals <= max_value)
        pos = np.where(flags)[0]
        df = pd.DataFrame({
            "chrom": chrom,
            "begin": pos,
            "end": pos+1,
            "value": vals[flags],
        })
        dflist.append(df)
    df = pd.concat(dflist)
    df.to_csv(sys.stdout, sep="\t", index=False, header=False)
