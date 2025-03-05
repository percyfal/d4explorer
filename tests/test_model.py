from pathlib import Path

import numpy as np
import pandas as pd
import param
import pytest
from panel.viewable import Viewer
from param.reactive import rx

from d4explorer.model.d4 import (
    D4AnnotatedHist,
    D4Hist,
    Feature,
    GFF3Annotation,
)


@pytest.fixture
def hist():
    return pd.DataFrame(
        {
            "x": ["<0", "0", "1", "2", "3", ">3"],
            "counts": [0, 1, 2, 1, 0, 0],
        }
    )


@pytest.fixture
def gene_hist():
    return pd.DataFrame(
        {"x": ["<0", "0", "1", "2", "3", ">3"], "counts": [0, 1, 2, 1, 0, 0]}
    )


@pytest.fixture
def exon_hist():
    return pd.DataFrame(
        {"x": ["<0", "0", "1", "2", "3", ">3"], "counts": [0, 2, 3, 1, 0, 0]}
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


@pytest.fixture
def gff_df_path(gff_df, tmpdir_factory):
    p = tmpdir_factory.mktemp("annotation")
    outfile = p / "annotation.gff"
    gff_df.to_csv(str(outfile), index=False, header=None, sep="\t")
    return Path(outfile)


@pytest.fixture
def gff_df_overlap(gff_df):
    return pd.concat(
        [
            gff_df,
            pd.DataFrame(
                {
                    "seqid": ["chr2"],
                    "source": ["d4explorer"],
                    "type": ["gene"],
                    "start": [30],
                    "end": [90],
                    "score": ["."],
                    "strand": ["+"],
                    "phase": ["."],
                    "attributes": ["ID=chr2_G000002:product=exon 1"],
                }
            ),
        ]
    )


@pytest.fixture
def genome():
    return pd.DataFrame(
        {"seqid": ["chr1", "chr2"], "start": [0, 0], "end": [110, 120]}
    )


def test_annotation_path(gff):
    GFF3Annotation(gff)


def test_annotation(gff_df):
    gff = GFF3Annotation(gff_df)
    np.testing.assert_array_equal(gff.feature_types, ["gene", "rRNA", "exon"])
    assert gff.shape == (4, 9)
    gff = gff["gene"]
    assert gff.shape == (2, 9)


def test_annotation_features(gff_df):
    gff = GFF3Annotation(gff_df)
    exons = gff["exon"]
    exons_ft = Feature(exons)
    assert len(exons_ft) == 40
    assert len(Feature(gff["gene"])) == 130


def test_merge_annotation_features(gff_df_overlap):
    gff = GFF3Annotation(gff_df_overlap)
    gene = Feature(gff["gene"])
    gene.merge()
    assert len(gene) == 160


def test_d4hist(hist, genome):
    d4hist = D4Hist(hist, feature=Feature(genome, "genome"))
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


def test_d4hist_trimmed(hist, genome):
    data = hist[(hist["x"] != "<0") & (hist["x"] != ">3")]
    d4hist = D4Hist(data, feature=Feature(genome, "genome"))
    assert d4hist.data.shape == (4, 2)
    assert d4hist.data["x"].dtype == np.int64
    assert d4hist.max_bin == 2
    assert d4hist.max_nonzero_x == 2
    np.testing.assert_array_equal(d4hist.nbases.values, [1, 2, 2, 0])


class IParam(Viewer):
    integer = param.Integer(default=1)


def test_rx_d4hist(hist, genome):
    d4hist = D4Hist(hist, feature=Feature(genome, "genome"))
    dfi = rx(d4hist)
    pmin = IParam(integer=0)
    pmax = IParam(integer=10)
    condition = dfi.data["x"].between(pmin.param.integer, pmax.param.integer)
    dfi = dfi[condition]
    assert dfi.rx.value.data.shape == (5, 2)
    sample1 = dfi.rx.value.sample(n=20, random_seed=42)
    pmin.integer = 1
    pmax.integer = 3
    assert dfi.rx.value.data.shape == (3, 2)
    sample2 = dfi.rx.value.sample(n=20, random_seed=42)
    with pytest.raises(AssertionError):
        np.testing.assert_array_equal(sample1, sample2)


def test_d4hist_w_annotation(hist, gene_hist, exon_hist, gff_df, genome):
    gff = GFF3Annotation(gff_df)
    genome = Feature(genome, "genome")
    d4hist = D4Hist(hist, feature=genome, genome_size=len(genome))
    exon_hist = D4Hist(
        exon_hist, feature=Feature(gff["exon"]), genome_size=len(genome)
    )
    gene_hist = D4Hist(
        gene_hist, feature=Feature(gff["gene"]), genome_size=len(genome)
    )
    assert d4hist.feature_type == "genome"
    assert d4hist.feature.name == "genome"
    assert exon_hist.feature_type == "exon"
    assert exon_hist.feature.name == "exon"
    assert gene_hist.feature_type == "gene"
    assert gene_hist.feature.name == "gene"
    assert d4hist.data.shape == (6, 2)
    assert exon_hist.data.shape == (6, 2)
    assert gene_hist.data.shape == (6, 2)
    assert d4hist.max_bin == 3
    assert exon_hist.max_bin == 3
    assert gene_hist.max_bin == 3


def test_d4annotatedhist(hist, exon_hist, gff_df, gff_df_path, genome):
    gff = GFF3Annotation(gff_df)
    genome = Feature(genome, "genome")
    d4hist = D4Hist(hist, feature=genome, genome_size=len(genome))
    d4exon_hist = D4Hist(
        exon_hist, feature=Feature(gff["exon"]), genome_size=len(genome)
    )
    D4AnnotatedHist(
        data=[d4hist, d4exon_hist],
        annotation=gff_df_path,
        genome_size=len(genome),
    )
    with pytest.raises(AssertionError):
        D4AnnotatedHist(
            data=[hist, exon_hist], annotation=hist, genome_size="100"
        )


class LParam(Viewer):
    ls = param.List(["genome"], item_type=str)


def test_rx_d4annotatedhist(hist, exon_hist, gff_df, gff_df_path, genome):
    gff = GFF3Annotation(gff_df)
    genome = Feature(genome, "genome")
    d4hist = D4Hist(hist, feature=genome, genome_size=len(genome))
    d4exon_hist = D4Hist(
        exon_hist, feature=Feature(gff["exon"]), genome_size=len(genome)
    )
    ds = D4AnnotatedHist(
        data=[d4hist, d4exon_hist],
        annotation=gff_df_path,
        genome_size=len(genome),
    )
    dfi = rx(ds)
    assert len(dfi.rx.value.data) == 2
    assert dfi.rx.value.data[0].feature_type == "genome"
    assert dfi.rx.value.data[1].feature_type == "exon"
    for x in dfi.rx.value.data:
        assert x.shape == (6, 2)
    pmin = IParam(integer=0)
    pmax = IParam(integer=2)
    irange = dfi.between(pmin.param.integer, pmax.param.integer)
    dfi = dfi[irange]
    for x in dfi.rx.value.data:
        assert x.shape == (3, 2)
    assert dfi.rx.value.data[0].shape == (3, 2)
    assert dfi.rx.value.data[0].feature_type == "genome"
    assert dfi.rx.value.data[1].feature_type == "exon"
    features = LParam(ls=["exon"])
    dfi = dfi[features.param.ls]
    assert len(dfi.rx.value.data) == 1
    assert dfi.rx.value.data[0].feature_type == "exon"
    features = LParam(ls=["foo"])
    dfi = dfi[features.param.ls]
