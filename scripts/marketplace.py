#!/usr/bin/env python3
"""Preserve unrelated personal marketplace entries during a Leo Search install."""
from __future__ import annotations
import fcntl
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

ENTRY = {
    "name": "leo-search",
    "source": {"source": "local", "path": "./plugins/leo-search"},
    "policy": {"installation": "AVAILABLE", "authentication": "ON_USE"},
    "category": "Productivity",
}


def update_marketplace(path: Path) -> str:
    path = path.expanduser().absolute()
    path.parent.mkdir(parents=True, exist_ok=True)
    # Advisory serialization covers cooperating Leo installers; other editors
    # must not be claimed transactional participants in this local lock.
    with path.with_name(path.name + '.leo-search.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        current = path.read_text(encoding='utf-8') if path.exists() else ''
        data = json.loads(current) if current else {'name': 'personal', 'interface': {'displayName': 'Personal'}, 'plugins': []}
        if not isinstance(data, dict):
            raise ValueError('marketplace must be a JSON object')
        name = data.setdefault('name', 'personal')
        if not isinstance(name, str) or not name.strip():
            raise ValueError('marketplace name must be a nonempty string')
        data.setdefault('interface', {'displayName': 'Personal'})
        plugins = data.setdefault('plugins', [])
        if not isinstance(plugins, list) or any(not isinstance(p, dict) or not isinstance(p.get('name'), str) for p in plugins):
            raise ValueError('marketplace plugins must be named objects')
        # Replace the one plugin without dropping/reordering unrelated entries;
        # remove duplicate Leo registrations that make installation ambiguous.
        updated, inserted = [], False
        for plugin in plugins:
            if plugin['name'] == 'leo-search':
                if not inserted:
                    updated.append(ENTRY.copy())
                    inserted = True
            else:
                updated.append(plugin)
        if not inserted:
            updated.append(ENTRY.copy())
        data['plugins'] = updated
        rendered = json.dumps(data, ensure_ascii=False, indent=2) + '\n'
        if rendered == current:
            print(f'Marketplace already current: {path}')
            return name
        temporary = None
        try:
            if path.exists():
                # Exclusive allocation, not second-resolution names: every
                # interrupted/repeated install retains its exact prior state.
                fd, backup = tempfile.mkstemp(prefix=path.name + '.bak.', dir=path.parent)
                os.close(fd)
                shutil.copy2(path, backup)
                print(f'Marketplace backup: {backup}')
            fd, temporary = tempfile.mkstemp(prefix='marketplace.', suffix='.json', dir=path.parent)
            with os.fdopen(fd, 'w', encoding='utf-8') as handle:
                handle.write(rendered)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            if temporary is not None and os.path.exists(temporary):
                os.unlink(temporary)
        print(f'Marketplace updated: {path}')
        return name


def main() -> int:
    if len(sys.argv) != 2:
        print('usage: marketplace.py <marketplace.json>', file=sys.stderr)
        return 2
    try:
        print(update_marketplace(Path(sys.argv[1])))
        return 0
    except (OSError, ValueError):
        # Do not print malformed JSON or paths from a provider/user payload.
        print('Marketplace update failed; original data and any backup were preserved.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
