import panel as pn
import param
from panel.viewable import Viewer

from .datastore import DataStore

pn.extension("vega", throttled=True)


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
        self._template = pn.template.MaterialTemplate(title=self.title)
        self._template.sidebar.append(self.datastore)
        self._template.main.append(self._views)

    def servable(self):
        if pn.state.served:
            return self._template.servable()
        return self

    @param.depends("views")
    def __panel__(self):
        return pn.Column(
            *[
                pn.Row(self.datastore, *self._views[0:2]),
                pn.Row(*self._views[2:]),
            ],
        )
