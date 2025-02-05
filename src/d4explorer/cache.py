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


# def cache(func):
#     def wrapper(*args, **kwargs):
#         cache = diskcache.Cache(CACHEDIR)
#         key = (args, frozenset(kwargs.items()))
#         if key in cache:
#             return cache[key]
#         result = func(*args, **kwargs)
#         cache[key] = result
#         return result
#     return wrapper
