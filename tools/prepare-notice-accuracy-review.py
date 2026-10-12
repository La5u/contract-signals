#!/usr/bin/env python3
"""Offline, evidence-gated French notice review preregistration. Never fetch or score."""
import argparse
from collections import Counter
from datetime import date
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
import stat
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
DATASETS = ('data/decp-cities.json', 'data/decp-history.json')
DEFAULT = Path.home() / '.cache/contract-signals/notice-accuracy-review/v1/plan.json'
VERSION = 'notice-accuracy-review-v1'
OPEN = "Appel d'offres ouvert"
STRATA = ('sources-agree', 'sources-disagree', 'single-source', 'notice-checked', 'unknown')
# Candidate mapping only: these constants are NOT primary-law verification.
THRESHOLDS = {
    2020: (5350000, 139000, 214000, '32019R1828'),
    2021: (5350000, 139000, 214000, '32019R1828'),
    2022: (5382000, 140000, 215000, '32021R1952'),
    2023: (5382000, 140000, 215000, '32021R1952'),
    2024: (5538000, 143000, 221000, '32023R2495'),
    2025: (5538000, 143000, 221000, '32023R2495'),
}
FIXED = {
    'regime': '2014/24/EU-ordinary', 'procedure': 'open',
    'awardKind': 'standalone-awarded-contract',
    'exclusions': 'reviewed-none-applicable',
    'valuationBasis': 'estimated-total-excluding-vat-options-renewals',
    'valuationScope': 'article-5-applicable-aggregate',
    'currency': 'EUR', 'lotTreatment': 'reviewed-no-derogation',
    'noticeDuty': 'individual-award-notice-required',
}
REQUIRED = tuple(FIXED) + ('buyerCategory', 'contractType', 'procurementStartDate',
                          'estimatedValue', 'thresholdRule', 'identityLink')


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(',', ':'), allow_nan=False).encode()


def digest(blob):
    return hashlib.sha256(blob).hexdigest()


def row_hash(row):
    return digest(canonical(row))


def load_json(blob):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f'Duplicate JSON key: {key}')
            result[key] = value
        return result
    return json.loads(blob, object_pairs_hook=unique,
                      parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))


def private_path(path, root=ROOT):
    """Reject repository/served-root outputs and symlinked paths; do not chmod ancestors."""
    path = Path(path).expanduser().absolute()
    if path.resolve().is_relative_to(Path(root).resolve()):
        raise ValueError('Evidence and freezes must be outside the repository/served root')
    for part in (path, *path.parents):
        if part.is_symlink():
            raise ValueError(f'Symlink forbidden: {part}')
    return path


def reference(ref, evidence_dir, root):
    if not isinstance(ref, dict):
        raise ValueError('Evidence reference must be an object')
    rel = Path(ref.get('path', ''))
    if rel.is_absolute() or '..' in rel.parts or str(rel) == '.':
        raise ValueError('Evidence path must be relative to the private evidence directory')
    path = private_path(Path(evidence_dir) / rel, root)
    if not path.resolve().is_relative_to(Path(evidence_dir).resolve()):
        raise ValueError('Evidence escapes directory')
    for parent in path.parents:
        if parent == Path(evidence_dir).absolute().parent:
            break
        if parent.stat().st_mode & 0o077:
            raise ValueError('Evidence directories must be private')
    mode = path.stat().st_mode
    if not stat.S_ISREG(mode) or mode & 0o077:
        raise ValueError('Evidence must be a private regular file')
    actual = digest(path.read_bytes())
    if actual != ref.get('sha256'):
        raise ValueError('Evidence checksum mismatch')
    url = urlsplit(ref.get('url', ''))
    host = url.hostname or ''
    if (url.scheme != 'https' or url.username or url.password or
            url.port not in (None, 443) or not (
                host in ('eur-lex.europa.eu', 'www.legifrance.gouv.fr', 'www.boamp.fr',
                         'ted.europa.eu', 'data.economie.gouv.fr') or host.endswith('.gouv.fr'))):
        raise ValueError('Evidence requires an official HTTPS URL')
    if not isinstance(ref.get('locator'), str) or not ref['locator'].strip():
        raise ValueError('Evidence requires a page/article/field locator')
    return {k: ref[k] for k in ('path', 'sha256', 'url', 'locator')}


def decimal(value):
    if not isinstance(value, str):
        raise ValueError('Estimated value must be a decimal string, not an inferred published amount')
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError('Invalid decimal') from exc
    if not result.is_finite() or result <= 0:
        raise ValueError('Estimated value must be finite and positive')
    return result


def eligibility(row, entry, evidence_dir, root=ROOT):
    """Fail closed. Legal and factual review are caller attestations, never inferred."""
    if row.get('procedure') is None:
        return 'unknown', ['missing-published-procedure'], None
    if row['procedure'] != OPEN:
        return 'ineligible', ['not-exact-demonstrably-open-label'], None
    if entry is None:
        return 'unknown', ['missing-reviewed-eligibility-manifest'], None
    if entry.get('rowSha256') != row_hash(row):
        raise ValueError('Stale row binding in eligibility manifest')
    if any(not isinstance(entry.get(k), str) or not entry[k].strip()
           for k in ('reviewedBy', 'reviewedOn')):
        return 'unknown', ['missing-review-attestation'], None
    date.fromisoformat(entry['reviewedOn'])
    facts = entry.get('facts', {})
    missing = [key for key in REQUIRED if not isinstance(facts.get(key), dict)
               or facts[key].get('value') is None or not facts[key].get('evidence')]
    if missing:
        return 'unknown', ['missing-evidence:' + key for key in missing], None
    proofs = {}
    for key in REQUIRED:
        proofs[key] = {'value': facts[key]['value'], 'evidence': [
            reference(ref, evidence_dir, root) for ref in facts[key]['evidence']]}
    values = {key: facts[key]['value'] for key in REQUIRED}
    mismatch = [key for key, value in FIXED.items() if values[key] != value]
    if mismatch:
        return 'ineligible', ['unsupported-scope:' + key for key in mismatch], proofs
    link = values['identityLink']
    if (not isinstance(link, dict) or not row.get('buyerSiret') or not row.get('contractId')
            or link.get('buyerSiret') != row['buyerSiret']
            or link.get('contractId') != row['contractId']
            or any(not isinstance(link.get(k), str) or not link[k].strip()
                   for k in ('procedureId', 'documentVersion'))):
        return 'unknown', ['identity-link-unestablished'], proofs
    if values['buyerCategory'] not in ('central', 'subcentral'):
        return 'unknown', ['unknown-buyer-category'], proofs
    if values['contractType'] not in ('works', 'supplies', 'ordinary-services'):
        return 'unknown', ['unsupported-or-unknown-contract-type'], proofs
    start = date.fromisoformat(values['procurementStartDate'])
    if start.isoformat() != values['procurementStartDate'] or start.year not in THRESHOLDS:
        return 'unknown', ['unsupported-procurement-start-date'], proofs
    works, central, subcentral, celex = THRESHOLDS[start.year]
    threshold = works if values['contractType'] == 'works' else (
        central if values['buyerCategory'] == 'central' else subcentral)
    rule = values['thresholdRule']
    expected = {'celex': celex, 'amountEUR': str(threshold), 'primaryTextReviewed': True,
                'dateType': 'call-dispatch-or-procurement-commencement',
                'applicabilityReviewed': True}
    if rule != expected:
        return 'unknown', ['threshold-primary-law-or-applicability-unverified'], proofs
    legal_refs = proofs['thresholdRule']['evidence'] + proofs['noticeDuty']['evidence']
    if any(urlsplit(ref['url']).hostname not in ('eur-lex.europa.eu', 'www.legifrance.gouv.fr')
           for ref in legal_refs):
        return 'unknown', ['legal-proof-not-primary-law'], proofs
    # Strictly above, not equality: narrower than legal "at or above" scope.
    if decimal(values['estimatedValue']) <= Decimal(threshold):
        return 'ineligible', ['not-strictly-above-reviewed-threshold'], proofs
    return 'eligible', ['reviewer-attested-obligation-and-applicability'], proofs


def build_plan(root=ROOT, manifest_path=None, evidence_dir=None, seed='notice-review-v1', per_stratum=10):
    root = Path(root)
    if type(per_stratum) is not int or not 1 <= per_stratum <= 100:
        raise ValueError('Per-stratum must be 1..100')
    entries, manifest_hash = {}, None
    if manifest_path is not None:
        manifest_path = private_path(manifest_path, root)
        blob = manifest_path.read_bytes()
        manifest_hash = digest(blob)
        manifest = load_json(blob)
        if manifest.get('schemaVersion') != VERSION or evidence_dir is None:
            raise ValueError('Manifest version/evidence directory required')
        evidence_dir = private_path(evidence_dir, root)
        if evidence_dir.stat().st_mode & 0o077 or manifest_path.stat().st_mode & 0o077:
            raise ValueError('Manifest and evidence directory must be private')
        for entry in manifest['records']:
            key = (entry['dataset'], entry['rowId'])
            if key in entries:
                raise ValueError('Duplicate manifest identity')
            entries[key] = entry
    inventory, snapshots, seen = [], {}, set()
    for dataset in DATASETS:
        blob = (root / dataset).read_bytes()
        snapshots[dataset] = digest(blob)
        for row in load_json(blob):
            key = (dataset, row['id'])
            if not isinstance(row['id'], str) or not row['id'] or key in seen:
                raise ValueError('Invalid/duplicate dataset row ID')
            seen.add(key)
            status, reasons, proofs = eligibility(row, entries.get(key), evidence_dir, root)
            stratum = (row.get('verification') or {}).get('status')
            if stratum not in STRATA:
                stratum = 'unknown'
            inventory.append({'dataset': dataset, 'rowId': row['id'], 'rowSha256': row_hash(row),
                              'status': status, 'reasons': reasons, 'stratum': stratum,
                              'reviewedEvidence': proofs,
                              'reviewer': {k: entries[key].get(k) for k in ('reviewedBy', 'reviewedOn')}
                              if key in entries else None})
    if set(entries) - seen:
        raise ValueError('Manifest contains identities outside frozen datasets')
    selected, strata = [], {}
    for stratum in STRATA:
        pool = [item for item in inventory if item['status'] == 'eligible' and item['stratum'] == stratum]
        def rank(item):
            return digest(canonical([VERSION, seed, item['dataset'], item['rowId']]))
        pool.sort(key=lambda item: (rank(item), item['dataset'], item['rowId']))
        strata[stratum] = {'eligiblePopulation': len(pool), 'selected': min(len(pool), per_stratum)}
        selected.extend({'dataset': item['dataset'], 'rowId': item['rowId'], 'stratum': stratum,
                         'selectionRankSha256': rank(item), 'reviewStatus': 'queued-not-reviewed'}
                        for item in pool[:per_stratum])
    plan = {'protocolVersion': VERSION, 'sourceSnapshots': snapshots,
            'helperSha256': digest(Path(__file__).read_bytes()), 'manifestSha256': manifest_hash,
            'seed': seed, 'perStratum': per_stratum, 'strata': strata,
            'selection': 'SHA-256 rank of canonical [version, seed, dataset, rowId]; no replacement',
            'eligibility': inventory, 'sample': selected,
            'limitations': 'Reviewer attestations are not verified by this tool. No outcomes, measured accuracy, legal advice or proof of upstream truth. Unknowns never enter sample.'}
    plan['planSha256'] = digest(canonical(plan))
    return plan


def verify_hash(plan):
    body = {k: v for k, v in plan.items() if k != 'planSha256'}
    if plan.get('planSha256') != digest(canonical(body)):
        raise ValueError('Invalid freeze hash')


def freeze(plan, path=DEFAULT, root=ROOT):
    verify_hash(plan)
    path = private_path(path, root)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.parent.stat().st_mode & 0o077:
        raise ValueError('Freeze directory must be mode 0700 or stricter')
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400)
    except FileExistsError:
        if not stat.S_ISREG(path.stat().st_mode) or path.stat().st_mode & 0o277:
            raise ValueError('Existing freeze must be a private read-only regular file')
        existing = load_json(path.read_bytes())
        verify_hash(existing)
        if canonical(existing) != canonical(plan):
            raise ValueError('Refusing to overwrite different freeze; use a new private protocol path')
        return False
    with os.fdopen(fd, 'wb') as stream:
        stream.write(canonical(plan) + b'\n')
        stream.flush()
        os.fsync(stream.fileno())
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--evidence-dir', type=Path)
    parser.add_argument('--plan', type=Path, default=DEFAULT)
    parser.add_argument('--seed', default='notice-review-v1')
    parser.add_argument('--per-stratum', type=int, default=10)
    args = parser.parse_args()
    plan = build_plan(manifest_path=args.manifest, evidence_dir=args.evidence_dir,
                      seed=args.seed, per_stratum=args.per_stratum)
    created = freeze(plan, args.plan)
    print(json.dumps({'path': str(args.plan), 'created': created, 'planSha256': plan['planSha256'],
                      'eligibilityCounts': dict(Counter(r['status'] for r in plan['eligibility'])),
                      'strata': plan['strata'], 'sampleSize': len(plan['sample'])}, indent=2))


if __name__ == '__main__':
    main()
