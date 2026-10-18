#!/usr/bin/env python3
"""Bounded, offline SEAP candidate from ONE existing normalized quarter; no downloads.

Output is private, browse-only, unverified. Public manifest contains aggregates only.
The existing cache is an input, not an authenticated or privacy-cleared source.
"""
import argparse
from collections import Counter
from datetime import date
import gzip
import hashlib
import json
import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
CACHE = Path.home() / '.cache/contract-signals/romania-seap'
RELATIVE = 'normalized/2025/Contracte-T1-2025.xlsx.jsonl.gz'
RESOURCE = 'https://data.gov.ro/dataset/e0cf7ffc-1fa0-4ffb-a82f-c83981d81f21/resource/7344eeaf-c478-4f87-9669-c1bac3e521a8'
BUYERS = {'4221306', '4288110', '4305857'}
MAX_ROWS = 200000
MAX_BYTES = 96 * 1024 * 1024
MAX_LINE = 256 * 1024
MAX_OUTPUT = 20000


def cui(value):
    """Exact organization-ID formatting variants only; never loose digit extraction."""
    s = str(value or '').strip().upper()
    return re.sub(r'^RO[ -]*', '', s) if re.fullmatch(r'(?:RO[ -]*)?\d{1,10}', s) else None


def iso_date(value):
    s = str(value or '').strip()
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}(?: 00:00:00)?', s):
        return None
    try:
        return date.fromisoformat(s[:10]).isoformat()
    except ValueError:
        return None


def candidate(row, line_number, digest):
    buyer_id = cui(row.get('buyer_cui'))
    if buyer_id not in BUYERS:
        return None
    if not str(row.get('buyer') or '').strip():
        raise ValueError('Selected row lacks buyer label')
    cpv = str(row.get('cpv') or '').strip()
    # This export has no contract subject column. Do not misrepresent a CPV label
    # or generated locator as a published contract title.
    description = 'SEAP contract export row (subject not supplied)'
    if re.fullmatch(r'\d{8}(?:-\d)?', cpv):
        description += ' · CPV ' + cpv
    provenance = {'resource': RESOURCE, 'normalizedFile': RELATIVE,
                  'normalizedSha256': digest, 'normalizedLine': line_number,
                  'noticeInitiation': row.get('notice_init'),
                  'noticeAward': row.get('notice_award'), 'lot': row.get('lot'),
                  'conclusionType': row.get('concluded_by')}
    return {
        'id': f'ro-seap-2025q1-{digest[:16]}-{line_number}',
        'cohortId': 'romania-seap-2025q1-candidate',
        'country': 'ROU', 'dataStatus': 'unverified', 'assessmentMode': 'browse',
        'buyer': row['buyer'], 'buyerId': buyer_id,
        'description': description, 'descriptionGenerated': True,
        'supplier': row.get('winner') or None,
        # No CUI for winners: even an apparently short ID is not privacy clearance.
        'supplierIds': [], 'supplierIndividualStatus': 'unknown',
        'date': iso_date(row.get('contract_date')),
        'dateNote': 'Source contract date; NOT publication date or an extraction-window filter.',
        'contractId': row.get('contract_no') or None,
        'procedure': row.get('procedure') or None,
        'directAward': None, 'offers': None, 'durationMonths': None,
        'amount': None, 'currency': None,
        'amountBasis': 'Not adopted: framework/contract/call-off granularity and value basis need review. No totals.',
        'cpv': cpv if re.fullmatch(r'\d{8}(?:-\d)?', cpv) else None,
        'source': RESOURCE, 'sourceLabel': 'ADR / SEAP, Contracte T1 2025 (data.gov.ro)',
        'provenance': provenance,
        'notes': 'Private candidate. Browse only, no scoring. Published supplier name retained; entity type unknown. No independent verification or TED deduplication.',
    }


def build(source):
    if source.stat().st_size > 8 * 1024 * 1024:
        raise ValueError('Compressed input exceeds 8 MiB budget')
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    records, counts, seen = [], Counter(), set()
    total_bytes = 0
    with gzip.open(source, 'rb') as fh:
        while True:
            raw = fh.readline(MAX_LINE + 1)
            if not raw:
                break
            total_bytes += len(raw)
            counts['inputRows'] += 1
            if len(raw) > MAX_LINE or total_bytes > MAX_BYTES or counts['inputRows'] > MAX_ROWS:
                raise ValueError(f'Input budget exceeded at row {counts["inputRows"]}, decoded bytes {total_bytes}, line bytes {len(raw)}; refusing partial-cohort output')
            row = json.loads(raw)
            if row.get('source') != '2025/Contracte-T1-2025.xlsx':
                raise ValueError('Unexpected source in frozen quarter')
            rec = candidate(row, counts['inputRows'], digest)
            if rec is None:
                continue
            # Detect, do NOT silently merge or sum repeated contract/lot/winner rows.
            key = json.dumps(row, sort_keys=True, ensure_ascii=False)
            counts['exactRepeatedSelectedRows'] += key in seen
            seen.add(key)
            records.append(rec)
            if len(records) > MAX_OUTPUT:
                raise ValueError('Explorer record limit exceeded')
    counts['selectedRows'] = len(records)
    return records, {
        'schemaVersion': 1, 'cohortId': 'romania-seap-2025q1-candidate',
        'status': 'private-candidate-not-registered', 'method': 'browse-only',
        'input': {'relativePath': RELATIVE, 'sha256': digest,
                  'compressedBytes': source.stat().st_size, 'decodedBytes': total_bytes},
        'selection': {'buyerIds': sorted(BUYERS), 'resource': RESOURCE,
                      'basis': 'All matching buyer identifiers in one cached Contracte T1 2025 export; not a contract-date or publication-date filter.'},
        'counts': dict(counts),
        'byBuyer': dict(sorted(Counter(r['buyerId'] for r in records).items())),
        'missingContractDates': sum(r['date'] is None for r in records),
        'conclusionTypes': dict(Counter(r['provenance']['conclusionType'] for r in records)),
        'rights': {'license': 'CC-BY-4.0', 'attribution': 'Autoritatea pentru Digitalizarea României, SEAP/SICAP via data.gov.ro; minimized and transformed by Contract Signals',
                   'evidence': 'data/romania-seap-rights.json',
                   'privacyCleared': False},
        'overlap': {'tedFile': 'data/ted-romania.json',
                    'tedFileSha256': hashlib.sha256((ROOT / 'data/ted-romania.json').read_bytes()).hexdigest(),
                    'tedRows': len(json.loads((ROOT / 'data/ted-romania.json').read_text())),
                    'sameBuyerIds': sorted(BUYERS), 'confirmedRecordLinks': None,
                    'assessment': 'Not joined: TED contractId is a local eForms CON-* reference, not the SEAP national contract number; native CAN/SCN identifiers are not retained in the TED normalized file. Same buyer or similar date/value/name does not establish overlap. Do not add totals or merge.'},
        'limits': {'maxInputRows': MAX_ROWS, 'maxDecodedBytes': MAX_BYTES,
                   'maxOutputRows': MAX_OUTPUT, 'networkRequests': 0},
        'blockers': ['Supplier names and free-text locators need privacy/content review; supplier legal form unknown.',
                     'Export has no contract subject field: descriptions are explicitly generated locators.',
                     'Duplicate publication-date headers are ambiguous; no publication date adopted.',
                     'Framework, call-off and contract value semantics not validated; all amounts and scores withheld.',
                     'National identifiers must be recovered from bounded TED XML before exact overlap audit.',
                     'Existing normalized cache is not independently authenticated against the original export.'],
    }


def private_write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as fh:
            fh.write(text)
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, default=CACHE)
    parser.add_argument('--manifest', type=Path, help='Optional aggregate-only public manifest path')
    args = parser.parse_args()
    cache = args.cache.expanduser().resolve()
    if cache == ROOT or ROOT in cache.parents:
        parser.error('Cache/candidate must remain outside repository/web root')
    records, manifest = build(cache / RELATIVE)
    output = cache / 'candidates/romania-seap-2025q1.json'
    text = json.dumps(records, ensure_ascii=False, indent=2) + '\n'
    if len(text.encode()) > 25 * 1024 * 1024:
        raise ValueError('Explorer file limit exceeded')
    private_write(output, text)
    manifest['candidate'] = {'relativePath': 'candidates/romania-seap-2025q1.json',
                             'sha256': hashlib.sha256(text.encode()).hexdigest(),
                             'bytes': len(text.encode()), 'dataStatus': 'unverified'}
    private_write(cache / 'candidates/romania-seap-2025q1-manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    if args.manifest:
        args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'counts': manifest['counts'], 'byBuyer': manifest['byBuyer'],
                      'candidate': str(output)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
