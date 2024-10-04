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
}} """

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


def make_regions(path, regions=None):
    d4 = D4File(path)
    retval = {"genome": d4.chroms()}
    if regions is None:
        return d4, retval
    # Assume gff3 for now
    df_annot = pd.read_table(
        regions, names=GFF3_COLUMNS, comment="#", header=None, sep="\t"
    )
    for ft, reg in df_annot.groupby("type"):
        retval[ft] = list(
            reg[["seqid", "start", "end"]].itertuples(index=False, name=None)
        )
    return d4, retval


@pn.cache(ttl=60 * 60 * 24)
def preprocess(path, max_bins=1_000):
    d4, regions = make_regions(path)
    dflist = []
    for ft, reg in regions.items():
        logger.info("Processing %s", ft)
        histl = d4.histogram(reg, 0, max_bins)
        prefix_sums = sum(np.array(h.prefix_sum) for h in histl)
        i = np.min(np.where(max(prefix_sums) == prefix_sums))
        prefix_sums[i:] = 0
        n = len(prefix_sums)
        d = pd.DataFrame(
            {"feature": ft, "x": np.arange(n), "count": prefix_sums}
        )
        dflist.append(d)

    logger.info("Computing summary dataframe")
    df = pd.concat(dflist)
    logger.info("Computed summary dataframe")
    return df


class DataStore(Viewer):
    data = param.DataFrame()

    def __init__(self, **params):
        super().__init__(**params)
        dfx = self.param.data.rx()
        widgets = []
        for filt in ["feature"]:
            dtype = self.data.dtypes[filt]
            options = dfx[filt].unique().tolist()
            widget = pn.widgets.MultiChoice(name=filt, options=options)
            condition = dfx[filt].isin(widget.rx().rx.where(widget, options))
            dfx = dfx[condition]
            widgets.append(widget)
        self.filtered = dfx
        self.count = dfx.rx.len()
        self._widgets = widgets

    def __panel__(self):
        return pn.Column(
            "## Filters",
            *self._widgets,
            stylesheets=[CARD_STYLE.format(padding="5px 10px")],
            margin=10,
        )
