import hvplot.pandas  # noqa
import holoviews as hv
import numpy as np
import panel as pn
import param
import pandas as pd
from panel.viewable import Viewer
from bokeh.models import CustomJSHover

from .datastore import DataStore

hv.extension("bokeh")


def make_vector(df, sample_size):
    """Make vector from dataframe."""
    n = np.sum(df["counts"])
    return np.random.choice(
        df["x"].rx.value,
        size=min(int(sample_size), n.rx.value),
        p=df["counts"].rx.value / n.rx.value,
    )


class View(Viewer):
    datastore = param.ClassSelector(class_=DataStore)
    min_height = param.Integer(default=400)
    min_width = param.Integer(default=400)


class Histogram(View):
    unit = param.Selector(
        default="Mbp", doc="Unit of bins", objects=["bp", "Kbp", "Mbp", "Gbp"]
    )
    factors = {"bp": 1, "Kbp": 1e3, "Mbp": 1e6, "Gbp": 1e9}

    @param.depends("unit")
    def __panel__(self):
        bases_formatter = CustomJSHover(
            code=f"""
        return (value / {self.factors[self.unit]}).toFixed(2) + ' {self.unit}';
        """
        )
        coverage_formatter = CustomJSHover(
            code="""
        return value.toFixed(2) + 'X';
        """
        )
        df = self.datastore.filtered
        p = df.hvplot.bar(
            x="x",
            y="counts",
            by="feature",
            fill_alpha=0.5,
            min_height=self.min_height,
            min_width=self.min_height,
            title="Coverage Histogram",
            xticks=None,
            xaxis=None,
            xlabel="coverage",
            hover_cols=["nbases", "coverage"],
            hover_tooltips=[
                ("Feature", "@feature"),
                ("NBases", "@nbases{custom}"),
                ("Coverage", "@coverage{custom}"),
                ("Counts", "@counts"),
                ("X", "@x"),
            ],
            hover_formatters={
                "@{nbases}": bases_formatter,
                "@{coverage}": coverage_formatter,
            },
            responsive=True,
            rot=45,
        ).opts(legend_position="right")
        return pn.FlexBox(self.param.unit, p)


class BoxPlot(View):
    samplesize = param.Integer(
        default=10000,
        doc=(
            "Sample size for boxplot. Samples are drawn from the "
            "x (coverage) column, weighted by the counts column."
        ),
    )

    @param.depends("samplesize")
    def __panel__(self):
        df = self.datastore.filtered
        data = {}
        for group, group_data in df.groupby("feature"):
            sample = make_vector(group_data, self.samplesize)
            data[group.rx.value] = sample
        data_df = pd.DataFrame(data)
        columns = data_df.columns.tolist()
        data = data_df.melt(value_vars=columns, var_name="feature")
        p = data.hvplot.box(
            y="value",
            by="feature",
            min_height=self.min_height,
            title="Subsampled coverage distribution",
            min_width=self.min_width,
            responsive=True,
            rot=45,
            color="feature",
        ).opts(legend_position="right")
        return pn.FlexBox(self.param.samplesize, p)


class ViolinPlot(View):
    samplesize = param.Integer(
        default=10000,
        doc=(
            "Sample size for violin plot. Samples are drawn from the "
            "x (coverage) column, weighted by the counts column."
        ),
    )

    @param.depends("samplesize")
    def __panel__(self):
        df = self.datastore.filtered
        data = {}
        for group, group_data in df.groupby("feature"):
            sample = make_vector(group_data, self.samplesize)
            data[group.rx.value] = sample
        data_df = pd.DataFrame(data)
        columns = data_df.columns.tolist()
        data = data_df.melt(value_vars=columns, var_name="feature")
        p = data.hvplot.violin(
            y="value",
            by="feature",
            min_height=self.min_height,
            min_width=self.min_width,
            title="Subsampled coverage distribution",
            responsive=True,
            rot=45,
            color="feature",
        ).opts(legend_position="right")
        return pn.FlexBox(self.param.samplesize, p)


class SummaryTable(View):
    columns = param.List(
        default=["feature", "x", "counts", "nbases", "coverage"]
    )

    def __panel__(self):
        data = self.datastore.filtered.describe(
            percentiles=np.arange(0, 1, 0.1)
        )
        return pn.widgets.Tabulator(
            data,
            pagination="remote",
            page_size=20,
            margin=10,
            sizing_mode="stretch_both",
        )


class Indicators(View):
    def __panel__(self):
        df = self.datastore.filtered
        data = self.datastore.feature_data
        return pn.FlexBox(
            pn.indicators.Number(
                value=np.sum(df.counts),
                name="Selected feature size",
                format="{value:,}",
            ),
            pn.indicators.Number(
                value=np.sum(data.counts),
                name="Total feature size",
                format="{value:,}",
            ),
            pn.indicators.Number(
                value=np.sum(df.counts) / np.sum(data.counts) * 100,
                name="Selected feature size (%)",
                format="{value:,.2f}",
            ),
        )
