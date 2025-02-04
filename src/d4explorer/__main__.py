import click
import daiquiri

daiquiri.setup(level="WARN")  # noqa
import panel as pn  # noqa

from . import app  # noqa
from .datastore import preprocess, DataStore  # noqa
from .views import (  # noqa
    Histogram,
    BoxPlot,
    ViolinPlot,
    SummaryTable,
    Indicators,
    FeatureTable,
)

logger = daiquiri.getLogger("d4explorer")


def log_level(expose_value=False):
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


@click.group()
def cli():
    """Command line interface for d4explorer."""


@cli.command()
@click.argument("path", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "--annotation-file", default=None, help="Annotation file in gff format"
)
@click.option("--port", default=8080, help="Port to serve on")
@click.option(
    "--show/--no-show",
    default=True,
    help="Launch a web-browser showing the app",
)
@click.option(
    "--no-log-filter",
    default=False,
    is_flag=True,
    help="Do not filter the output log (advanced debugging only)",
)
@click.option(
    "--max-bins", default=1000, help="Maximum number of bins to display"
)
@click.option(
    "--threads", default=1, help="Number of threads to use for pre-processing"
)
@log_level()
def serve(path, port, annotation_file, show, no_log_filter, max_bins, threads):
    """Serve the app"""
    logger.info("Starting panel server")
    data, regions = preprocess(
        path, annotation=annotation_file, max_bins=max_bins, threads=threads
    )

    app_ = app.App(
        datastore=DataStore(
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


if __name__ == "__main__":
    cli()
