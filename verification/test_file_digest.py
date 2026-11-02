#!/usr/bin/env python3
"""Regression checks for the in-process file digest cache (#460)."""
from __future__ import annotations

import hashlib
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import file_digest  # noqa: E402


def old_file(path: Path, data: bytes, age_seconds: int) -> None:
    """Write `data` with an explicit past mtime; distinct ages, since Windows clocks tick coarsely."""
    path.write_bytes(data)
    past = time.time_ns() - age_seconds * 1_000_000_000
    os.utime(path, ns=(past, past))


def main() -> int:
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "image.bin"
        old_file(path, b"first", 20)
        assert file_digest.sha256_hex(path) == hashlib.sha256(b"first").hexdigest()
        assert any(key[0] == str(path) for key in file_digest._CACHE), "an old file is cached"
        if os.name != "nt":  # POSIX ctime changes on every write; Windows ctime is creation time
            info = path.stat()
            path.write_bytes(b"other")  # same size; restore the old mtime to simulate a racy rewrite
            os.utime(path, ns=(info.st_atime_ns, info.st_mtime_ns))
            assert file_digest.sha256_hex(path) == hashlib.sha256(b"other").hexdigest(), \
                "a rewrite with the old mtime must not reuse the cached digest"
        old_file(path, b"third", 10)
        assert file_digest.sha256_hex(path) == hashlib.sha256(b"third").hexdigest()
        fresh = Path(folder) / "fresh.bin"
        fresh.write_bytes(b"fresh")
        file_digest._CACHE.clear()
        assert file_digest.sha256_hex(fresh) == hashlib.sha256(b"fresh").hexdigest()
        assert not file_digest._CACHE, "a file modified in the last two seconds is never cached"
    print("file digest cache passed: content-equal digests, rewrite and racy guards")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
