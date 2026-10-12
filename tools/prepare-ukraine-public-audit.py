#!/usr/bin/env python3
"""Freeze a small public Ukraine review cohort before new contract/document requests."""
import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
VERSION = 'ukraine-public-audit-v1'
INPUTS = ('data/prozorro.json', 'data/prozorro-contract-changes.json',
          'data/prozorro-contract-links.json', 'data/prozorro/raw/manifest.json', 'script.js')
DEFAULT = Path.home() / '.cache/contract-signals/ukraine-public-audit/v1/plan.json'


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def engine_scores(root):
    js = r"""
const fs=require('fs'),vm=require('vm');
const ctx=vm.createContext({URL});vm.runInContext(fs.readFileSync('script.js','utf8'),ctx);
ctx.rows=JSON.parse(fs.readFileSync('data/prozorro.json','utf8'));
const prepared=vm.runInContext('prepareContracts(rows)',ctx);
console.log(JSON.stringify(prepared.map(c=>{ctx.c=c;return {id:c.id,score:vm.runInContext('getScoreBreakdown(c).score',ctx)};})));
"""
    result = subprocess.run(['node', '-e', js], cwd=root, capture_output=True, check=True, timeout=30)
    return {row['id']: row['score'] for row in json.loads(result.stdout)}


def build(root=ROOT, maximum=12, scores=None):
    root = Path(root)
    if type(maximum) is not int or not 1 <= maximum <= 12:
        raise ValueError('Review maximum must be 1..12')
    snapshots = {name: sha((root / name).read_bytes()) for name in INPUTS}
    rows = json.loads((root / INPUTS[0]).read_text())
    scores = engine_scores(root) if scores is None else scores
    if len({r['id'] for r in rows}) != len(rows) or set(scores) != {r['id'] for r in rows}:
        raise ValueError('Nonunique or missing score identities')
    pools = defaultdict(list)
    bindings, amount_queue, raw_snapshots = {}, [], {}
    value_differences = Counter()
    for row_index, row in enumerate(rows):
        count = row.get('contractChanges')
        if type(count) is not int or count < 0:
            raise ValueError('Amendment count unknown; version protocol before selecting')
        group = 'reporting' if row.get('procedure') == 'reporting' else 'competitive-or-other'
        band = '3+' if count >= 3 else '1-2' if count else '0'
        score = scores[row['id']]
        flag = 'flagged' if score is not None and score > 0 else 'zero' if score == 0 else 'not-assessed'
        stratum = '|'.join((group, band, flag))
        pools[stratum].append(row['id'])
        raw_path = 'data/prozorro/raw/records/' + row['tenderID'] + '.json.gz'
        raw_blob = (root / raw_path).read_bytes()
        raw_snapshots[raw_path] = sha(raw_blob)
        tender = json.loads(gzip.decompress(raw_blob))['data']
        matches = [(i, c) for i, c in enumerate(tender.get('contracts', []))
                   if c.get('id') == row.get('contractInternalId')]
        awards = [(i, a) for i, a in enumerate(tender.get('awards', [])) if a.get('id') == row.get('awardId')]
        if len(matches) != 1 or len(awards) != 1:
            raise ValueError('Ambiguous contract/award mapping: ' + row['id'])
        ci, contract = matches[0]
        ai, award = awards[0]
        if (tender.get('id') != row.get('procedureId') or tender.get('tenderID') != row.get('tenderID') or
            tender.get('procuringEntity', {}).get('identifier', {}).get('id') != row.get('buyerId') or
            contract.get('contractID') != row.get('contractId') or contract.get('awardID') != award.get('id')):
            raise ValueError('Exact identity mismatch: ' + row['id'])
        binding = {'rowId': row['id'], 'rowPointer': '/' + str(row_index), 'rowSha256': sha(canonical(row)),
                   'stratum': stratum, 'scoreAtSelection': score, 'contractChangesAtSelection': count,
                   'procedure': row['procedure'], 'buyerId': row['buyerId'], 'tenderID': row['tenderID'],
                   'tenderInternalId': row['procedureId'], 'contractInternalId': row['contractInternalId'],
                   'contractId': row['contractId'], 'awardId': row['awardId'], 'lotId': row.get('lotId'),
                   'rawPath': raw_path, 'contractPointer': '/data/contracts/' + str(ci),
                   'awardPointer': '/data/awards/' + str(ai),
                   'contractURL': 'https://public-api.prozorro.gov.ua/api/2.5/contracts/' + row['contractInternalId'],
                   'tenderURL': row['source'], 'portalURL': row['portalUrl']}
        bindings[row['id']] = binding
        cv, av = contract.get('value') or {}, award.get('value') or {}
        if any(cv.get(k) != av.get(k) for k in ('amount', 'currency', 'valueAddedTaxIncluded')):
            value_differences['amount-currency-vat-tuple'] += 1
        if cv.get('amount') != av.get('amount'):
            value_differences['amount'] += 1
            amount_queue.append(binding)
    rank = lambda row_id, stratum: sha(canonical([VERSION, stratum, row_id]))
    for stratum, ids in pools.items():
        ids.sort(key=lambda row_id: (rank(row_id, stratum), row_id))
    selected = []
    depth = 0
    while len(selected) < min(maximum, len(rows)):
        added = False
        for stratum in sorted(pools):
            if depth < len(pools[stratum]):
                row_id = pools[stratum][depth]
                selected.append({**bindings[row_id], 'selectionRankSha256': rank(row_id, stratum)})
                added = True
                if len(selected) == maximum:
                    break
        if not added:
            break
        depth += 1
    plan = {'schemaVersion': VERSION, 'inputHashes': snapshots, 'rawSnapshotHashes': raw_snapshots,
            'helperSha256': sha(Path(__file__).read_bytes()), 'maximum': maximum,
            'selection': 'Round-robin sorted nonempty procedure x amendment-band x frozen-score strata; within stratum SHA256([version,stratum,rowId]); no replacement after access outcomes.',
            'selectionTiming': 'After existing snapshot inventory and separate discovery probes; before new contract/tender/document acquisition. Not independent validation or a representative accuracy sample.',
            'strata': {k: {'population': len(v), 'selected': sum(r['stratum'] == k for r in selected)} for k, v in sorted(pools.items())},
            'selected': selected, 'amountReviewQueue': sorted(amount_queue, key=lambda r: r['rowId']),
            'valueDifferenceInventory': dict(value_differences),
            'requestBudget': {'contractRecords': len(selected), 'optionalLinkedDocuments': 2,
                              'amountTenderRecords': len(amount_queue), 'discoveryAttempts': 5, 'overallCeiling': 30,
                              'secondsPerAttempt': 15, 'bodyBytesPerAttempt': 2097152,
                              'minimumSpacingSeconds': 1, 'retryCount': 0, 'redirectCount': 0,
                              'stopOnHTTP': [403, 429]},
            'scope': 'Source linkage, amendment count/date/type, financial bases and public discovery diagnostics. No legal conclusions, scoring/weights changes, corruption labels, cohort expansion or automatic field replacement.'}
    if len(selected) + 2 + len(amount_queue) + 5 > 30:
        raise ValueError('Request inventory exceeds fixed overall budget')
    plan['planSha256'] = sha(canonical(plan))
    return plan


def verify(plan):
    body = {k: v for k, v in plan.items() if k != 'planSha256'}
    if plan.get('planSha256') != sha(canonical(body)):
        raise ValueError('Plan hash mismatch')


def freeze(plan, path=DEFAULT, root=ROOT):
    verify(plan)
    path = Path(path).expanduser().absolute()
    if path.resolve().is_relative_to(Path(root).resolve()) or any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('Freeze must be private, external and not symlinked')
    path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    if path.parent.stat().st_mode & 0o077:
        raise ValueError('Freeze directory must be private')
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400)
    except FileExistsError:
        if path.stat().st_mode & 0o277:
            raise ValueError('Freeze must be read-only and private')
        existing = json.loads(path.read_text())
        verify(existing)
        if existing != plan:
            raise ValueError('Different existing freeze; use a new protocol/path')
        return False
    with os.fdopen(fd, 'wb') as stream:
        stream.write(canonical(plan) + b'\n')
        stream.flush()
        os.fsync(stream.fileno())
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, default=DEFAULT)
    parser.add_argument('--public-output', type=Path, default=ROOT / 'data/ukraine-public-audit-plan.json')
    args = parser.parse_args()
    plan = build()
    created = freeze(plan, args.plan)
    if args.public_output.resolve() == args.plan.expanduser().resolve():
        raise ValueError('Public output cannot overwrite freeze')
    args.public_output.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'created': created, 'planSha256': plan['planSha256'],
                      'selected': len(plan['selected']), 'strata': plan['strata'],
                      'amountQueue': len(plan['amountReviewQueue']), 'requestBudget': plan['requestBudget']}, indent=2))


if __name__ == '__main__':
    main()
