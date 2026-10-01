#!/usr/bin/env python3
"""Link the canonical Leo Search skill into other local Agent skill roots."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import fcntl
import os
from pathlib import Path
import shutil
import sys
import tempfile


TARGETS = {
    "agents": Path.home() / ".agents" / "skills" / "leo-search",
    "claude": Path.home() / ".claude" / "skills" / "leo-search",
    "cursor": Path.home() / ".cursor" / "skills" / "leo-search",
}


def install_targets(names, source, force) -> int:
    """Serialize cooperating installers; stage links before preserving old data."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    backup_root = None
    conflicts = False
    for name in names:
        target = TARGETS[name]
        if target.is_symlink() and target.resolve() == source:
            print(f"{name}: already linked")
            continue
        if (target.exists() or target.is_symlink()) and not force:
            print(f"{name}: conflict, preserved; use --force to replace")
            conflicts = True
            continue
        backup = None
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix='.leo-search-link-', dir=target.parent) as staged:
                link = Path(staged) / 'leo-search'
                link.symlink_to(source, target_is_directory=True)
                if target.exists() or target.is_symlink():
                    if backup_root is None:
                        parent = Path.home() / '.leo-search-backups'
                        parent.mkdir(parents=True, exist_ok=True)
                        backup_root = Path(tempfile.mkdtemp(prefix=timestamp + '-', dir=parent))
                    backup = backup_root / name / 'leo-search'
                    backup.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(target), str(backup))
                try:
                    os.replace(link, target)
                except OSError:
                    if backup is not None and not (target.exists() or target.is_symlink()):
                        shutil.move(str(backup), str(target))
                    raise
            print(f"{name}: linked to {source}")
        except OSError:
            print(f"{name}: installation failed; existing data was not deleted", file=sys.stderr)
            if backup is not None and (backup.exists() or backup.is_symlink()):
                print(f"{name}: original preserved at {backup}", file=sys.stderr)
            conflicts = True
    return 1 if conflicts else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--targets", default="agents,claude,cursor")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    names = list(dict.fromkeys(name.strip() for name in args.targets.split(",") if name.strip()))
    unknown = [name for name in names if name not in TARGETS]
    if unknown:
        print(f"Unknown targets: {', '.join(unknown)}", file=sys.stderr)
        return 2
    if not names:
        parser.error("--targets must name at least one target")

    source = Path(__file__).resolve().parents[1] / "skills" / "leo-search"
    try:
        with (Path.home() / '.leo-search-install.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            return install_targets(names, source, args.force)
    except OSError:
        print('Could not lock installation; no target was changed', file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
