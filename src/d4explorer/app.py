import panel as pn
import param
from panel.viewable import Viewer

from .datastore import DataStore

pn.extension("vega", throttled=True)

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
    datastore = param.ClassSelector(class_=DataStore)

    title = param.String()

    views = param.List()

    def __init__(self, **params):
        super().__init__(**params)
        updating = self.datastore.filtered.rx.updating()
        updating.rx.watch(
            lambda updating: pn.state.curdoc.hold()
            if updating
            else pn.state.curdoc.unhold()
        )
        _views = [view(datastore=self.datastore) for view in self.views]
        self._views = pn.FlexBox(
            *(v for v in _views),
            loading=updating,
        )
        self.unit = _views[2].param.unit

    #     self._template = pn.template.MaterialTemplate(title=self.title)
    #     self._template.sidebar.append(self.datastore)
    #     self._template.main.append(self._views)

    # def servable(self):
    #     if pn.state.served:
    #         return self._template.servable()
    #     return self

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
                        self._views[0],
                        pn.Row(*[self._views[2], self._views[1]]),
                    ),
                    pn.Row(*self._views[3:]),
                ]
            ),
            sidebar=[self.datastore, self.unit],
            raw_css=[RAW_CSS],
            **DEFAULT_PARAMS,
        )

    # @param.depends("views")
    # def __panel__(self):
    #     return pn.Column(
    #         *[
    #             pn.Row(self.datastore, *self._views[0:2]),
    #             pn.Row(*self._views[2]),
    #             pn.Row(*self._views[3:]),
    #         ],
    #     )
