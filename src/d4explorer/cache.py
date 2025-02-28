import diskcache

CACHEDIR = "cache"

# Main cache instance
# FIXME: Target for deletion
cache = diskcache.Cache(CACHEDIR)


# @dataclass
# class CacheData:
#     """Dataclass for storing cache data."""
#     data: model.D4AnnotatedHist # Add more types here

#     def __post_init__(self):
#         pass

#     @property
#     def key(self):
#         return self.data.key


class D4ExplorerCache:
    """Main cache interface class for d4explorer."""

    def __init__(self, cachedir: str = CACHEDIR):
        self.diskcache = diskcache.Cache(cachedir)

    @property
    def keys(self):
        return [key for key in self.diskcache.iterkeys()]

    def has_key(self, key: str) -> bool:
        """Check if a key exists in the cache."""
        return key in self.diskcache

    def get(self, key: str):  # -> CacheData:
        """Get a value from the cache."""
        if not self.diskcache.get(key):
            return None
        return self.diskcache.get(key)

    def add(self, value):  # CacheData):
        """Add a value to the cache."""
        self.diskcache[value.key] = value

    @property
    def key(self):
        return self.diskcache.key
