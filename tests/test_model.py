import numpy as np
import pandas as pd
import param
import pytest
from panel.viewable import Viewer
from param.reactive import rx

from d4explorer.model import D4Hist, GFF3Annotation


@pytest.fixture
def hist():
    return pd.DataFrame(
        {
            "x": ["<0", "0", "1", "2", "3", ">3"],
            "counts": [0, 1, 2, 1, 0, 0],
        }
    )


@pytest.fixture
def gff_df():
    return pd.DataFrame(
        {
            "seqid": ["chr1", "chr1", "chr2", "chr2"],
            "source": ["d4explorer"] * 4,
            "type": ["gene", "rRNA", "gene", "exon"],
            "start": [10, 10, 20, 20],
            "end": [100, 100, 60, 60],
            "score": ["."] * 4,
            "strand": ["+", "+", "-", "-"],
            "phase": ["."] * 4,
            "attributes": [
                "ID=chr1_G000001;product=5S ribosomal RNA",
                (
                    "ID=chr1_G000001.rRNA.1;Parent=chr1_G000001;"
                    "product=5S ribosomal RNA"
                ),
                "ID=chr2_G000001;product=exon 1",
                "ID=chr2_G000001.exon.1;Parent=chr2_G000001;product=exon 1",
            ],
        }
    )


def test_annotation(gff_df):
    gff = GFF3Annotation(gff_df)
    assert gff.shape == (4, 9)
    gff = gff["gene"]
    assert gff.shape == (2, 9)


def test_d4hist(hist):
    d4hist = D4Hist(hist)
    assert d4hist.data.shape == (6, 2)
    assert d4hist.data["x"].dtype == np.int64
    assert d4hist.max_bin == 3
    assert d4hist.max_nonzero_x == 2
    np.testing.assert_array_equal(d4hist.nbases.values, [0, 0, 2, 2, 0, 0])
    with pytest.raises(TypeError):
        d4hist.coverage
    d4hist.genome_size = 10
    np.testing.assert_array_equal(
        d4hist.coverage, [0.0, 0.0, 0.2, 0.2, 0.0, 0.0]
    )
    sample = d4hist.sample(n=5, random_seed=42)
    np.testing.assert_array_equal(sample, [1, 2, 1, 1, 0])


def test_d4hist_trimmed(hist):
    data = hist[(hist["x"] != "<0") & (hist["x"] != ">3")]
    d4hist = D4Hist(data)
    assert d4hist.data.shape == (4, 2)
    assert d4hist.data["x"].dtype == np.int64
    assert d4hist.max_bin == 2
    assert d4hist.max_nonzero_x == 2
    np.testing.assert_array_equal(d4hist.nbases.values, [0, 2, 2, 0])


class Parameters(Viewer):
    integer = param.Integer(default=1)


def test_rx_d4hist(hist):
    d4hist = D4Hist(hist)
    dfi = rx(d4hist)
    pmin = Parameters(integer=0)
    pmax = Parameters(integer=10)
    condition = dfi.data["x"].between(pmin.param.integer, pmax.param.integer)
    dfi = dfi[condition]
    assert dfi.rx.value.data.shape == (5, 2)
    pmax.integer = 2
    assert dfi.rx.value.data.shape == (3, 2)
