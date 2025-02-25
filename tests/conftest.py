import os

import panel as pn
from pytest import fixture

dirname = os.path.abspath(os.path.dirname(__file__))

PORT = [6000]


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
