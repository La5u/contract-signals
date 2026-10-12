#!/usr/bin/env python3
"""Hash-bound interpretation of the frozen amendment evidence; never rewrites it.

The evidence ledger records what was observed (an omitted `changes` field is
`unavailable`). Two frozen document plans pin its exact bytes, so the publisher
serialization rule is applied here as a separate overlay instead.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = 'data/ukraine-amendment-evidence.json'
OUTPUT = 'data/ukraine-amendment-counts.json'
ABSENT = 'changes:absent-no-schema-default-assumed'
REPO = 'https://github.com/ProzorroUKR/openprocurement.api'
COMMIT = '4dfb3a4d9e81f430dae2f22add9751159840e26f'
RULE = {
    'statement': 'An omitted `changes` field means the contract has no changes: the list is created only when the '
                 'first change is posted, and the API serializer never outputs empty lists or nulls.',
    'repository': REPO,
    'commit': COMMIT,
    'verifiedOn': '2026-10-11',
    'sources': [
        {'path': 'src/openprocurement/contracting/core/procedure/models/contract.py', 'lines': '156',
         'quote': 'changes = ListType(ModelType(Change, required=True))'},
        {'path': 'src/openprocurement/contracting/core/procedure/views/change.py', 'lines': '43-44',
         'quote': 'if not contract.get("changes"):\n    contract["changes"] = []'},
        {'path': 'src/openprocurement/api/procedure/serializers/base.py', 'lines': '75-78',
         'quote': 'if serialized_value is None:  # we don\'t show null in our outputs\n    continue\n'
                  'elif isinstance(serialized_value, list) and len(serialized_value) == 0:  # and empty lists\n    continue'},
    ],
    'corroboration': 'No empty list appears anywhere in the 542 cached tender records; sampled modules also omit '
                     '`documents`/`milestones` when empty.',
    'log': 'research/ukraine-corrections-log.md#1-omitted-amendment-list-was-silently-counted-as-zero',
}


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def interpret(root=ROOT):
    blob = (root / EVIDENCE).read_bytes()
    evidence = json.loads(blob)
    rows = []
    for r in evidence['requests']:
        e = r['extract']
        require(r['outcome'] == 'verified-module' and e is not None, 'Unverified module: ' + r['rowId'])
        if e['changesState'] in ('retrieved-array', 'retrieved-empty-array'):
            count, basis = e['activeChangeCount'], 'published-array'
        else:
            # Only a cleanly omitted field qualifies; a null or malformed value stays unknown.
            require(e['changesState'] == 'unavailable' and ABSENT in e['anomalies'] and e['changeCount'] is None,
                    'Unrecognized changes state: ' + r['rowId'])
            count, basis = 0, 'omitted-field-publisher-omits-empty-lists'
        snapshot = r['binding']['contractChangesAtSelection']
        rows.append({'rowId': r['rowId'], 'observedState': e['changesState'], 'activeChangeCount': count,
                     'basis': basis, 'snapshotCount': snapshot, 'agreesWithSnapshot': count == snapshot})
    body = {'schemaVersion': 1, 'evidence': EVIDENCE, 'evidenceFileSha256': hashlib.sha256(blob).hexdigest(),
            'evidenceSha256': evidence['evidenceSha256'], 'publisherRule': RULE, 'rows': rows,
            'counts': {'rows': len(rows), 'byBasis': dict(sorted(Counter(r['basis'] for r in rows).items())),
                       'agreeWithSnapshot': sum(r['agreesWithSnapshot'] for r in rows)}}
    return body


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='fail if the committed overlay is stale')
    args = parser.parse_args()
    body = interpret()
    text = json.dumps(body, ensure_ascii=False, indent=2) + '\n'
    path = ROOT / OUTPUT
    if args.check:
        require(path.read_text(encoding='utf-8') == text, 'Stale amendment-count overlay')
    else:
        path.write_text(text, encoding='utf-8')
    print(json.dumps(body['counts'], sort_keys=True))


if __name__ == '__main__':
    main()
