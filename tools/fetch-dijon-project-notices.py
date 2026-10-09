#!/usr/bin/env python3
"""Bounded exact-ID fetch of the Dijon Maison des Associations relaunch award notices.

Three BOAMP award notices, discovered by the earlier frozen project search, are
requested by exact idweb only. Default prints the plan; --fetch performs it once.
Responses stay private; nothing here edits data.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import urllib.parse

ROOT = Path(__file__).resolve().parents[1]
CACHE = Path.home() / '.cache/contract-signals/decp-conflict-dijon'
BOAMP = 'https://www.boamp.fr/api/explore/v2.1/catalog/datasets/boamp/records'
NOTICES = ('24-73828', '24-77579', '24-78296')

spec = importlib.util.spec_from_file_location('decp_conflict_fetch', ROOT / 'tools/fetch-decp-conflict-evidence.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)


def requests():
    return [{'label': 'boamp-' + n, 'url': BOAMP + '?' + urllib.parse.urlencode({'where': f'idweb="{n}"', 'limit': 2})}
            for n in NOTICES]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fetch', action='store_true')
    parser.add_argument('--output-dir', type=Path, default=CACHE / 'project-notices-20261008')
    args = parser.parse_args()
    if args.fetch:
        base.requests = requests  # same frozen policy: caps, spacing, no redirects/retries, exclusive plan
        base.fetch(args.output_dir.resolve())
    else:
        print(json.dumps(requests(), indent=2))


if __name__ == '__main__':
    main()
