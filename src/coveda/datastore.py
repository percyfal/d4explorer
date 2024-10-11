import daiquiri
import numpy as np
import pandas as pd
import panel as pn
import param
from panel.viewable import Viewer
from pyd4 import D4File

logger = daiquiri.getLogger("coveda")

CARD_STYLE = """
:host {{
  box-shadow: rgba(50, 50, 93, 0.25) 0px 6px 12px -2px, rgba(0, 0, 0, 0.3) 0px 3px 7px -3px;
  padding: {padding};
}} """  # noqa

GFF3_COLUMNS = [
    "seqid",
    "source",
    "type",
    "start",
    "end",
    "score",
    "strand",
    "phase",
    "attributes",
]


def make_vector(df, sample_size):
    """Make vector from dataframe."""
    n = np.sum(df["counts"])
    return np.random.choice(
        df["x"].rx.value,
        size=min(int(sample_size), n.rx.value),
        p=df["counts"].rx.value / n.rx.value,
    )


def make_regions(path, annotation=None):
    d4 = D4File(path)
    retval = {"genome": d4.chroms()}
    if annotation is None:
        return d4, retval
    # Assume gff3 for now
    logger.info("Reading annotation")
    df_annot = pd.read_table(
        annotation, names=GFF3_COLUMNS, comment="#", header=None, sep="\t"
    )
    for ft, reg in df_annot.groupby("type"):
        retval[ft] = list(
            reg[["seqid", "start", "end"]].itertuples(index=False, name=None)
        )
    logger.info("Made annotation regions")
    return d4, retval


@pn.cache(ttl=60 * 60 * 24, to_disk=True)
def preprocess(path, annotation=None, max_bins=1_000):
    d4, regions = make_regions(path, annotation)
    dflist = []
    genome_size = sum([x[1] for x in d4.chroms()])
    for ft, reg in regions.items():
        logger.info("Processing %s", ft)
        histl = d4.histogram(reg, 0, max_bins)
        prefix_sums = sum(np.array(h.prefix_sum) for h in histl)
        counts = np.diff(prefix_sums)
        n = len(counts)
        d = pd.DataFrame(
            {"path": path, "feature": ft, "x": np.arange(n), "counts": counts}
        )
        d["nbases"] = d["counts"] * d["x"]
        d["coverage"] = d["nbases"] / genome_size
        dflist.append(d)

    logger.info("Computing summary dataframe")
    df = pd.concat(dflist)
    logger.info("Computed summary dataframe")
    return df


class DataStore(Viewer):
    data = param.DataFrame()

    filters = param.List(constant=True)

    def __init__(self, **params):
        super().__init__(**params)
        dfx = self.param.data.rx()
        datax = self.param.data.rx()
        widgets = []
        for filt in self.filters:
            dtype = self.data.dtypes[filt]
            if dtype.kind == "i":
                widget = pn.widgets.RangeSlider(
                    name=filt,
                    start=dfx[filt].min(),
                    end=dfx[filt].max(),
                    value=(dfx[filt].min(), dfx[filt].max()),
                    step=1,
                )
                condition = dfx[filt].between(*widget.rx())
            else:
                options = dfx[filt].unique().tolist()
                widget = pn.widgets.MultiChoice(name=filt, options=options)
                condition = dfx[filt].isin(
                    widget.rx().rx.where(widget, options)
                )
                if filt == "feature":
                    datax = datax[condition]
            dfx = dfx[condition]
            widgets.append(widget)
        self.filtered = dfx
        self.count = dfx.rx.len()
        self.feature_data = datax
        self._widgets = widgets

    def __panel__(self):
        return pn.Column(
            "## Filters",
            *self._widgets,
            stylesheets=[CARD_STYLE.format(padding="5px 10px")],
            margin=10,
        )
