import pytest

from d4explorer import cache
from d4explorer.cache import D4ExplorerCache


@pytest.fixture(autouse=True)
def change_test_dir(tmpdir_factory, monkeypatch):
    d = tmpdir_factory.mktemp("cache")
    monkeypatch.chdir(d)


def test_d4explorer_cache(change_test_dir):
    d4cache = D4ExplorerCache()
    assert d4cache.diskcache.directory == cache.CACHEDIR
    d4cache = D4ExplorerCache("test")
    assert d4cache.diskcache.directory == "test"
