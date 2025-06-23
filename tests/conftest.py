import os
from pathlib import Path

import pandas as pd
import panel as pn
import pytest
from pytest import fixture

dirname = Path(os.path.abspath(os.path.dirname(__file__)))

PORT = [6000]


def pytest_configure(config):
    pytest.dname = dirname


@fixture
def port():
    PORT[0] += 1
    return PORT[0]


@fixture(autouse=True)
def server_cleanup():
    """Cleanup server after test."""
    try:
        yield
    finally:
        pn.state.reset()


@pytest.fixture
def d4file():
    def _d4file(name):
        return pytest.dname / "data" / f"{name}.per-base.d4"

    return _d4file


@pytest.fixture(scope="session")
def gff():
    return pytest.dname / "data" / "annotation.gff.gz"


@pytest.fixture(scope="session")
def sum_d4():
    return pytest.dname / "data" / "sum.d4"


@pytest.fixture(scope="session")
def count_d4():
    return pytest.dname / "data" / "count.d4"


@pytest.fixture(scope="session")
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
                ("ID=chr1_G000001.rRNA.1;Parent=chr1_G000001;product=5S ribosomal RNA"),
                "ID=chr2_G000001;product=exon 1",
                "ID=chr2_G000001.exon.1;Parent=chr2_G000001;product=exon 1",
            ],
        }
    )


@pytest.fixture(scope="session")
def gff_df_path(gff_df, tmpdir_factory):
    p = tmpdir_factory.mktemp("annotation")
    outfile = p / "annotation.gff"
    gff_df.to_csv(str(outfile), index=False, header=None, sep="\t")
    return Path(outfile)
