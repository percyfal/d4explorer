import click
import daiquiri
import numpy as np
from pyd4 import D4File

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
    for chrom, chromlen in d4.chroms():
        logger.info(f"Chromosome: {chrom}")
        vals = d4[chrom]
        flags = (vals >= min_value) & (vals <= max_value)
        pos = np.where(flags)[0]
        for p, v in zip(pos, vals[flags]):
            print(f"{chrom}\t{p}\t{p+1}\t{v}")
