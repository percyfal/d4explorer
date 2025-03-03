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

# from .datastore import DataStore, order_features
from d4explorer.model import D4AnnotatedHist


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


# def make_vector(df, sample_size):
#     """Make vector from dataframe."""
#     n = np.sum(df["counts"])
#     if int(sample_size) > n.rx.value:
#         feat = df["feature"].rx.value.unique()
#         logger.warning(
#             (
#                 "Sample size (n=%i) is larger than the data (n=%i); "
#                 "resampling values for feature %s"
#             ),
#             int(sample_size),
#             n.rx.value,
#             ",".join(feat),
#         )
#     try:
#         y = np.random.choice(
#             df["x"].rx.value,
#             size=int(sample_size),
#             p=df["counts"].rx.value / n.rx.value,
#         )
#     except ValueError:
#         logger.warning("Issue sampling data")
#         y = np.zeros(int(sample_size))
#     return y


def make_group_data(df, sample_size):
    pass


class View(Viewer):
    data = param.ClassSelector(class_=D4AnnotatedHist)
    fulldata = param.ClassSelector(class_=pd.DataFrame)


class D4HistogramView(View):
    unit = param.Selector(
        default="Mbp", doc="Unit of bins", objects=["bp", "Kbp", "Mbp", "Gbp"]
    )
    factors = {"bp": 1, "Kbp": 1e3, "Mbp": 1e6, "Gbp": 1e9}
    min_height = param.Integer(default=400)
    min_width = param.Integer(default=600)

    @pn.depends("unit")
    def __panel__(self):
        if len(self.data.data) == 0:
            return pn.Column(
                pn.pane.Markdown("# Coverage histogram"),
                pn.pane.Markdown("No data available"),
            )
        bases_formatter = CustomJSHover(
            code=f"""
            const num = (value/{self.factors[self.unit]}).toFixed(2);
            return num + ' {self.unit}';
            """
        )
        coverage_formatter = CustomJSHover(
            code="""
            return value.toFixed(2) + 'X';
            """
        )
        df = self.data.df()

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
            pn.pane.Markdown("# Coverage histogram"), pn.FlexBox(p)
        )


class D4BoxPlotView(View):
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


class D4ViolinPlotView(View):
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


# class FeatureTable(View):
#     columns = param.List(default=["feature", "size", "SI"])

#     def __panel__(self):
#         data = []
#         for ft, ft_data in self.datastore.regions.items():
#             data.append(
#                 {
#                     "feature": ft,
#                     "SI": ft_data.format(),
#                     "size": ft_data.total,
#                 }
#             )
#         df = pd.DataFrame(data)
#         df.set_index(["feature"], inplace=True)
#         p = pn.widgets.Tabulator(
#             df,
#             pagination="remote",
#             page_size=20,
#             margin=10,
#             layout="fit_data_table",
#         )
#         return pn.Column(pn.pane.Markdown("## Feature table"), p)


# class SummaryTable(View):
#     columns = param.List(
#         default=["feature", "x", "counts", "nbases", "coverage"]
#     )

#     def __panel__(self):
#         data = self.datastore.filtered.describe(
#             percentiles=np.arange(0, 1, 0.1)
#         )
#         p = pn.widgets.Tabulator(
#             data,
#             pagination="remote",
#             page_size=20,
#             margin=10,
#             layout="fit_data_table",
#         )
#         return pn.Column(pn.pane.Markdown("## Summary statistics table"), p)


class D4IndicatorView(View):
    def __panel__(self):
        tooltip = pn.widgets.TooltipIcon(
            value=(
                "The coverage ranges are computed from a "
                "random sample of 10,000 bases from the "
                "genome. The lower and upper suggested "
                "thresholds are defined as in Lou 2021 "
                "(10.1111/mec.16077)"
            )
        )
        if len(self.data.data) == 0:
            return pn.Column(
                pn.Row(pn.pane.Markdown("# Feature size indicators"), tooltip),
                pn.pane.Markdown("No data available"),
            )

        region_size = {x.feature.name: len(x.feature) for x in self.data.data}
        fsize_tab_list = []
        for k, v in region_size.items():
            df = self.data.df()
            fsize = v
            ssize = np.sum(
                df[df["feature"] == k].counts[df[df["feature"] == k].x > 0]
            )
            ssize_frac = np.round(ssize / fsize * 100.0, 2)

            # These should be fix!
            gdata = self.fulldata
            gdata = gdata[gdata["feature"] == k]
            gdata = gdata[gdata["x"] > 0]
            logger.info("sampling values...")
            x = np.random.choice(
                gdata["x"].values,
                p=gdata["counts"].values / np.sum(gdata["counts"].values),
                size=1_000_000,
            )
            mean_coverage = np.round(np.mean(x), 2)
            median_coverage = np.round(np.median(x), 2)
            std_coverage = np.round(np.std(x), 2)
            pct_60_coverage = np.round(mean_coverage * 0.6, 2)
            pct_70_coverage = np.round(mean_coverage * 0.7, 2)
            pct_80_coverage = np.round(mean_coverage * 0.8, 2)
            pct_90_coverage = np.round(mean_coverage * 0.9, 2)
            median_plus_1sd = np.round(median_coverage + std_coverage, 2)
            median_plus_2sd = np.round(median_coverage + 2 * std_coverage, 2)
            fsize_tab_list.append(
                {
                    "feature": k,
                    "size": fsize,
                    "selected": ssize,
                    "selected (%)": ssize_frac,
                    "Coverage: mean": mean_coverage,
                    "median": median_coverage,
                    "std": std_coverage,
                    "60%": pct_60_coverage,
                    "70%": pct_70_coverage,
                    "80%": pct_80_coverage,
                    "90%": pct_90_coverage,
                    "median+1sd": median_plus_1sd,
                    "median+2sd": median_plus_2sd,
                }
            )
        fsize_tab_df = pd.DataFrame(fsize_tab_list)
        fsize_tab_df.set_index(["feature"], inplace=True)

        stylesheet = """
        .tabulator-header {
        font-size: 20pt;
        }
        .tabulator-cell {
        font-size: 16pt;
        }
        """

        fsize_tab_widget = pn.widgets.Tabulator(
            fsize_tab_df,
            pagination="remote",
            page_size=20,
            margin=10,
            layout="fit_data_table",
            stylesheets=[stylesheet],
        )

        return pn.Column(
            pn.Row(pn.pane.Markdown("# Feature size indicators"), tooltip),
            pn.FlexBox(fsize_tab_widget),
        )
