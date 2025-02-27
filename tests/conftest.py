import os
from pathlib import Path

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
