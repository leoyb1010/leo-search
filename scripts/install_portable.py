#!/usr/bin/env python3
"""Link the canonical Leo Search skill into other local Agent skill roots."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import shutil
import sys


TARGETS = {
    "agents": Path.home() / ".agents" / "skills" / "leo-search",
    "claude": Path.home() / ".claude" / "skills" / "leo-search",
    "cursor": Path.home() / ".cursor" / "skills" / "leo-search",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--targets", default="agents,claude,cursor")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    names = [name.strip() for name in args.targets.split(",") if name.strip()]
    unknown = [name for name in names if name not in TARGETS]
    if unknown:
        print(f"Unknown targets: {', '.join(unknown)}", file=sys.stderr)
        return 2

    source = Path(__file__).resolve().parents[1] / "skills" / "leo-search"
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    backup_root = Path.home() / ".leo-search-backups" / timestamp
    for name in names:
        target = TARGETS[name]
        if target.is_symlink() and target.resolve() == source:
            print(f"{name}: already linked")
            continue
        if target.exists() or target.is_symlink():
            if not args.force:
                print(f"{name}: conflict, preserved; use --force to replace")
                continue
            backup = backup_root / name / "leo-search"
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(target), str(backup))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.symlink_to(source, target_is_directory=True)
        print(f"{name}: linked to {source}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
