import holoviews as hv
import panel as pn
import param
from panel.viewable import Viewer

from .datastore import DataStore

hv.extension("bokeh")


class View(Viewer):
    datastore = param.ClassSelector(class_=DataStore)


class Histogram(View):
    def __panel__(self):
        df = self.datastore.filtered
        # p = df.hvplot.bar(x="x", y="count", by="feature")
        # return pn.FlexBox(p)

        return pn.widgets.Tabulator(df)
