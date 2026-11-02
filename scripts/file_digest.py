"""In-process SHA-256 cache for files that one process hashes repeatedly (images, #460).

A build or test that hashes the same unchanged image several times reads it once. The key carries
size, mtime, inode and ctime, so a rewritten file is hashed again; a file modified within the last
two seconds is never cached (the racy-clean guard Git uses for its index).
"""
from __future__ import annotations

import hashlib
import os
import time

_CACHE: dict[tuple, str] = {}
_RACY_NS = 2_000_000_000


def sha256_hex(path: os.PathLike | str) -> str:
    """Return the hex SHA-256 of a file's bytes."""
    info = os.stat(path)
    key = (os.fspath(path), info.st_size, info.st_mtime_ns, info.st_ino, info.st_ctime_ns)
    cached = _CACHE.get(key)
    if cached is not None:
        return cached
    with open(path, "rb") as handle:
        digest = hashlib.file_digest(handle, "sha256").hexdigest()
    if time.time_ns() - info.st_mtime_ns > _RACY_NS:
        _CACHE[key] = digest
    return digest
