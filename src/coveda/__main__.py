import click
import daiquiri

daiquiri.setup(level="WARN")  # noqa
import panel as pn  # noqa

from . import app  # noqa
from .datastore import preprocess, DataStore  # noqa
from .views import Histogram, BoxPlot, ViolinPlot, SummaryTable, Indicators  # noqa

logger = daiquiri.getLogger("coveda")


def log_level(expose_value=False):
    """Setup logging"""

    def callback(ctx, param, value):
        no_log_filter = ctx.params.get("no_log_filter")
        if no_log_filter:
            logger = daiquiri.getLogger("root")
            logger.setLevel(value)
        else:
            loggers = ["tseda", "cache", "bokeh", "tornado"]
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
    """Command line interface for coveda."""


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
    "--annotation-file", default=None, help="Annotation file in gff format"
)
@click.option(
    "--no-log-filter",
    default=False,
    is_flag=True,
    help="Do not filter the output log (advanced debugging only)",
)
@log_level()
@click.option(
    "--max-bins", default=1000, help="Maximum number of bins to display"
)
def serve(path, port, annotation_file, show, no_log_filter, max_bins):
    """Serve the app"""
    logger.info("Starting panel server")
    data = preprocess(path, annotation_file, max_bins)

    app_ = app.App(
        datastore=DataStore(data=data, filters=["feature", "x"]),
        views=[Indicators, SummaryTable, Histogram, BoxPlot, ViolinPlot],
        title="Coveda",
    )
    pn.serve(app_, port=port, show=show, verbose=False)


if __name__ == "__main__":
    cli()
