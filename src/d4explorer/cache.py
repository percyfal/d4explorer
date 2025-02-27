import os
from dataclasses import dataclass, field
from pathlib import Path

import diskcache
import pandas as pd

CACHEDIR = "cache"

# Main cache instance
# FIXME: Target for deletion
cache = diskcache.Cache(CACHEDIR)


@dataclass
class CacheData:
    """Dataclass for storing cache data."""

    path: Path
    data: pd.DataFrame
    regions: dict[str] = field(default_factory=dict)
    max_bins: int = 1000

    def __post_init__(self):
        pass

    @classmethod
    def cache_key(cls, path: Path, max_bins: int) -> str:
        """Generate a cache key for a given path and max_bins."""
        size = path.stat().st_size
        absname = os.path.normpath(str(path.absolute()))
        return f"d4explorer:{absname}:{size}:{max_bins}"

    @property
    def key(self):
        return self.cache_key(self.path, self.max_bins)

    def regions_asdf(self):
        return pd.DataFrame(self.regions)


class D4ExplorerCache:
    """Main cache class for d4explorer."""

    def __init__(self, cachedir: str = CACHEDIR):
        self.diskcache = diskcache.Cache(cachedir)

    @property
    def keys(self):
        return [key for key in self.diskcache.iterkeys()]

    def has_key(self, key: str) -> bool:
        """Check if a key exists in the cache."""
        return key in self.diskcache

    def cache_key(self, path: Path, max_bins: int) -> str:
        """Generate a cache key for a given path and max_bins."""
        if not isinstance("path", Path):
            path = Path(path)
        size = path.stat().st_size
        absname = os.path.normpath(str(path.absolute()))
        return f"d4explorer:{absname}:{size}:{max_bins}"

    def get(self, key: str):
        """Get a value from the cache."""
        if not self.diskcache.get(key):
            return None
        return self.diskcache.get(key)

    def add(self, value: CacheData):
        """Add a value to the cache."""
        self.diskcache[value.key] = value

    @property
    def key(self):
        return self.diskcache.key


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
