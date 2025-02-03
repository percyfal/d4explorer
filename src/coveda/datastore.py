import os
import subprocess as sp
from tempfile import mkdtemp

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


def d4hist(path, regions, max_bins):
    """Compute histogram from d4. Call d4tools as the pyd4 interface
    is not working properly."""
    try:
        temp_dir = mkdtemp()
        temp_file = os.path.join(temp_dir, "regions.bed")
        logger.info("Writing regions to %s", temp_file)
        with open(temp_file, "w") as f:
            for r in regions:
                f.write(f"{r[0]}\t{r[1]}\t{r[2]}\n")
            res = sp.run(
                [
                    "d4tools",
                    "stat",
                    "-s",
                    "hist",
                    "-r",
                    temp_file,
                    "--max-bin",
                    str(max_bins),
                    path,
                ],
                capture_output=True,
            )
    except sp.CalledProcessError as e:
        logger.error(e)
    data = pd.DataFrame(
        [x.split() for x in res.stdout.decode("utf-8").split("\n") if x],
        columns=["x", "counts"],
    )
    data.drop([0, data.shape[0] - 1], inplace=True)
    data["x"] = data["x"].astype(int)
    data["counts"] = data["counts"].astype(int)
    return data


def make_vector(df, sample_size):
    """Make vector from dataframe."""
    n = np.sum(df["counts"])
    try:
        data = np.random.choice(
            df["x"].rx.value,
            size=min(int(sample_size), n.rx.value),
            p=df["counts"].rx.value / n.rx.value,
        )
    except ValueError:
        data = None
    return data


def make_regions(path, annotation=None):
    d4 = D4File(path)
    retval = {"genome": [(x[0], 0, x[1]) for x in d4.chroms()]}
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
    genome_size = np.sum(x[1] for x in d4.chroms())
    for ft, reg in regions.items():
        logger.info("Processing %s", ft)
        data = d4hist(path, reg, max_bins)
        d = pd.DataFrame(
            {
                "path": path,
                "feature": ft,
                "x": data["x"],
                "counts": data["counts"],
            }
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
