import os
from pathlib import Path

import diskcache

CACHEDIR = "cache"

# Main cache instance
cache = diskcache.Cache(CACHEDIR)


class D4ExplorerCache:
    """Main cache class for d4explorer."""

    def __init__(self):
        self.cache = diskcache.Cache(CACHEDIR)

    @property
    def keys(self):
        return [key for key in self.cache.iterkeys()]

    def cache_key(self, path: Path, max_bins: int) -> str:
        """Generate a cache key for a given path and max_bins."""
        if not isinstance("path", Path):
            path = Path(path)
        size = path.stat().st_size
        absname = os.path.normpath(str(path.absolute()))
        return f"d4explorer:{absname}:{size}:{max_bins}"

    def get(self, key: str):
        """Get a value from the cache."""
        if not self.cache.get(key):
            return None
        return self.cache.get(key)


def cache_key(path: Path, max_bins: int) -> str:
    """Generate a cache key for a given path and max_bins."""
    if not isinstance("path", Path):
        path = Path(path)
    size = path.stat().st_size
    absname = os.path.normpath(str(path.absolute()))
    return f"d4explorer:{absname}:{size}:{max_bins}"


def get_keys():
    """Get all cache keys."""
    return [key for key in cache.iterkeys()]
