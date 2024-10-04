import pathlib

import click
import daiquiri

daiquiri.setup(level="WARN")  # noqa
import panel as pn  # noqa

from . import app  # noqa


logger = daiquiri.getLogger("tseda")


def log_level(expose_value=False):
    """Setup logging"""

    def callback(ctx, param, value):
        no_log_filter = ctx.params["no_log_filter"]
        if no_log_filter:
            logger = daiquiri.getLogger("root")
            logger.setLevel(value)
        else:
            loggers = ["tseda", "cache", "bokeh", "tornado"]
            for logname in loggers:
                logger = daiquiri.getLogger(logname)
                logger.setLevel(log_level)
            logger = daiquiri.getLogger("bokeh.server.protocol_handler")
            logger.setLevel("CRITICAL")
        return

    return click.option(
        "--log-level",
        default="INFO",
        help="Logging level",
        callback=callback,
        expose_value=expose_value,
        is_eager=True,
    )


@click.group()
def cli():
    """Command line interface for coveda."""


@cli.command()
@click.argument("path", type=click.Path(exists=True, dir_okay=False))
@click.option("--port", default=8080, help="Port to serve on")
@click.option(
    "--show/--no-show",
    default=True,
    help="Launch a web-browser showing the app",
)
@log_level()
@click.option(
    "--no-log-filter",
    default=False,
    is_flag=True,
    help="Do not filter the output log (advanced debugging only)",
)
def serve(path, port, show, log_level, no_log_filter):
    """Serve the app"""
    loger.info("Starting panel server")
