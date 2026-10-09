#!/usr/bin/env python3
"""Freeze an offline, exact-ID document reading queue; no validation claims or fetching."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PLAN = Path.home() / '.cache/contract-signals/document-review/plan.json'
DATASETS = {
    'boamp': 'data/contracts.json',
    'cities': 'data/decp-cities.json',
    'colombia': 'data/colombia-secop2.json',
    'paraguay': 'data/paraguay-dncp.json',
    'paraguay3': 'data/paraguay-dncp-3buyers.json',
    'uk': 'data/uk-fts.json',
}
STRATA = (
    ('scored-flagged-positive', ('boamp',)),
    ('scored-zero-positive', ('boamp',)),
    ('declared-zero', ('boamp', 'colombia')),
    ('missing-amount', ('boamp', 'uk')),
    ('initial-conflict', ('cities',)),
    ('published-contractSigned', ('paraguay', 'paraguay3')),
)
# No DOM: same helpers as the app, complete datasets prepared separately, never
# selected rows together (supplier context and publication baselines are cohort-local).
NODE_HELPER = r"""
const fs = require('node:fs'), vm = require('node:vm');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const ctx = vm.createContext({URL});
vm.runInContext(input.code, ctx);
const call = (fn, arg) => { ctx.arg = arg; return vm.runInContext(`${fn}(arg)`, ctx); };
const result = {version: vm.runInContext('SCORE_VERSION', ctx), datasets: {}};
for (const [key, rows] of Object.entries(input.datasets)) {
  result.datasets[key] = call('prepareContracts', rows).map(c => {
    const a = call('getAssessment', c);
    return {id:c.id, score:call('getVigilanceScore', c), assessment:{
      evaluated:a.evaluated, applicable:a.applicable,
      unknownApplicability:a.unknownApplicability,
      excluded:Boolean(a.excludedReason),
      checks:a.checks.map(r => ({id:r.id, status:r.status, applicability:r.applicability}))
    }};
  });
}
process.stdout.write(JSON.stringify(result));
"""
ID_FIELDS = ('noticeId', 'lotId', 'contractId', 'contractFolderId', 'processId',
             'procedureId', 'awardId', 'ocid', 'buyerSiret', 'buyerNit', 'buyerId')
VALUE_FIELDS = ('amount', 'currency', 'amountBasis', 'date', 'dateNote',
                'publicationDate', 'signatureDate', 'awardDate', 'callPublishedDate')
URL_HOSTS = {
    'source': {'www.boamp.fr', 'data.economie.gouv.fr', 'www.datos.gov.co',
               'www.contrataciones.gov.py', 'www.find-tender.service.gov.uk'},
    'processUrl': {'community.secop.gov.co'},
    'portalUrl': {'www.find-tender.service.gov.uk'},
    'callUrl': {'www.contrataciones.gov.py'},
    'awardUrl': {'www.contrataciones.gov.py'},
    'signedDocumentUrls': {'www.contrataciones.gov.py'},
}


def digest(blob):
    return hashlib.sha256(blob).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def official_urls(row):
    from urllib.parse import urlsplit
    urls = {}
    for field, hosts in URL_HOSTS.items():
        values = row.get(field, []) if field == 'signedDocumentUrls' else [row.get(field)]
        accepted = []
        for value in values:
            if not isinstance(value, str):
                continue
            url = urlsplit(value)
            if (url.scheme == 'https' and url.hostname in hosts and
                    not url.username and not url.password and url.port in (None, 443)):
                accepted.append(value)
        if accepted:
            urls[field] = sorted(set(accepted)) if field == 'signedDocumentUrls' else accepted[0]
    return urls


def positive(value):
    return type(value) in (int, float) and math.isfinite(value) and value > 0


def eligible(stratum, row, scored):
    amount = row.get('amount')
    if stratum == 'scored-flagged-positive':
        return positive(amount) and positive(scored['score'])
    if stratum == 'scored-zero-positive':
        return positive(amount) and scored['score'] == 0 and not scored['assessment']['excluded']
    if stratum == 'declared-zero':
        return type(amount) in (int, float) and amount == 0 and bool(official_urls(row))
    if stratum == 'missing-amount':
        return amount is None and row.get('dataFamily') in ('boamp', 'fts')
    if stratum == 'initial-conflict':
        return bool(row.get('initialConflicts'))
    if stratum == 'published-contractSigned':
        return bool(official_urls(row).get('signedDocumentUrls'))
    raise ValueError(stratum)


def select_rows(datasets, scores, snapshots):
    selected, used, empty = [], set(), []
    for stratum, scope in STRATA:
        candidates = []
        for dataset in scope:
            for row in datasets[dataset]:
                identity = (dataset, row['id'])
                if identity not in used and eligible(stratum, row, scores[dataset][row['id']]):
                    candidates.append((dataset, row['id'], row))
        if not candidates:
            empty.append(stratum)
            continue
        dataset, row_id, row = min(candidates, key=lambda item: item[:2])
        used.add((dataset, row_id))
        # Explicit allowlists: no description, supplier names/IDs, histories,
        # document filenames, raw variants, or assessment free-text reasons.
        selected.append({
            'stratum': stratum, 'dataset': dataset, 'rowId': row_id,
            'sourceSnapshot': snapshots[dataset],
            'matchingIds': {key: row[key] for key in ID_FIELDS if row.get(key) is not None},
            'published': {key: row.get(key) for key in VALUE_FIELDS},
            'officialUrls': official_urls(row),
            'initialConflicts': row.get('initialConflicts', []),
            'score': scores[dataset][row_id]['score'],
            'assessment': scores[dataset][row_id]['assessment'],
            'reviewStatus': 'queued-not-verified',
        })
    return selected, empty


def build_plan(root=ROOT):
    root = Path(root)
    datasets, snapshots = {}, {}
    for key, relative in DATASETS.items():
        blob = (root / relative).read_bytes()
        rows = json.loads(blob)
        ids = [row['id'] for row in rows]
        if any(not isinstance(i, str) for i in ids) or len(ids) != len(set(ids)):
            raise ValueError(f'Non-unique or invalid row IDs: {key}')
        datasets[key] = rows
        snapshots[key] = {'path': relative, 'sha256': digest(blob)}
    code = (root / 'script.js').read_bytes()
    scored = json.loads(subprocess.run(
        ['node', '-e', NODE_HELPER], input=json.dumps({'code': code.decode(), 'datasets': datasets}),
        text=True, capture_output=True, check=True).stdout)
    scores = {key: {row['id']: row for row in rows}
              for key, rows in scored['datasets'].items()}
    rows, empty = select_rows(datasets, scores, snapshots)
    plan = {
        'protocolVersion': 'document-review-v1',
        'selection': 'fixed strata; lexicographic (dataset key, row ID); no score ranking; no replacements after reading',
        'strata': [{'id': name, 'datasets': list(scope)} for name, scope in STRATA],
        'sourceSnapshots': snapshots,
        'scoring': {'version': scored['version'], 'scriptSha256': digest(code),
                    'helperSha256': digest(NODE_HELPER.encode())},
        'rows': rows, 'emptyStrata': empty,
        'limitations': 'Offline queue, not completed review, independent verification, ground truth, or representative accuracy estimate.',
    }
    plan['planSha256'] = digest(canonical(plan))
    return plan


def verify_hash(plan):
    body = {key: value for key, value in plan.items() if key != 'planSha256'}
    if plan.get('planSha256') != digest(canonical(body)):
        raise ValueError('Existing freeze has an invalid plan hash')


def freeze(plan, path=DEFAULT_PLAN):
    """Exclusive creation; identical reruns do not touch the file or its timestamp."""
    verify_hash(plan)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o400)
    except FileExistsError:
        existing = json.loads(path.read_bytes())
        verify_hash(existing)
        if canonical(existing) != canonical(plan):
            raise ValueError(f'Refusing to overwrite existing freeze: {path}; use a new private path for a new protocol/snapshot')
        return False
    with os.fdopen(fd, 'wb') as output:
        output.write(json.dumps(plan, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False).encode() + b'\n')
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, default=DEFAULT_PLAN,
                        help='Private destination; existing different freezes are never overwritten')
    args = parser.parse_args()
    plan = build_plan()
    created = freeze(plan, args.plan)
    print(json.dumps({'path': str(args.plan), 'created': created,
                      'planSha256': plan['planSha256'], 'emptyStrata': plan['emptyStrata'],
                      'rows': [{k: row[k] for k in ('stratum', 'dataset', 'rowId', 'score')}
                               for row in plan['rows']]}, indent=2))


if __name__ == '__main__':
    main()
