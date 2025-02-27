import pytest

from d4explorer import cache
from d4explorer.cache import D4ExplorerCache


@pytest.fixture(scope="module")
def cachedata():
    # data = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
    return cache.CacheData()


def test_d4explorer_cache():
    d4cache = D4ExplorerCache()
    assert d4cache.diskcache.directory == cache.CACHEDIR
    d4cache = D4ExplorerCache("test")
    assert d4cache.diskcache.directory == "test"
