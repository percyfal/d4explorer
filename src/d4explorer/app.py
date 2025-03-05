import daiquiri
import panel as pn
import param
from panel.viewable import Viewer

from .datastore import DataStore, DataStoreSummarize

daiquiri.setup(level="WARN")  # noqa


logger = daiquiri.getLogger("d4explorer")
pn.extension("vega", throttled=True)
pn.extension(sizing_mode="stretch_width")


RAW_CSS = """
        .sidenav#sidebar {
            background-color: WhiteSmoke;
        }
        .title {
            font-size: var(--type-ramp-plus-2-font-size);
        }
    """
DEFAULT_PARAMS = {
    "site": "d4explorer",
    "theme_toggle": False,
}


class App(Viewer):
    datastore = param.ClassSelector(class_=DataStore | DataStoreSummarize)

    def __init__(self, **params):
        super().__init__(**params)
        self.title = self.datastore.title

    def view(self):
        self._template = pn.template.FastListTemplate(
            title=self.title,
            sidebar=[self.datastore.sidebar],
            main=self.datastore,
        )
        return self._template


def serve(servable, summarize=False, **kw):
    """Serve the app"""
    logger.info("Serving main app")

    kwargs = {}
    if "cachedir" in kw:
        kwargs["cachedir"] = kw.pop("cachedir")
    if summarize:
        ds = DataStoreSummarize(**kwargs)
    else:
        ds = DataStore(**kwargs)
    app_ = App(datastore=ds)

    if servable:
        return app_.view().servable()
    return pn.serve(app_.view(), **kw)
