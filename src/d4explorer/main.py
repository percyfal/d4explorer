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
from d4explorer import scratch  # noqa
import daiquiri
import sys
from collections import deque
from d4explorer.__main__ import serve, preprocess

daiquiri.setup(level="INFO")  # noqa
logger = daiquiri.getLogger("d4explorer")

arglist = deque(sys.argv)
arglist.popleft()

try:
    argfun = arglist.popleft()
except IndexError:
    argfun = "serve"

if argfun == "serve":
    arglist.append("--servable")
    fun = serve
elif argfun == "preprocess":
    fun = preprocess
elif argfun == "sandbox":
    arglist.append("--servable")
    fun = scratch.sandbox
else:
    fun = serve
    arglist.append("--help")

try:
    fun(arglist, standalone_mode=False)
except Exception as e:
    logger.error(e)
    sys.exit(1)
