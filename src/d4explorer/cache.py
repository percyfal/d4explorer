import os
from pathlib import Path

import diskcache

CACHEDIR = "cache"

# Main cache instance
cache = diskcache.Cache(CACHEDIR)


def cache_key(path: Path, max_bins: int) -> str:
    if not isinstance("path", Path):
        path = Path(path)
    size = path.stat().st_size
    absname = os.path.normpath(str(path.absolute()))
    return f"d4explorer:{absname}:{size}:{max_bins}"
