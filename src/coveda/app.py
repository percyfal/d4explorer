import panel as pn
import param
from panel.viewable import Viewer

from .datastore import DataStore
from .views import Histogram

pn.extension("vega", throttled=True)


class App(Viewer):
    datastore = param.ClassSelector(class_=DataStore)

    title = param.String()

    # views = param.List()

    def __init__(self, **params):
        super().__init__(**params)
        self.views = [Histogram]
        updating = self.datastore.filtered.rx.updating()
        updating.rx.watch(
            lambda updating: pn.state.curdoc.hold()
            if updating
            else pn.state.curdoc.unhold()
        )
        self._views = pn.FlexBox(
            *(view(datastore=self.datastore) for view in self.views),
            loading=updating,
        )
        self._template = pn.template.MaterialTemplate(title=self.title)
        self._template.sidebar.append(self.datastore)
        self._template.main.append(self._views)

    def servable(self):
        if pn.state.served:
            return self._template.servable()
        return self

    def __panel__(self):
        return pn.Row(self.datastore, self._views)
