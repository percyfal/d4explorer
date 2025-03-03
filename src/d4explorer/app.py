import daiquiri
import panel as pn
import param
from panel.viewable import Viewer

from . import __version__
from .datastore import DataStore

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


class OldApp(Viewer):
    datastore = param.ClassSelector(class_=DataStore)

    title = param.String()

    views = param.Dict()

    def __init__(self, **params):
        super().__init__(**params)
        updating = self.datastore.filtered.rx.updating()
        updating.rx.watch(
            lambda updating: pn.state.curdoc.hold()
            if updating
            else pn.state.curdoc.unhold()
        )
        order = [
            "indicators",
            "histogram",
            "summarytable",
            "featuretable",
            "boxplot",
            "violinplot",
        ]
        _views = [self.views[k](datastore=self.datastore) for k in order]
        self._views = pn.FlexBox(*(v for v in _views), loading=updating)
        self._views_d = {k: v for k, v in zip(order, self._views)}
        self.unit = _views[1].param.unit

    def load(self):
        return self.view()

    @property
    def version(self):
        return pn.pane.Markdown(
            f"d4explorer, {__version__}", styles={"font_size": "18pt"}
        )

    @param.depends("views")
    def view(self):
        """Creates the main application view.

        Returns:
            pn.Column: A Panel Column containing the datastore and views.
        """
        return pn.template.FastListTemplate(
            title=self.title,
            main=pn.Column(
                *[
                    pn.Column(
                        self._views_d["indicators"],
                        pn.Row(
                            *[self._views_d["histogram"]]
                        ),  # , self._views[2]]),
                        # pn.Row(
                        #     *[self._views[3], self._views[4], self._views[5]]
                        # ),
                    ),
                ]
            ),
            sidebar=[self.version, self.datastore, self.unit],
            raw_css=[RAW_CSS],
            **DEFAULT_PARAMS,
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


def serve(servable, **kw):
    """Serve the app"""
    logger.info("Serving main app")

    kwargs = {}
    if "cachedir" in kw:
        kwargs["cachedir"] = kw.pop("cachedir")
    ds = DataStore(**kwargs)
    app_ = App(datastore=ds)

    if servable:
        return app_.view().servable()
    return pn.serve(app_.view(), **kw)
