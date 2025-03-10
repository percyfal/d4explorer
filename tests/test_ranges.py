from pathlib import Path

import pandas as pd
import pytest

from d4explorer.model.ranges import GFF3, Bed, Ranges


@pytest.fixture
def data():
    return pd.DataFrame(
        {
            "seqid": ["chr1", "chr1", "chr2", "chr2"],
            "start": [10, 10, 20, 20],
            "end": [100, 100, 60, 60],
            "name": ["gene", "rRNA", "gene", "exon"],
            "score": [1, 10, 0, 3],
            "strand": ["+", "+", "-", "-"],
        }
    )


@pytest.fixture
def path(tmpdir_factory, data):
    p = tmpdir_factory.mktemp("data").join("data.bed")
    data.to_csv(p, sep="\t", index=False, header=None)
    return Path(p)


def test_ranges(data):
    rg = Ranges(data=data[["seqid", "start", "end"]])
    assert rg.width == 260


def test_bed(data, path):
    bed1 = Bed(data=data)
    bed2 = Bed(data=path)
    assert bed1.data.equals(bed2.data)
    assert bed1.bedtype == bed2.bedtype
    assert bed1.path != bed2.path
    assert bed1.width == 260
    assert bed2.width == 260


def test_gff3(gff_df, gff_df_path):
    gff1 = GFF3(data=gff_df)
    gff2 = GFF3(data=gff_df_path)
    assert gff1.data.equals(gff2.data)
    assert gff1.width == 260
    assert gff2.width == 260
    assert gff1.shape == (4, 9)
    assert gff2.shape == (4, 9)
    exon = gff1["exon"]
    assert exon.name == "exon"
    assert exon.shape == (1, 9)
    assert exon.width == 40
    gene = gff2["gene"]
    assert gene.shape == (2, 9)
    assert gene.width == 130
    assert gene.name == "gene"
