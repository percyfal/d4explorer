from pathlib import Path

import pandas as pd
import pytest

from d4explorer.datastore import DataStore, make_regions, preprocess
from d4explorer.model.d4 import D4AnnotatedHist, D4Hist
from d4explorer.model.feature import Feature


@pytest.fixture(scope="module")
def datastore(tmpdir_factory):
    p = Path(tmpdir_factory.mktemp("cache"))
    ds = DataStore(cachedir=p)
    assert ds.data is None
    return ds


@pytest.fixture(scope="module")
def count_data(count_d4, gff):
    return preprocess(count_d4, annotation=gff)


@pytest.fixture(scope="module")
def sum_data(sum_d4, gff):
    return preprocess(sum_d4, annotation=gff)


@pytest.fixture
def genome():
    n = 1_000_000
    return Feature(
        pd.DataFrame(
            {
                "seqid": ["chr1", "chr2", "chr3"],
                "start": [0, 0, 0],
                "end": [n, n, n],
            }
        ),
        "genome",
    )


def test_make_regions(d4file, gff, genome):
    s1 = d4file("s1")
    d4, regions = make_regions(str(s1))
    assert d4 is not None
    assert isinstance(regions["genome"], Feature)
    assert regions["genome"].data.shape == (3, 3)

    d4, regions = make_regions(str(s1), annotation=gff)
    assert d4 is not None
    for ft, reg in regions.items():
        assert isinstance(reg, Feature)


def test_preprocess(d4file):
    s1 = d4file("s1")
    ds = preprocess(str(s1))
    assert isinstance(ds, D4AnnotatedHist)
    assert isinstance(ds.data[0], D4Hist)
    assert ds.data[0].feature_type == "genome"
    assert ds.data[0].feature.name == "genome"
    assert len(ds.data[0].feature) == 3_000_000
    assert ds.data[0].genome_size == 3_000_000


def test_preprocessannot(d4file, gff):
    s1 = d4file("s1")
    ds = preprocess(str(s1), annotation=gff)
    assert isinstance(ds, D4AnnotatedHist)
    assert len(ds.data) == 9
    for data in ds.data:
        assert isinstance(data, D4Hist)
        if data.feature_type != "genome":
            assert len(data.feature) != 3_000_000
        else:
            assert len(data.feature) == 3_000_000


def test_datastore_cache(datastore, sum_data):
    keys = datastore.cache.keys
    cache_data, metadata = sum_data.to_cache()
    for d, md in cache_data:
        datastore.cache.add(value=(d, md), key=md.get("id"))
    datastore.cache.add(value=metadata, key=metadata.get("id"))
    keys = datastore.cache.keys
    d4ah = D4AnnotatedHist.load(keys[0], datastore.cache)
    assert isinstance(d4ah, D4AnnotatedHist)
    assert len(d4ah.data) == 9
    for data in d4ah.data:
        assert isinstance(data, D4Hist)
        if data.feature_type != "genome":
            assert len(data.feature) != 3_000_000
        else:
            assert len(data.feature) == 3_000_000
            assert data.genome_size == 3_000_000
