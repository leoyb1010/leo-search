"""Publish a complete UTF-8 report without truncating an earlier result on failure."""
import os
from pathlib import Path
import tempfile


def write_report(path: Path, rendered: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise OSError('report destination must not be a symbolic link')
    temporary = None
    try:
        fd, temporary = tempfile.mkstemp(prefix='.' + path.name + '.', suffix='.tmp', dir=path.parent)
        with os.fdopen(fd, 'w', encoding='utf-8') as handle:
            handle.write(rendered)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and os.path.exists(temporary):
            os.unlink(temporary)
