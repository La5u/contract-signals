#!/usr/bin/env python3
"""Prepare an offline public-document investigation and evidence-gated review queue."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path
import re
import stat

ROOT = Path(__file__).resolve().parents[1]
VERSION = 'public-document-benchmark-v1'
INPUTS = ('data/boamp-decp-links.json', 'data/contracts.json',
          'data/decp-history.json', 'data/decp-cities.json')
DEFAULT = Path.home() / '.cache/contract-signals/public-document-benchmark/v1/plan.json'
EXACT = {'buyer-published-contract-reference', 'buyer-exact-notice-lot'}


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(',', ':'), allow_nan=False).encode()


def digest(blob):
    return hashlib.sha256(blob).hexdigest()


def load_json(blob):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON key')
            result[key] = value
        return result
    return json.loads(blob, object_pairs_hook=unique,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def exact_identity(link, b, d):
    """Recheck identifiers in published rows; never equate notice-local CON IDs."""
    buyer = b.get('buyerSiret')
    if (b.get('dataFamily') != 'boamp' or d.get('dataFamily') != 'decp'
            or not isinstance(buyer, str) or not re.fullmatch(r'[0-9]{14}', buyer)
            or buyer != d.get('buyerSiret') or not d.get('contractId')):
        return False
    basis = set(link['basis'])
    ref = b.get('contractReference')
    contract = ('buyer-published-contract-reference' in basis
                and isinstance(ref, str) and bool(ref.strip())
                and not re.fullmatch(r'CON-\d+', ref.strip(), re.I)
                and ref == d.get('contractId'))
    notice = ('buyer-exact-notice-lot' in basis
              and bool(b.get('noticeId')) and bool(b.get('lotId'))
              and b['noticeId'] == d.get('noticeId') and b['lotId'] == d.get('lotId'))
    return bool(contract or notice)


def build_plan(root=ROOT, seed=VERSION):
    root = Path(root)
    loaded, snapshots = {}, {}
    for name in INPUTS:
        path = root / name
        if path.is_symlink() or not path.resolve().is_relative_to((root / 'data').resolve()):
            raise ValueError('Inputs must be public data files inside data/')
        blob = path.read_bytes()
        loaded[name] = load_json(blob)
        snapshots[name] = digest(blob)
    artifact = loaded[INPUTS[0]]
    if artifact.get('schemaVersion') != 1 or not isinstance(artifact.get('links'), list):
        raise ValueError('Unsupported link artifact')
    indexes = [defaultdict(list), defaultdict(list)]
    for name in INPUTS[1:]:
        rows = loaded[name]
        if not isinstance(rows, list):
            raise ValueError('Dataset must be an array')
        index = indexes[0 if name == INPUTS[1] else 1]
        for row in rows:
            index[row['id']].append((name, row))
    links = artifact['links']
    seen = set()
    for link in links:
        key = (link['boampId'], link['decpId'])
        if any(not isinstance(v, str) or not v for v in key) or key in seen:
            raise ValueError('Invalid/duplicate pair identity')
        seen.add(key)
        for field in ('basis', 'warnings'):
            if not isinstance(link.get(field), list) or any(
                    not isinstance(v, str) for v in link[field]):
                raise ValueError('Invalid link metadata')
    bc = Counter(link['boampId'] for link in links)
    dc = Counter(link['decpId'] for link in links)
    inventory = []
    for link in sorted(links, key=lambda v: (v['boampId'], v['decpId'])):
        reasons = []
        if link.get('status') != 'confirmed':
            reasons.append('unconfirmed-link')
        if not EXACT.intersection(link['basis']):
            reasons.append('no-exact-identifier-basis')
        if 'unconfirmed-no-exact-reference' in link['warnings']:
            reasons.append('unconfirmed-reference-warning')
        if (any(w.startswith('multiple-') for w in link['warnings'])
                or bc[link['boampId']] > 1 or dc[link['decpId']] > 1):
            reasons.append('multiple-match')
        b = indexes[0].get(link['boampId'], [])
        d = indexes[1].get(link['decpId'], [])
        if len(b) != 1 or len(d) != 1:
            reasons.append('missing-or-nonunique-public-row')
        elif not exact_identity(link, b[0][1], d[0][1]):
            reasons.append('exact-identity-not-revalidated-in-public-rows')
        bindings = [{'dataset': name, 'rowId': row['id'], 'rowSha256': digest(canonical(row))}
                    for name, row in b + d]
        rank = digest(canonical([VERSION, seed, link['boampId'], link['decpId']]))
        inventory.append({'boampId': link['boampId'], 'decpId': link['decpId'],
                          'linkStatus': link.get('status'), 'basis': link['basis'],
                          'warnings': link['warnings'], 'linkSha256': digest(canonical(link)),
                          'publicRowBindings': bindings,
                          'status': 'blocked' if reasons else 'eligible-not-reviewed',
                          'blockedReasons': reasons, 'selectionRankSha256': rank})
    queue = sorted(inventory, key=lambda r: (r['selectionRankSha256'], r['boampId'], r['decpId']))
    identity = lambda r: {k: r[k] for k in ('boampId', 'decpId', 'selectionRankSha256')}
    eligible = [r for r in queue if r['status'] == 'eligible-not-reviewed']
    plan = {'protocolVersion': VERSION, 'sourceSnapshots': snapshots,
            'helperSha256': digest(Path(__file__).read_bytes()), 'seed': seed,
            'selection': 'All pairs, SHA-256 rank of canonical [version, seed, boampId, decpId]; no replacement',
            'investigationCohort': inventory, 'investigationQueue': [identity(r) for r in queue],
            'noticeLinkedAgreementQueue': [identity(r) for r in eligible],
            'counts': {'investigationPairs': len(inventory), 'blockedPairs': len(inventory) - len(eligible),
                       'eligiblePairs': len(eligible), 'factualAgreementDenominator': 0},
            'reviewStatus': 'not-performed',
            'limitations': 'Purposive candidate linkage investigation, not representative accuracy. '
                           'Eligibility is not document agreement. No document access, legal obligations, '
                           'amount conclusions, outcomes, or accuracy estimates. Raw-only identifier evidence '
                           'is blocked until published-row revalidation is possible.'}
    plan['planSha256'] = digest(canonical(plan))
    return plan


def verify_hash(plan):
    if plan.get('planSha256') != digest(canonical({k: v for k, v in plan.items() if k != 'planSha256'})):
        raise ValueError('Invalid freeze hash')


def private_path(path, root=ROOT):
    path = Path(path).expanduser().absolute()
    if path.resolve().is_relative_to(Path(root).resolve()):
        raise ValueError('Freeze must be outside repository/served root')
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise ValueError('Symlinked freeze path forbidden')
    return path


def freeze(plan, path=DEFAULT, root=ROOT):
    verify_hash(plan)
    path = private_path(path, root)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.parent.stat().st_mode & 0o077:
        raise ValueError('Freeze directory must be private (0700 or stricter)')
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400)
    except FileExistsError:
        mode = path.stat().st_mode
        if not stat.S_ISREG(mode) or mode & 0o277:
            raise ValueError('Existing freeze must be private and read-only')
        existing = load_json(path.read_bytes())
        verify_hash(existing)
        if canonical(existing) != canonical(plan):
            raise ValueError('Refusing to overwrite different freeze; use a new private path')
        return False
    with os.fdopen(fd, 'wb') as stream:
        stream.write(canonical(plan) + b'\n')
        stream.flush()
        os.fsync(stream.fileno())
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, default=DEFAULT)
    parser.add_argument('--seed', default=VERSION)
    parser.add_argument('--public-output', type=Path,
                        help='Optional minimized public copy of the successfully frozen plan')
    args = parser.parse_args()
    plan = build_plan(seed=args.seed)
    created = freeze(plan, args.plan)
    if args.public_output:
        if args.public_output.resolve() == args.plan.expanduser().resolve():
            raise ValueError('Public copy must not overwrite the immutable freeze')
        args.public_output.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'created': created, 'path': str(args.plan), 'planSha256': plan['planSha256'],
                      'counts': plan['counts']}, indent=2))


if __name__ == '__main__':
    main()
