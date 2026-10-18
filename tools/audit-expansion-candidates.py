#!/usr/bin/env python3
"""Offline, bounded audit of the frozen Ukrainian and Romanian candidates.

Writes aggregate findings only; never republishes private SEAP rows or supplier names.
No joins are treated as confirmed contract identity, no live requests are made.
"""
import argparse
from collections import Counter
import contextlib
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
CACHE = Path.home() / '.cache/contract-signals'
MAX_XML_BYTES = 8 * 1024 * 1024
MAX_XML_TOTAL = 64 * 1024 * 1024


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'tools' / filename)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalized_ref(value):
    # Do not erase punctuation, leading zeros, prefixes or infer truncated identifiers.
    return ' '.join(str(value or '').split()).upper()


def native_contracts(body):
    """Return only actual settled contracts, not nested CON-* result references."""
    root = ET.fromstring(body)
    out = {}
    for node in root.findall('.//{*}NoticeResult/{*}SettledContract'):
        internal = (node.findtext('{*}ID') or '').strip()
        reference = normalized_ref(node.findtext('{*}ContractReference/{*}ID'))
        day = (node.findtext('{*}IssueDate') or '')[:10]
        if internal and reference and day:
            value = (reference, day)
            if internal in out and out[internal] != value:
                raise ValueError('Conflicting settled-contract identifier')
            out[internal] = value
    return out


def seap_keys(rows):
    return Counter((r['buyerId'], normalized_ref(r.get('contractId')), r.get('date'))
                   for r in rows if r.get('contractId') and r.get('date'))


def ted_overlap(rows, ted, directory):
    import re
    pubs = sorted({r['noticeId'] for r in ted})
    if len(pubs) > 400:
        raise ValueError('TED notice budget exceeded')
    native, total = {}, 0
    xml_hashes = []
    for pub in pubs:
        if not re.fullmatch(r'\d+-\d{4}', pub):
            raise ValueError('Invalid notice identifier')
        path = directory / f'{pub}.xml.gz'
        with gzip.open(path, 'rb') as fh:
            body = fh.read(MAX_XML_BYTES + 1)
        total += len(body)
        if len(body) > MAX_XML_BYTES or total > MAX_XML_TOTAL:
            raise ValueError('TED XML byte budget exceeded')
        native[pub] = native_contracts(body)
        xml_hashes.append(f'{pub}:{hashlib.sha256(body).hexdigest()}')
    index = {}
    recovered = 0
    for row in ted:
        for internal in re.findall(r'CON-\d+', row.get('contractId') or ''):
            value = native[row['noticeId']].get(internal)
            if not value:
                continue
            recovered += 1
            key = (row['buyerId'], *value)
            index.setdefault(key, set()).add(row['id'])
    keys = seap_keys(rows)
    matching = keys.keys() & index.keys()
    return {
        'cachedNoticesInspected': len(pubs), 'decodedXmlBytes': total,
        'xmlInventorySha256': hashlib.sha256('\n'.join(xml_hashes).encode()).hexdigest(),
        'recoveredTedContractReferences': recovered,
        'seapRowsWithBuyerReferenceDateCandidate': sum(keys[k] for k in matching),
        'tedRowsWithBuyerReferenceDateCandidate': len(set().union(*(index[k] for k in matching))) if matching else 0,
        'sharedBuyerReferenceDateKeys': len(matching),
        'duplicateSeapBuyerReferenceDateKeys': sum(n > 1 for n in keys.values()),
        'confirmedContractLinks': None,
        'method': 'Exact buyer ID + whitespace/case-normalized native contract reference + exact contract date. Punctuation and leading zeros retained. Candidate links only: lot, supplier and framework/call-off identity not adjudicated.',
        'nonMatchesAreNotProvenAdditionalContracts': True,
    }


def audit():
    ua = module('candidate_ua', 'import-prozorro.py')
    seap = module('candidate_ro', 'import-romania-seap.py')
    expansion = ROOT / 'data/prozorro-expansion'
    with tempfile.TemporaryDirectory(prefix='contract-candidate-audit-') as temp:
        with contextlib.redirect_stdout(io.StringIO()):
            ua.expand_cached(expansion / 'config.json', CACHE / 'labels/ukraine-cohort', Path(temp))
        ua_replay = {name: sha(Path(temp) / name) == sha(expansion / name)
                     for name in ('contracts.json', 'coverage.json')}
        if not all(ua_replay.values()):
            raise ValueError('Ukraine replay differs from retained extract')
    ur = json.loads((expansion / 'contracts.json').read_bytes())
    pilot = json.loads((ROOT / 'data/prozorro.json').read_bytes())
    config = json.loads((expansion / 'config.json').read_bytes())
    uc = json.loads((expansion / 'coverage.json').read_bytes())
    if uc['configSha256'] != sha(expansion / 'config.json'):
        raise ValueError('Ukraine config hash mismatch')
    source = CACHE / 'romania-seap' / seap.RELATIVE
    rr, rebuilt = seap.build(source)
    manifest = json.loads((ROOT / 'data/romania-seap-candidate-manifest.json').read_bytes())
    candidate = CACHE / 'romania-seap' / manifest['candidate']['relativePath']
    if (rebuilt['input'] != manifest['input'] or sha(candidate) != manifest['candidate']['sha256']
            or candidate.stat().st_size != manifest['candidate']['bytes']
            or rr != json.loads(candidate.read_bytes())):
        raise ValueError('Romania input, replay or candidate hash mismatch')
    ted_path = ROOT / 'data/ted-romania.json'
    if sha(ted_path) != manifest['overlap']['tedFileSha256']:
        raise ValueError('TED snapshot changed since candidate creation')
    dates = sorted(r['date'] for r in rr if r.get('date'))
    buyers = Counter(r['buyerId'] for r in ur)
    return {
        'schemaVersion': 1, 'mode': 'offline-cache-audit', 'networkRequests': 0,
        'ukraine': {
            'candidateSha256': sha(expansion / 'contracts.json'),
            'pilotSha256': sha(ROOT / 'data/prozorro.json'), 'replayByteIdentical': ua_replay,
            'selectedTenders': len(config['records']), 'retainedRows': len(ur),
            'retainedBuyers': len(buyers), 'buyersWithOneRetainedRow': sum(n == 1 for n in buyers.values()),
            'overlapWithPilot': {key: len({r.get(key) for r in ur if r.get(key)} & {r.get(key) for r in pilot if r.get(key)})
                                 for key in ('id', 'procedureId', 'contractInternalId', 'buyerId')},
            'missingOffers': sum(r.get('offers') is None for r in ur),
            'missingContractChanges': sum('contractChanges' not in r for r in ur),
            'sourceRetrievalRange': [min(r['sourceRetrievedAt'] for r in ur), max(r['sourceRetrievedAt'] for r in ur)],
            'selectionBias': 'Audit/label-research cache convenience sample; hash selection does not remove inherited bias. Not complete buyer histories.',
            'recommendation': 'Do not register as a general second Ukrainian dataset. Keep as a separately labelled research extract; use systematic discovery for real coverage expansion.',
        },
        'romania': {
            'candidateSha256': sha(candidate), 'inputSha256': sha(source),
            'tedSnapshotSha256': sha(ted_path),
            'replayRecordsIdentical': True, 'candidateHashAndBytesMatch': True,
            'retainedRows': len(rr), 'retainedBuyers': len({r['buyerId'] for r in rr}),
            'contractDateRange': [dates[0], dates[-1]],
            'contractDatesOutsideQ12025': sum(not ('2025-01-01' <= r['date'] < '2025-04-01') for r in rr),
            'generatedDescriptions': sum(bool(r.get('descriptionGenerated')) for r in rr),
            'frameworkLabelRows': sum('acord-cadru' in (r['provenance'].get('conclusionType') or '').lower() for r in rr),
            'knownAmounts': sum(r.get('amount') is not None for r in rr),
            'retainedSupplierIds': sum(len(r.get('supplierIds') or []) for r in rr),
            'unknownSupplierLegalForm': sum(r.get('supplierIndividualStatus') == 'unknown' for r in rr),
            'overlap': ted_overlap(rr, json.loads(ted_path.read_bytes()), ROOT / 'data/ted-romania/raw/notices'),
            'privacyCleared': False,
            'recommendation': 'Do not register this candidate yet. A separate SEAP source is worthwhile in principle, but resolve overlap/granularity and review public fields first. Never inherit TED scoring or sum framework values.',
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='Aggregate-only JSON report')
    args = parser.parse_args()
    report = audit()
    text = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        args.output.write_text(text)
    print(text, end='')


if __name__ == '__main__':
    main()
