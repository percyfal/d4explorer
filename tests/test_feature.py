from pathlib import Path

import pandas as pd
import pytest

from d4explorer.model.feature import Feature
from d4explorer.model.ranges import GFF3, Bed


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


def test_bed_feature(data, path):
    ft1 = Feature(data=Bed(data=data))
    ft2 = Feature(data=path)
    assert ft1.data.equals(ft2.data)
    assert ft1.total == 260
    assert ft2.width == 260
    assert len(ft1) == 260


def test_gff_feature(gff_df, gff_df_path):
    ft1 = Feature(data=GFF3(data=gff_df))
    ft2 = Feature(data=gff_df_path)
    assert ft1.data.equals(ft2.data)
    assert ft1.total == 260
    assert ft2.width == 260
    assert len(ft1) == 260
    with pytest.raises(ValueError):
        # If data frame passed to feature, it is assumed to represent
        # bed format, not gff
        Feature(data=gff_df)


def test_feature_props(data):
    ft = Feature(data=Bed(data=data))
    assert ft.total == 260
