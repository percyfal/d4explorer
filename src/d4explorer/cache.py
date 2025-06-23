import daiquiri
import diskcache

CACHEDIR = "cache"

# Main cache instance
# FIXME: Target for deletion
cache = diskcache.Cache(CACHEDIR)

logger = daiquiri.getLogger("d4explorer")


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

    def get(self, key: str):
        """Get a value from the cache."""
        if not self.diskcache.get(key):
            return None
        return self.diskcache.get(key)

    def add(self, *, value: tuple, key: str = None):
        """Add a value to the cache.

        The value is a tuple (metadata, data) where data can be None.
        """
        assert isinstance(value, tuple), "cache data must be tuple"
        assert isinstance(value[0], dict), (
            "first item in cache data tuple must be a metadata dictionary"
        )
        md = value[0]
        if key is None:
            key = md.key
        if key in self.diskcache:
            logger.info("Key already exists in cache: %s", key)
            return
        self.diskcache[key] = value

    @property
    def key(self):
        return self.diskcache.key
