import panel as pn
import param
from panel.viewable import Viewer

from d4explorer import config
from d4explorer.cache import CACHEDIR, D4ExplorerCache
from d4explorer.logging import app_logger as logger

pn.extension(sizing_mode="stretch_width")


class DataStore(Viewer):
    """Class representing the main data store.

    Load data from cache and respond to filters to create views of th e data.
    """

    dataset = pn.widgets.Select(name="Dataset")

    load_data_button = pn.widgets.Button(
        name="Load Data",
        button_type="success",
        margin=(10, 10),
        description="Load data from selected dataset.",
    )

    cachedir = param.Path(
        default=CACHEDIR,
        doc="Path to cache directory",
        allow_None=True,
    )

    def __init__(self, **params):
        super().__init__(**params)
        self.cache = D4ExplorerCache(self.cachedir)
        self.data = None
        self.dataset.options = self.cache.keys
        self.dataset.value = None

    @pn.depends("dataset")
    def load_data(self):
        if self.dataset.value is None:
            return
        logger.info("Loading data for dataset %s", self.dataset.value)
        self.data = self.cache.get(self.dataset.value)

    def add_data(self, data):
        """Add data to the cache."""
        self.cache.add(data)

    @pn.depends("dataset")
    def shape(self):
        if self.data is None:
            return pn.Column("### Shape", "No data loaded")
        return pn.Column("### Shape", self.data.data.data.shape, self.dataset.value)

    @pn.depends("dataset", "load_data_button.value")
    def __panel__(self):
        self.load_data()
        # if self.data is not None:
        #     cdhist = CDHistogram(data=self.data)
        # else:
        #     print("No data loaded")
        #     cdhist = pn.Column("Nope data loaded")
        # return pn.Column(self.shape, cdhist)
        return pn.Column(self.shape)

    def sidebar(self) -> pn.Card:
        return pn.Column(
            pn.Card(
                self.dataset,
                self.load_data_button,
                collapsed=False,
                title="Dataset options",
                header_background=config.SIDEBAR_BACKGROUND,
                active_header_background=config.SIDEBAR_BACKGROUND,
                styles=config.VCARD_STYLE,
            ),
        )


class App(Viewer):
    datastore = param.ClassSelector(class_=DataStore)

    def __init__(self, **params):
        super().__init__(**params)

    def view(self):
        self._template = pn.template.FastListTemplate(
            title="D4 Explorer",
            sidebar=[self.datastore.sidebar],
            main=self.datastore,
        )
        return self._template


def sandbox(servable, **kw):
    """Sandbox version of the app"""
    logger.info("Running scratch sandbox")

    kwargs = {}
    if "cachedir" in kw:
        kwargs["cachedir"] = kw.pop("cachedir")
    ds = DataStore(**kwargs)
    app_ = App(datastore=ds)

    if servable:
        return app_.view().servable()
    return pn.serve(app_.view(), **kw)
