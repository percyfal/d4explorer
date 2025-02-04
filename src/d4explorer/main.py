"""Helper module for serving the d4explorer app from the command line
using panel serve.

This module is used to serve the d4explorer app from the command line
using panel serve. One use case is for development purposes where the
--dev argument enables automated reloading of the app when the source
code changes. To launch the app from the command line run:

$ panel serve --dev --admin --show --args path/to/sum.d4
  --annotation-file path/to/annotation.gff3

See https://panel.holoviz.org/how_to/server/commandline.html for more
information.
"""

from d4explorer import app  # noqa
from d4explorer import datastore  # noqa
from d4explorer import views
import daiquiri
import sys
from collections import deque

daiquiri.setup(level="INFO")  # noqa
logger = daiquiri.getLogger("d4explorer")


if len(sys.argv) < 2:
    logger.error("Please provide the path to a D4 file via the --args option.")
    sys.exit(1)


args = {}
arglist = deque(sys.argv)
while len(arglist) > 0:
    arg = arglist.popleft()
    if arg == "main.py":
        pass
    elif arg == "--annotation-file":
        args["annotation_file"] = arglist.popleft()
    elif arg == "--max-bins":
        args["max_bins"] = int(arglist.popleft())
    elif arg == "--threads":
        args["threads"] = int(arglist.popleft())
    elif not arg.startswith("-"):
        path = arg

logger.info("Reading data from %s", path)
data, regions = datastore.preprocess(
    path,
    annotation=args.get("annotation_file", None),
    max_bins=args.get("max_bins", 1000),
    threads=args.get("threads", 1),
)

app_ = app.App(
    datastore=datastore.DataStore(
        data=data, filters=["feature", "x"], regions=regions
    ),
    views={
        "indicators": views.Indicators,
        "summarytable": views.SummaryTable,
        "featuretable": views.FeatureTable,
        "histogram": views.Histogram,
        "boxplot": views.BoxPlot,
        "violinplot": views.ViolinPlot,
    },
    title="D4explorer",
)

app_.view().servable()
