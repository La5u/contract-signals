#!/usr/bin/env python3
"""Coverage index of the merged France DECP dataset (both cohort imports, one explorer dataset).

The explorer loads data/decp-history.json and data/decp-cities.json as one dataset. Each import
keeps its own coverage file with the exact queries; this index summarises both and the sources
they are reconciled with. Run after both DECP imports.
"""
from collections import Counter
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
PARTS = [('decp-history.json', 'decp-coverage.json', 'Ville de Paris and Département de l’Ardèche'),
         ('decp-cities.json', 'decp-cities-coverage.json', 'Rennes, Nantes, Bordeaux, Grenoble, Dijon and Tours (municipalities)')]


def main():
    rows, parts = [], []
    for data, coverage, buyers in PARTS:
        records = json.loads((DATA / data).read_text())
        cov = json.loads((DATA / coverage).read_text())
        rows += records
        parts.append({'file': f'data/{data}', 'coverage': f'data/{coverage}', 'buyers': buyers, 'records': len(records),
                      'feedReconciliation': (cov.get('feedReconciliation') or {}).get('statistics')})
    status = Counter((r.get('verification') or {}).get('status') for r in rows)
    index = {
        'title': 'France — DECP contracts of eight buyers, notified 2024–2025',
        'parts': parts,
        'counts': {'records': len(rows), 'buyers': len({r['buyerSiret'] for r in rows}),
                   'verification': dict(sorted(status.items())),
                   'addedFromFeedsOrLists': sum(bool((r.get('verification') or {}).get('addedFromFeed')) for r in rows),
                   'possibleDuplicates': sum(bool(r.get('possibleDuplicateOf')) for r in rows),
                   'initialConflicts': sum(bool(r.get('initialConflicts')) for r in rows)},
        'sources': ['Ministère de l’Économie, decp-2022-marches-valides (data/decp-history-raw.json.gz, data/decp-cities-raw.json)',
                    'Buyer publication feeds via the national consolidated DECP (data/decp-feeds-raw.json.gz)',
                    'Ville de Nantes and Bordeaux Métropole open-data contract lists (data/city-portals-raw.json.gz)'],
        'rules': 'research/france-cross-dataset-check.md; research/decp-identifier-collisions.md',
        'merge': 'Both imports produce disjoint buyers; the explorer concatenates them. Scores compare each buyer only with itself, so merging changes no score.',
    }
    (DATA / 'decp-france-coverage.json').write_text(json.dumps(index, ensure_ascii=False, indent=2) + '\n')
    print(f"{index['counts']['records']} records, {index['counts']['buyers']} buyers -> data/decp-france-coverage.json")


if __name__ == '__main__':
    main()
