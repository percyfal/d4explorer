import daiquiri
import panel as pn
import param
from panel.viewable import Viewer

from d4explorer import config
from d4explorer.cache import D4ExplorerCache

daiquiri.setup(level="WARN")  # noqa


logger = daiquiri.getLogger("d4explorer")
pn.extension(sizing_mode="stretch_width")


class DataStore(Viewer):
    dataset = pn.widgets.Select(name="Dataset")

    load_data_button = pn.widgets.Button(
        name="Load Data",
        button_type="success",
        margin=(10, 10),
        description="Load data from selected dataset.",
    )

    def __init__(self, **params):
        super().__init__(**params)
        self.cache = D4ExplorerCache()
        self.data = None
        self.regions = None
        self.dataset.options = self.cache.keys
        self.dataset.value = None

    @pn.depends("dataset")
    def load_data(self):
        if self.dataset.value is None:
            return
        logger.info("Loading data for dataset %s", self.dataset.value)
        self.data, self.regions = self.cache.get(self.dataset.value)

    @pn.depends("dataset", watch=True)
    def shape(self):
        if self.data is None:
            return pn.Column("### Shape", "No data loaded")
        return pn.Column("### Shape", self.data.shape, self.dataset.value)

    @pn.depends("dataset", "load_data_button.value", watch=True)
    def __panel__(self):
        self.load_data()
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
            )
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

    ds = DataStore()
    app_ = App(datastore=ds)

    if servable:
        return app_.view().servable()
    return pn.serve(app_.view(), **kw)
