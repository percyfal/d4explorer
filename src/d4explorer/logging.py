import click
import daiquiri

daiquiri.setup(level="WARN")  # noqa

logger = daiquiri.getLogger("d4explorer")


def log_level(expose_value=False):
    """Setup logging level.

    Parameters:
        expose_value (bool): Whether to expose the value to the command function.
    """

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
