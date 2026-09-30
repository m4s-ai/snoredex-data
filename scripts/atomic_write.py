"""Replace a rendered store without truncating its retained contents."""

import os
import stat
import tempfile
from pathlib import Path


def atomic_write(path: Path, body: str | bytes) -> None:
    # ponytail: One file only; add a journal if multi-store crash consistency is required.
    content = body.encode("utf-8") if isinstance(body, str) else body
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False,
        ) as handle:
            temporary = handle.name
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        output_mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o644
        os.chmod(temporary, output_mode)
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary:
            if os.name == "nt" and Path(temporary).exists():
                os.chmod(temporary, 0o600)
            Path(temporary).unlink(missing_ok=True)
