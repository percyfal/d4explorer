import hvplot.pandas  # noqa
import holoviews as hv
import numpy as np
import panel as pn
import param
import pandas as pd
import random
from panel.viewable import Viewer
from bokeh.models import CustomJSHover

from .datastore import DataStore

hv.extension("bokeh")
pn.extension("tabulator")


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
    min_height = param.Integer(default=400)
    min_width = param.Integer(default=600)

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
            min_width=self.min_width,
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
            legend=None,
        )
        return pn.Column(
            pn.pane.Markdown("## Coverage histogram"), pn.FlexBox(p)
        )


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
        p = pn.widgets.Tabulator(
            data,
            pagination="remote",
            page_size=20,
            margin=10,
            layout="fit_data_table",
            # sizing_mode="stretch_both",
        )
        return pn.Column(pn.pane.Markdown("## Summary statistics table"), p)


class Indicators(View):
    def __panel__(self):
        df = self.datastore.filtered
        data = self.datastore.feature_data

        gdata = self.datastore.data
        gdata = gdata[gdata["feature"] == "genome"]
        gdata = gdata[gdata["x"] > 0]
        x = random.choices(
            gdata["x"].values, weights=gdata["counts"].values, k=10_000
        )

        return pn.Column(
            pn.FlexBox(
                pn.indicators.Number(
                    value=np.sum(df.counts),
                    name="Selected feature size",
                    format="{value:,}",
                    font_size="20pt",
                ),
                pn.indicators.Number(
                    value=np.sum(data.counts),
                    name="Total feature size",
                    format="{value:,}",
                    font_size="20pt",
                ),
                pn.indicators.Number(
                    value=np.sum(df.counts) / np.sum(data.counts) * 100,
                    name="Selected feature size (%)",
                    format="{value:,.2f}",
                    font_size="20pt",
                ),
            ),
            pn.FlexBox(
                pn.indicators.Number(
                    value=np.mean(x),
                    name="Mean coverage",
                    format="{value:,.2f}",
                    font_size="20pt",
                ),
                pn.indicators.Number(
                    value=np.median(x),
                    name="Median coverage",
                    format="{value:,.2f}",
                    font_size="20pt",
                ),
                pn.indicators.Number(
                    value=np.std(x),
                    name="Std coverage",
                    format="{value:,.2f}",
                    font_size="20pt",
                ),
                pn.indicators.Number(
                    value=np.mean(x) * 0.8,
                    name="80% coverage",
                    format="{value:,.2f}",
                    font_size="20pt",
                ),
                pn.indicators.Number(
                    value=np.median(x) + np.std(x),
                    name="median + 1sd",
                    format="{value:,.2f}",
                    font_size="20pt",
                ),
                pn.indicators.Number(
                    value=np.median(x) + 2 * np.std(x),
                    name="median + 2sd",
                    format="{value:,.2f}",
                    font_size="20pt",
                ),
                pn.widgets.TooltipIcon(
                    value=(
                        "The coverage ranges are computed from a "
                        "random sample of 10,000 bases from the "
                        "genome. The lower and upper suggested "
                        "thresholds are defined as in Lou 2021 "
                        "(10.1111/mec.16077)"
                    )
                ),
            ),
        )
