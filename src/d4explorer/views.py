import hvplot.pandas  # noqa
import holoviews as hv
import numpy as np
import panel as pn
import param
import pandas as pd
import daiquiri
from panel.viewable import Viewer
from bokeh.models import CustomJSHover
from holoviews.plotting.util import process_cmap

from .datastore import DataStore, order_features


hv.extension("bokeh")
pn.extension("tabulator")


logger = daiquiri.getLogger("d4explorer")

CMAP_GLASBEY = {
    cm.name: cm
    for cm in hv.plotting.util.list_cmaps(
        records=True, category="Categorical", reverse=False
    )
    if cm.name.startswith("glasbey")
}
colormap = "glasbey_hv"
COLORS = process_cmap(
    CMAP_GLASBEY[colormap].name, provider=CMAP_GLASBEY[colormap].provider
)


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

    @pn.depends("unit")
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
            legend=False,
            color=COLORS,
        )
        return pn.Column(
            pn.pane.Markdown("## Coverage histogram"), pn.FlexBox(p)
        )


def make_group_data(df, samplesize):
    data = {}
    for group, group_data in df.groupby(["feature"]):
        sample = make_vector(group_data, samplesize)
        data[group.rx.value] = sample
    if len(group.rx.value) == 1:
        index = ["index"]
        id_vars = None
        data_df = pd.DataFrame(data)
    elif len(group.rx.value) == 2:
        index = ["index", "path"]
        id_vars = ["path"]
        data_df = pd.DataFrame(data).stack(future_stack=True)
    else:
        raise ValueError("Too many groups")
    columns = data_df.columns.tolist()
    data = data_df.reset_index(names=index).melt(
        value_vars=columns, var_name="feature", id_vars=id_vars
    )
    data["feature"] = data["feature"].astype("category")
    data["feature"] = data["feature"].cat.set_categories(
        order_features(data["feature"].cat.categories.values), ordered=True
    )
    if len(index) == 2:
        data["path"] = data["path"].astype("category")
        data = data.sort_values(["feature", "path"])
    else:
        data = data.sort_values(["feature"])
    return data


class BoxPlot(View):
    samplesize = param.Integer(
        default=10000,
        doc=(
            "Sample size for boxplot. Samples are drawn from the "
            "x (coverage) column, weighted by the counts column."
        ),
    )

    @pn.depends("samplesize")
    def __panel__(self):
        df = self.datastore.filtered
        data = make_group_data(df, self.samplesize)
        by = ["feature"] if len(data.columns) == 2 else ["path", "feature"]
        p = data.hvplot.box(
            y="value",
            by=by,
            min_height=self.min_height,
            title="Subsampled coverage distribution",
            min_width=self.min_width,
            responsive=True,
            rot=45,
            color="feature",
            cmap=COLORS,
            legend=False,
        )
        return pn.FlexBox(self.param.samplesize, p)


class ViolinPlot(View):
    samplesize = param.Integer(
        default=10000,
        doc=(
            "Sample size for violin plot. Samples are drawn from the "
            "x (coverage) column, weighted by the counts column."
        ),
    )

    @pn.depends("samplesize")
    def __panel__(self):
        df = self.datastore.filtered
        data = make_group_data(df, self.samplesize)
        by = ["feature"] if len(data.columns) == 2 else ["path", "feature"]

        p = data.hvplot.violin(
            y="value",
            by=by,
            min_height=self.min_height,
            min_width=self.min_width,
            title="Subsampled coverage distribution",
            responsive=True,
            rot=45,
            color="feature",
            cmap=COLORS,
            legend=False,
        )
        return pn.FlexBox(self.param.samplesize, p)


class FeatureTable(View):
    columns = param.List(default=["feature", "size", "SI"])

    def __panel__(self):
        data = []
        for ft, ft_data in self.datastore.regions.items():
            data.append(
                {
                    "feature": ft,
                    "SI": ft_data.format(),
                    "size": ft_data.total,
                }
            )
        df = pd.DataFrame(data)
        df.set_index(["feature"], inplace=True)
        p = pn.widgets.Tabulator(
            df,
            pagination="remote",
            page_size=20,
            margin=10,
            layout="fit_data_table",
        )
        return pn.Column(pn.pane.Markdown("## Feature table"), p)


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
        )
        return pn.Column(pn.pane.Markdown("## Summary statistics table"), p)


class Indicators(View):
    def __panel__(self):
        df = self.datastore.filtered
        data = self.datastore.feature_data

        gdata = self.datastore.data
        gdata = gdata[gdata["feature"] == "genome"]
        gdata = gdata[gdata["x"] > 0]
        logger.info("sampling values...")
        x = np.random.choice(
            gdata["x"].values,
            p=gdata["counts"].values / np.sum(gdata["counts"].values),
            size=1_000_000,
        )
        logger.info("done!")

        return pn.Column(
            pn.pane.Markdown("## Feature size indicators"),
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
            pn.pane.Markdown("## Genome-wide coverage indicators"),
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
                    value=np.mean(x) * 0.6,
                    name="60% coverage",
                    format="{value:,.2f}",
                    font_size="20pt",
                ),
                pn.indicators.Number(
                    value=np.mean(x) * 0.7,
                    name="70% coverage",
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
                    value=np.mean(x) * 0.9,
                    name="90% coverage",
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
