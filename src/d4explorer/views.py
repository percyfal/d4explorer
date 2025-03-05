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
from d4explorer.model.d4 import D4AnnotatedHist


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


class View(Viewer):
    data = param.ClassSelector(class_=D4AnnotatedHist)
    fulldata = param.ClassSelector(class_=pd.DataFrame)


class D4HistogramView(View):
    unit = param.Selector(
        default="Mbp", doc="Unit of bins", objects=["bp", "Kbp", "Mbp", "Gbp"]
    )
    factors = {"bp": 1, "Kbp": 1e3, "Mbp": 1e6, "Gbp": 1e9}
    min_height = param.Integer(default=400, doc="Minimum height of plot")
    min_width = param.Integer(default=400, doc="Minimum width of plot")

    @pn.depends(
        "unit",
        "min_height",
        "min_width",
    )
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
            pn.pane.Markdown("# Coverage histogram"),
            pn.FlexBox(
                pn.Column(
                    pn.Row(
                        self.param.unit,
                        self.param.min_height,
                        self.param.min_width,
                    ),
                    p,
                )
            ),
        )


class D4BoxPlotView(View):
    samplesize = param.Integer(
        default=10000,
        doc=(
            "Sample size for boxplot. Samples are drawn from the "
            "x (coverage) column, weighted by the counts column."
        ),
    )
    min_height = param.Integer(default=400, doc="Minimum height of plot")
    min_width = param.Integer(default=400, doc="Minimum width of plot")

    @pn.depends(
        "samplesize",
        "min_height",
        "min_width",
    )
    def __panel__(self):
        df = self.data.df()
        if len(df) == 0:
            return pn.Column(
                pn.pane.Markdown("# Boxplot"),
                pn.pane.Markdown("No data available"),
            )
        dflist = []
        for ft_data in self.data.data:
            df = pd.DataFrame(
                {
                    "feature": ft_data.feature.name,
                    "value": ft_data.sample(self.samplesize),
                }
            )
            dflist.append(df)
        data = pd.concat(dflist)
        by = ["feature"]
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
        return pn.FlexBox(
            pn.Column(
                pn.pane.Markdown("# Boxplot"),
                pn.Row(
                    self.param.samplesize,
                    self.param.min_height,
                    self.param.min_width,
                ),
                p,
            )
        )


class D4ViolinPlotView(View):
    samplesize = param.Integer(
        default=10000,
        doc=(
            "Sample size for violin plot. Samples are drawn from the "
            "x (coverage) column, weighted by the counts column."
        ),
    )
    min_height = param.Integer(default=400)
    min_width = param.Integer(default=600)

    @pn.depends(
        "samplesize",
        "min_height",
        "min_width",
    )
    def __panel__(self):
        df = self.data.df()
        if len(df) == 0:
            return pn.Column(
                pn.pane.Markdown("# Violin plot"),
                pn.pane.Markdown("No data available"),
            )
        dflist = []
        for ft_data in self.data.data:
            df = pd.DataFrame(
                {
                    "feature": ft_data.feature.name,
                    "value": ft_data.sample(self.samplesize),
                }
            )
            dflist.append(df)
        data = pd.concat(dflist)
        by = ["feature"]
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
        return pn.FlexBox(
            pn.Column(
                pn.pane.Markdown("## Violin plot"),
                pn.Row(
                    self.param.samplesize,
                    self.param.min_height,
                    self.param.min_width,
                ),
                p,
            )
        )


class D4IndicatorView(View):
    def __panel__(self):
        tooltip = pn.widgets.TooltipIcon(
            value=(
                "The coverage ranges are computed from a "
                "random sample of 1,000,000 bases from each "
                "feature. The lower and upper suggested "
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
            fix_data = self.fulldata.loc[k]
            fsize_tab_list.append(
                {
                    "feature": k,
                    "size": fsize,
                    "selected": ssize,
                    "selected (%)": ssize_frac,
                    "Coverage: mean": fix_data.mean_coverage,
                    "median": fix_data.median_coverage,
                    "std": fix_data.std_coverage,
                    "60%": fix_data.pct_60_coverage,
                    "70%": fix_data.pct_70_coverage,
                    "80%": fix_data.pct_80_coverage,
                    "90%": fix_data.pct_90_coverage,
                    "median+1sd": fix_data.median_plus_1sd,
                    "median+2sd": fix_data.median_plus_2sd,
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
