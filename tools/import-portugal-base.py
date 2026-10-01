#!/usr/bin/env python3
"""Offline BASE candidate importer. Default is plan-only (no archive or network IO).

--extract scans the three private ZIPs sequentially, verifying download hashes,
and atomically creates a NEW private candidate directory; it never publishes.
--publish-reviewed reads only that candidate and the small provenance documents,
requires --reviewer and --candidate-sha256, validates the minimized schema, and
copies to data/portugal-base{,-coverage}.json without replacing differing files.
A reviewer authorizes name disclosure/redistribution, not factual verification.
No network code, archive extraction to disk, UI mutation, or inferred party type.
"""
import argparse
import base64
from collections import Counter
from datetime import date
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / 'data/portugal-base-download-plan.json'
DOWNLOADS = ROOT / 'data/portugal-base-downloads.json'
CACHE = Path(os.environ.get('XDG_CACHE_HOME', str(Path.home() / '.cache'))) / 'contract-signals'
CHUNK_BYTES = 64 * 1024
MAX_RECORD_BYTES = 1024 * 1024
MAX_DEPTH = 64
MAX_COHORT = 20000
MAX_CANDIDATE_BYTES = 20 * 1024 * 1024  # Strictly below this limit.
MAX_MEMBER_BYTES = 512 * 1024 * 1024
YEARS = (2024, 2025, 2026)
NOTES = [
    'Source documented; no independent factual verification. Browse only, no allegations.',
    'Company names retained as published after removing NIF prefixes. A holder whose NIF is blank or begins with 1, 2, 3 or 45 is an individual, or a foreign entity without a Portuguese number: the name is published by BASE and can be shown one record at a time, but it is stored scrambled and replaced by a stable code in lists, search and exports. No supplier or competitor identifiers.',
    'precoContratual is a platform declaration; currency is unverified. Execution duration unit is unknown.',
    'Only dataPublicacao selects the window. Missing/invalid publication dates are excluded, never replaced by signing dates.',
    'Missing/unparseable buyers prevent a claim of full cohort coverage. Conflicting minimized variants are all omitted for review.',
]
AMOUNT_BASIS = 'Source precoContratual; platform declaration; currency unverified.'
SOURCE_LABEL = 'Official BASE dataset · search by contract identifier'
DATE_NOTE = 'Source dataPublicacao: publication date, not signing or award date.'
# Natural persons: Portuguese NIFs beginning 1, 2 or 3 (residents) or 45 (non-residents), and
# holders whose NIF the register blanks. A blank NIF can also be a foreign entity without a
# Portuguese number, hence the neutral label. Names stay viewable per record, not in bulk.
PERSON_NIF = re.compile(r'(?:[123][0-9]{8}|45[0-9]{7})\Z')
PERSON_LABEL = 'Individual or foreign holder'
NAME_SALT = b'contract-signals:base:name:v1'
NAME_ITERATIONS = 400_000  # deliberately slow; the browser repeats it for each name shown
EMAIL = re.compile(r'[^\s@]+@[^\s@]+\.[^\s@]+')
ERRORS = {'buyer-shape', 'supplier-shape', 'contract-id', 'amount', 'subject'}
ROW_COUNTS = ('matchingBuyerRows', 'outsideWindowRows', 'invalidPublicationDateRows',
              'inWindowRows', 'rejectedNormalizationRows', 'normalizedRows',
              'duplicateIdenticalRows', 'conflictingRows', 'extractedRows')
COUNT_KEYS = ('nationalRows', 'nonMatchingBuyerRows', 'unknownBuyerRows', 'buyerParseErrorRows') + ROW_COUNTS
PARTY_PREFIX = re.compile(r'^\s*([0-9]{9})\s*[-–]\s*')
# A holder published with a blank tax number: two separators, then the name (" - - NAME").
BLANK_NIF_PREFIX = re.compile(r'^\s*[-–]\s*[-–]\s*')
ID_RE = re.compile(r'[0-9]+\Z')
CPV_RE = re.compile(r'([0-9]{8})(?:-[0-9])?(?:\s+[-–]\s+[^\r\n]+)?\Z')


def fail(message):
    # All diagnostics are fixed schema/error descriptions, never source values.
    raise ValueError(message)


def no_constant(_):
    fail('Nonstandard JSON number.')


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            fail('Duplicate JSON property.')
        result[key] = value
    return result


def decode_json(blob):
    try:
        return json.loads(blob, parse_constant=no_constant, object_pairs_hook=unique_keys)
    except (UnicodeError, json.JSONDecodeError, RecursionError):
        fail('Malformed JSON.')


def iter_json_array(stream, chunk_bytes=CHUNK_BYTES, record_max=MAX_RECORD_BYTES, max_depth=MAX_DEPTH):
    """Frame object records in bounded byte chunks, then use the generic decoder.

    JSON syntax within a record is checked by json.loads; the framing state
    strictly checks array commas/closing delimiters and EOF/trailing garbage.
    UTF-8 (including multibyte characters split across chunks) is decoded only
    after a complete bounded record. Depth and byte limits precede decoding.
    """
    if not 0 < chunk_bytes <= CHUNK_BYTES or not 0 < record_max <= MAX_RECORD_BYTES:
        fail('Parser limits exceed policy.')
    if not 0 < max_depth <= MAX_DEPTH:
        fail('Parser depth exceeds policy.')
    state, record, stack = 'start', bytearray(), []
    quoted = escaped = False
    prefix = bytearray()
    first = True
    while True:
        chunk = stream.read(chunk_bytes)
        if not chunk:
            break
        # Accommodate a split UTF-8 BOM without buffering an entire stream.
        if first:
            prefix.extend(chunk)
            if len(prefix) < 3 and b'\xef\xbb\xbf'.startswith(prefix):
                continue
            chunk = bytes(prefix)
            prefix.clear()
            first = False
            if chunk.startswith(b'\xef\xbb\xbf'):
                chunk = chunk[3:]
        for char in chunk:
            if state == 'record':
                record.append(char)
                if len(record) > record_max:
                    fail('JSON record exceeds byte limit.')
                if quoted:
                    if escaped:
                        escaped = False
                    elif char == 92:
                        escaped = True
                    elif char == 34:
                        quoted = False
                elif char == 34:
                    quoted = True
                elif char in (123, 91):
                    stack.append(char)
                    if len(stack) > max_depth:
                        fail('JSON record exceeds depth limit.')
                elif char in (125, 93):
                    if not stack or (stack.pop(), char) not in ((123, 125), (91, 93)):
                        fail('Mismatched JSON delimiter.')
                    if not stack:
                        row = decode_json(bytes(record))
                        if not isinstance(row, dict):
                            fail('Expected JSON record object.')
                        record.clear()
                        state = 'delimiter'
                        yield row
                continue
            if char in b' \t\r\n':
                continue
            if state == 'start' and char == 91:
                state = 'first-record'
            elif state in ('first-record', 'next-record') and char == 123:
                record.append(char)
                stack = [char]
                state = 'record'
            elif state == 'first-record' and char == 93:
                state = 'end'
            elif state == 'delimiter' and char == 44:
                state = 'next-record'
            elif state == 'delimiter' and char == 93:
                state = 'end'
            else:
                fail('Invalid array delimiter or trailing JSON content.')
    if state != 'end' or prefix:
        fail('Incomplete JSON array; no partial output permitted.')


def parse_date(value):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9]{2}/[0-9]{2}/[0-9]{4}', value):
        return None
    try:
        return date(int(value[6:]), int(value[3:5]), int(value[:2])).isoformat()
    except ValueError:
        return None


def parse_party(value):
    """Strict nine-digit NIF + separator; the name's content is not rewritten."""
    if not isinstance(value, str):
        return None
    match = PARTY_PREFIX.match(value)
    if not match:
        return None
    name = value[match.end():]
    # Reject identifier-only/nested party strings rather than disclose an ID as a name.
    if not name.strip() or re.search(r'(?<![0-9])[0-9]{9}(?![0-9])', name) or name.strip().isdigit():
        return None
    return match.group(1), name


def parse_supplier(value):
    """A holder: strict NIF + name, or a blank NIF + name. Only the name is kept either way."""
    party = parse_party(value)
    if party is not None or not isinstance(value, str):
        return party
    match = BLANK_NIF_PREFIX.match(value)
    if not match:
        return None
    name = value[match.end():]
    # Same guards as parse_party: never keep an identifier, or nothing, as a name.
    if not name.strip() or re.search(r'[0-9]{9}', name) or name.strip().isdigit():
        return None
    return None, name


def person_code(name):
    """Stable short code for one published name, so repeat holders can be recognised."""
    key = ' '.join(name.casefold().split()).encode('utf-8')
    return hashlib.sha256(NAME_SALT + b':code:' + key).hexdigest()[:8]


def scramble_name(record_id, index, name):
    """XOR with a keystream from a slow, record-specific key. A deterrent to bulk collection,
    not secrecy: the method is public and the names are public at the source."""
    data = name.encode('utf-8')
    key = hashlib.pbkdf2_hmac('sha256', record_id.encode('utf-8'), NAME_SALT + b':%d' % index, NAME_ITERATIONS, 32)
    stream = b''.join(hashlib.sha256(key + bytes([block])).digest() for block in range(len(data) // 32 + 1))
    return base64.b64encode(bytes(a ^ b for a, b in zip(data, stream))).decode('ascii')


def is_person(nif):
    return nif is None or bool(PERSON_NIF.match(nif))


def parse_buyers(row, selected):
    values = row.get('adjudicante')
    if not isinstance(values, list) or not values:
        return [], [], True
    parties = [parse_party(value) for value in values]
    valid = [party for party in parties if party is not None]
    matched = sorted({nif for nif, _ in valid if nif in selected})
    return valid, matched, len(valid) != len(parties)


def contract_id(value):
    if isinstance(value, int) and not isinstance(value, bool) and 0 <= value < 10 ** 64:
        return str(value)
    if isinstance(value, str) and ID_RE.fullmatch(value) and len(value) <= 64:
        return value  # Preserve the source numeric text, including leading zeroes.
    return None


def number(value):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and value >= 0 and (not isinstance(value, float) or math.isfinite(value)))


def cpv_code(value):
    if not isinstance(value, list) or not value:
        return None
    codes = set()
    for item in value:
        match = CPV_RE.fullmatch(item) if isinstance(item, str) else None
        if not match:
            return None  # Do not salvage codes from mixed malformed/free-text classifications.
        codes.add(match.group(1))
    return next(iter(codes)) if len(codes) == 1 else None


def normalize(row, plan, buyers, matched, buyer_error=False):
    """Minimize a selected row only. ValueError messages are reason codes."""
    if buyer_error:
        fail('buyer-shape')
    cid = contract_id(row.get('idcontrato'))
    if cid is None:
        fail('contract-id')
    suppliers = row.get('adjudicatarios')
    if suppliers is None:
        suppliers = []
    if not isinstance(suppliers, list):
        fail('supplier-shape')
    parties = [parse_supplier(item) for item in suppliers]
    if any(party is None for party in parties):
        fail('supplier-shape')
    record_id = f'base-{cid}'
    names, protected = [], []
    for index, (nif, name) in enumerate(parties):
        if is_person(nif):
            if len(name.encode('utf-8')) > 255 * 32:
                fail('supplier-shape')
            code = person_code(name)
            names.append(f'{PERSON_LABEL} · {code}')
            protected.append({'code': code, 'data': scramble_name(record_id, index, name)})
        else:
            names.append(name)
            protected.append(None)
    amount = row.get('precoContratual')
    if amount is not None and not number(amount):
        fail('amount')
    subject_key, subject = None, None
    for key in ('descContrato', 'objectoContrato'):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            subject_key, subject = key, value
            break
    # Subject is the ONLY permitted source free-text field; no party/procedure raw dump.
    if subject is None or re.search(r'(?<![0-9])[0-9]{9}(?![0-9])', subject) or EMAIL.search(subject):
        fail('subject')
    # A subject line that repeats a protected holder's name would publish it in clear.
    for (nif, name), item in zip(parties, protected):
        words = name.split()
        if item and len(words) >= 2:
            pattern = re.compile(r'\s+'.join(re.escape(word) for word in words), re.IGNORECASE)
            subject = pattern.sub(f'[{PERSON_LABEL.lower()} · {item["code"]}]', subject)
    publication = parse_date(row.get('dataPublicacao'))
    result = {
        'id': f'base-{cid}', 'contractId': cid, 'country': 'PT', 'source': plan['dataset'],
        'sourceLabel': SOURCE_LABEL,
        'assessmentMode': 'browse', 'dataStatus': 'unverified',
        'primarySource': plan['dataset'], 'sourceReference': f'BASE contract {cid}',
        'buyer': ' / '.join(name for _, name in buyers),
        'buyerNamesPublished': [name for _, name in buyers], 'buyerIds': matched,
        'supplier': ' / '.join(names) if names else None, 'supplierNamesPublished': names,
        'description': subject, 'publicationDate': publication, 'date': publication,
        'dateNote': DATE_NOTE,
        'amount': amount, 'amountBasis': AMOUNT_BASIS, 'currency': None,
        'durationMonths': None, 'offers': None, 'directAward': None,
        'cpv': cpv_code(row.get('cpv')),
        'baseSigningDate': parse_date(row.get('dataCelebracaoContrato')),
        'baseAwardDate': parse_date(row.get('dataDecisaoAdjudicacao')),
        'baseClosureDate': parse_date(row.get('dataFechoContrato')),
        'notes': ' '.join(NOTES),
    }
    if len(buyers) == 1:
        result['buyerId'] = matched[0]
    result['raw'] = {subject_key: subject}
    if any(protected):
        result['supplierProtectedNames'] = protected
    duration = row.get('prazoExecucao')
    if number(duration):
        result['baseDurationOriginal'] = {'value': duration, 'unit': 'unknown'}
    return result


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True,
                       indent=2) + '\n').encode('utf-8')


def sha256(blob):
    return hashlib.sha256(blob).hexdigest()


def bounded_read(path, limit=MAX_CANDIDATE_BYTES):
    with Path(path).open('rb') as stream:
        blob = stream.read(limit + 1)
    if len(blob) >= limit:
        fail('Document exceeds byte limit.')
    return blob


def read_inputs(plan_path=PLAN, downloads_path=DOWNLOADS):
    plan_blob = bounded_read(plan_path, 1024 * 1024)
    downloads_blob = bounded_read(downloads_path, 1024 * 1024)
    plan, downloads = decode_json(plan_blob), decode_json(downloads_blob)
    if not isinstance(plan, dict) or not isinstance(downloads, dict):
        fail('Expected scope/provenance documents.')
    selected = plan.get('buyerNifs')
    if (not isinstance(selected, list) or not selected
            or any(not isinstance(nif, str) or not re.fullmatch(r'[0-9]{9}', nif) for nif in selected)
            or len(selected) != len(set(selected))):
        fail('Invalid preregistered buyer scope.')
    window = plan.get('window', {})
    if not isinstance(window, dict):
        fail('Invalid preregistered date scope.')
    try:
        start, end = date.fromisoformat(window['startInclusive']), date.fromisoformat(window['endExclusive'])
        if start >= end or start.isoformat() != window['startInclusive'] or end.isoformat() != window['endExclusive']:
            fail('Invalid preregistered date scope.')
    except (ValueError, KeyError, TypeError):
        fail('Invalid preregistered date scope.')
    if not isinstance(plan.get('dataset'), str) or not plan['dataset'].startswith('https://dados.gov.pt/datasets/'):
        fail('Expected official dataset primary source.')
    resources = plan.get('resources', [])
    entries = downloads.get('downloads', [])
    if (not isinstance(resources, list) or not isinstance(entries, list)
            or any(not isinstance(item, dict) for item in resources + entries)
            or [r.get('year') for r in resources] != list(YEARS) or len(entries) != 3):
        fail('Expected exactly three annual archive provenance records.')
    provenance = []
    for resource in resources:
        year = resource['year']
        if resource.get('filename') != f'contratos{year}.zip':
            fail('Unexpected archive filename.')
        matches = [entry for entry in entries if entry.get('year') == year]
        if len(matches) != 1:
            fail('Missing or ambiguous archive provenance.')
        entry = matches[0]
        if (entry.get('status') != 'downloaded'
                or any(entry.get(key) != resource.get(key) for key in ('filename', 'url', 'resourceId', 'expectedBytes'))
                or not isinstance(entry.get('sha256'), str) or not re.fullmatch(r'[0-9a-f]{64}', entry['sha256'])
                or type(entry.get('bytes')) is not int or entry['bytes'] != resource['expectedBytes']
                or not 0 < entry['bytes'] <= 60 * 1024 * 1024):
            fail('Invalid downloaded archive provenance.')
        provenance.append({'year': year, 'bytes': entry['bytes'], 'sha256': entry['sha256']})
    if sum(entry['bytes'] for entry in provenance) > 160 * 1024 * 1024:
        fail('Annual archives exceed total byte budget.')
    return plan, provenance, {'planSha256': sha256(plan_blob), 'downloadsSha256': sha256(downloads_blob)}


def private_path(path):
    path = Path(path).expanduser().resolve()
    forbidden = [ROOT.resolve(), Path('/var/www'), Path('/srv/www'), Path('/srv/http'), Path('/usr/share/nginx/html')]
    if any(path == base or path.is_relative_to(base) for base in forbidden):
        fail('Private storage must be outside repository/webroots.')
    return path


def scope(plan):
    return {'buyerIds': plan['buyerNifs'], 'startInclusive': plan['window']['startInclusive'],
            'endExclusive': plan['window']['endExclusive'], 'dateField': 'dataPublicacao'}


def reconcile(counts, national=False):
    if any(type(value) is not int or value < 0 for value in counts.values()):
        fail('Invalid aggregate count.')
    if national and counts['nationalRows'] != sum(counts[key] for key in ('matchingBuyerRows', 'nonMatchingBuyerRows', 'unknownBuyerRows')):
        fail('National reconciliation failed.')
    if counts['matchingBuyerRows'] != sum(counts[key] for key in ('outsideWindowRows', 'invalidPublicationDateRows', 'inWindowRows')):
        fail('Date reconciliation failed.')
    if counts['inWindowRows'] != counts['rejectedNormalizationRows'] + counts['normalizedRows']:
        fail('Normalization reconciliation failed.')
    if counts['normalizedRows'] != sum(counts[key] for key in ('duplicateIdenticalRows', 'conflictingRows', 'extractedRows')):
        fail('Deduplication reconciliation failed.')


def collect(archives, plan, provenance):
    """Consume sequential (year, object-iterator) pairs; fixtures need no ZIPs."""
    selected = set(plan['buyerNifs'])
    counts = dict.fromkeys(COUNT_KEYS, 0)
    per_buyer = {nif: dict.fromkeys(ROW_COUNTS, 0) for nif in plan['buyerNifs']}
    errors, groups, rejected_ids, archive_counts = Counter(), {}, set(), []
    minimized_bytes = 0

    def tally(key, ids):
        counts[key] += 1
        for nif in ids:
            per_buyer[nif][key] += 1

    for year, rows in archives:
        scanned = 0
        for row in rows:
            scanned += 1
            counts['nationalRows'] += 1
            buyers, matched, buyer_error = parse_buyers(row, selected)
            if buyer_error:
                counts['buyerParseErrorRows'] += 1
            if not matched:
                counts['unknownBuyerRows' if buyer_error else 'nonMatchingBuyerRows'] += 1
                continue
            tally('matchingBuyerRows', matched)
            publication = parse_date(row.get('dataPublicacao'))
            if publication is None:
                tally('invalidPublicationDateRows', matched)
                continue
            if not plan['window']['startInclusive'] <= publication < plan['window']['endExclusive']:
                tally('outsideWindowRows', matched)
                continue
            tally('inWindowRows', matched)
            if counts['inWindowRows'] > MAX_COHORT:
                fail('Selected cohort exceeds record limit.')
            try:
                record = normalize(row, plan, buyers, matched, buyer_error)
            except ValueError as error:
                reason = str(error)
                if reason not in ERRORS:
                    raise
                errors[reason] += 1
                tally('rejectedNormalizationRows', matched)
                cid = contract_id(row.get('idcontrato'))
                if cid is not None:
                    rejected_ids.add(cid)
                continue
            tally('normalizedRows', matched)
            canonical = json_bytes(record)
            cid = record['contractId']
            if cid not in groups:
                minimized_bytes += len(canonical)
                if minimized_bytes >= MAX_CANDIDATE_BYTES:
                    fail('Minimized cohort exceeds byte limit.')
                groups[cid] = {'record': record, 'canonical': canonical, 'conflict': False, 'occurrences': []}
            group = groups[cid]
            if not group['conflict'] and canonical != group['canonical']:
                group['conflict'] = True
                minimized_bytes -= len(group['canonical'])
                group['record'] = group['canonical'] = None  # Conflicts can never be resurrected.
            group['occurrences'].append(matched)
        archive_counts.append({'year': year, 'scannedRows': scanned})
    if [entry['year'] for entry in archive_counts] != list(YEARS):
        fail('Incomplete sequential annual scan.')
    candidate, review = [], []
    for cid, group in sorted(groups.items()):
        if group['conflict'] or cid in rejected_ids:
            review.append({'contractId': cid, 'reason': 'conflicting-variants'})
            for ids in group['occurrences']:
                tally('conflictingRows', ids)
        else:
            candidate.append(group['record'])
            tally('extractedRows', group['occurrences'][0])
            for ids in group['occurrences'][1:]:
                tally('duplicateIdenticalRows', ids)
    for cid in sorted(rejected_ids):
        review.append({'contractId': cid, 'reason': 'normalization-rejected'})
    reconcile(counts, national=True)
    for entry in per_buyer.values():
        reconcile(entry)
    completeness = ('unknown' if any(counts[key] for key in
                    ('buyerParseErrorRows', 'invalidPublicationDateRows', 'rejectedNormalizationRows', 'conflictingRows'))
                    else 'complete-for-parseable-buyers')
    coverage = {'schemaVersion': 1, 'status': 'candidate',
                'assessmentMode': 'browse', 'dataStatus': 'unverified',
                'primarySource': plan['dataset'], 'scope': scope(plan), 'completeScan': True,
                'completeness': completeness, 'counts': counts, 'perBuyer': per_buyer,
                'normalizationErrors': dict(errors), 'reviewQueue': review, 'notes': NOTES,
                'archives': [{**entry, 'scannedRows': summary['scannedRows']}
                             for entry, summary in zip(provenance, archive_counts)]}
    return candidate, coverage


def archive_rows(archive_dir, provenance):
    """One archive at a time, hash first, then bounded member streaming; no disk extraction."""
    for entry in provenance:
        year = entry['year']
        path = archive_dir / f'contratos{year}.zip'
        digest, size = hashlib.sha256(), 0
        with path.open('rb') as stream:
            while True:
                chunk = stream.read(CHUNK_BYTES)
                if not chunk:
                    break
                size += len(chunk)
                if size > entry['bytes']:
                    fail('Archive exceeds provenance size.')
                digest.update(chunk)
            if size != entry['bytes'] or digest.hexdigest() != entry['sha256']:
                fail('Archive fingerprint mismatch.')
            stream.seek(0)
            with zipfile.ZipFile(stream) as archive:
                matches = [member for member in archive.infolist() if member.filename == f'Contratos{year}.json']
                if len(matches) != 1 or matches[0].flag_bits & 1 or matches[0].file_size > MAX_MEMBER_BYTES:
                    fail('Unexpected, encrypted or oversized JSON member.')
                with archive.open(matches[0]) as member:
                    yield year, iter_json_array(member)


def write_private(path, blob):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(blob)
        stream.flush()
        os.fsync(stream.fileno())


def extract(candidate_dir, archive_dir, plan_path=PLAN, downloads_path=DOWNLOADS):
    destination, archives = private_path(candidate_dir), private_path(archive_dir)
    if destination.exists():
        fail('Candidate directory already exists; no overwrite.')
    plan, provenance, fingerprints = read_inputs(plan_path, downloads_path)
    candidate, coverage = collect(archive_rows(archives, provenance), plan, provenance)
    candidate_blob, coverage_blob = json_bytes(candidate), json_bytes(coverage)
    if len(candidate_blob) >= MAX_CANDIDATE_BYTES:
        fail('Candidate exceeds byte limit.')
    validate_candidate(candidate, plan)
    validate_coverage(coverage, candidate, plan, provenance)
    manifest = {'schemaVersion': 1, 'status': 'candidate', **fingerprints,
                'candidateSha256': sha256(candidate_blob),
                'coverageSha256': sha256(coverage_blob), 'completeScan': True,
                'reviewRequired': True, 'assessmentMode': 'browse', 'dataStatus': 'unverified'}
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.base-candidate-', dir=destination.parent))
    try:
        for name, blob in [('candidate.json', candidate_blob), ('coverage.json', coverage_blob), ('manifest.json', json_bytes(manifest))]:
            write_private(staging / name, blob)
        # Never merge with an existing directory, even if a concurrent process created it.
        if destination.exists():
            fail('Candidate directory already exists; no overwrite.')
        staging.rename(destination)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return manifest


REQUIRED_RECORD = {'id', 'contractId', 'country', 'source', 'sourceLabel', 'date', 'dateNote',
                   'assessmentMode', 'dataStatus',
                   'primarySource', 'sourceReference', 'buyer', 'buyerNamesPublished', 'buyerIds',
                   'supplier', 'supplierNamesPublished', 'description', 'publicationDate', 'amount',
                   'amountBasis', 'currency', 'durationMonths', 'offers', 'directAward', 'cpv',
                   'baseSigningDate', 'baseAwardDate', 'baseClosureDate', 'notes'}
OPTIONAL_RECORD = {'buyerId', 'raw', 'baseDurationOriginal', 'supplierProtectedNames'}


def safe_names(names, nonempty=False):
    if not isinstance(names, list) or (nonempty and not names):
        fail('Invalid minimized published-name list.')
    for name in names:
        if (not isinstance(name, str) or not name.strip() or name.strip().isdigit()
                or re.search(r'(?<![0-9])[0-9]{9}(?![0-9])', name)):
            fail('Invalid minimized published name.')


def iso_date(value):
    if not isinstance(value, str):
        return False
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def validate_candidate(records, plan):
    """Strict publication whitelist; no extra raw, identities, claims, or arbitrary fields."""
    if not isinstance(records, list) or len(records) > MAX_COHORT:
        fail('Invalid candidate array.')
    seen = set()
    for record in records:
        if (not isinstance(record, dict) or not REQUIRED_RECORD <= record.keys()
                or not record.keys() <= REQUIRED_RECORD | OPTIONAL_RECORD):
            fail('Candidate record fields violate publication whitelist.')
        cid = contract_id(record['contractId'])
        if cid is None or not isinstance(record['contractId'], str) or cid in seen:
            fail('Invalid or duplicate candidate contract ID.')
        seen.add(cid)
        fixed = {'id': f'base-{cid}', 'country': 'PT', 'source': plan['dataset'],
                 'sourceLabel': SOURCE_LABEL, 'dateNote': DATE_NOTE, 'assessmentMode': 'browse',
                 'dataStatus': 'unverified', 'primarySource': plan['dataset'],
                 'sourceReference': f'BASE contract {cid}', 'amountBasis': AMOUNT_BASIS,
                 'currency': None, 'durationMonths': None, 'offers': None, 'directAward': None,
                 'notes': ' '.join(NOTES)}
        if any(record[key] != value for key, value in fixed.items()):
            fail('Candidate claims/source metadata violate publication policy.')
        safe_names(record['buyerNamesPublished'], nonempty=True)
        safe_names(record['supplierNamesPublished'])
        if record['buyer'] != ' / '.join(record['buyerNamesPublished']):
            fail('Invalid buyer display.')
        supplier = ' / '.join(record['supplierNamesPublished']) if record['supplierNamesPublished'] else None
        if record['supplier'] != supplier:
            fail('Invalid supplier display.')
        protected = record.get('supplierProtectedNames')
        if protected is not None:
            names = record['supplierNamesPublished']
            if not isinstance(protected, list) or len(protected) != len(names) or not any(protected):
                fail('Invalid protected-name list.')
            for name, item in zip(names, protected):
                if item is None:
                    if name.startswith(PERSON_LABEL):
                        fail('Unprotected natural-person label.')
                    continue
                if (not isinstance(item, dict) or item.keys() != {'code', 'data'}
                        or not re.fullmatch(r'[0-9a-f]{8}', str(item['code']))
                        or not isinstance(item['data'], str) or not re.fullmatch(r'[A-Za-z0-9+/]+=*', item['data'])
                        or name != f"{PERSON_LABEL} · {item['code']}"):
                    fail('Invalid protected name.')
        elif any(name.startswith(PERSON_LABEL) for name in record['supplierNamesPublished']):
            fail('Unprotected natural-person label.')
        ids = record['buyerIds']
        if (not isinstance(ids, list) or not ids or any(nif not in plan['buyerNifs'] for nif in ids)
                or ids != sorted(set(ids)) or len(ids) > len(record['buyerNamesPublished'])):
            fail('Invalid preselected buyer IDs.')
        if len(record['buyerNamesPublished']) == 1:
            if record.get('buyerId') != ids[0]:
                fail('Invalid single buyer ID.')
        elif 'buyerId' in record:
            fail('Single buyer ID on multi-buyer contract.')
        publication = record['publicationDate']
        if (not iso_date(publication) or record['date'] != publication
                or not plan['window']['startInclusive'] <= publication < plan['window']['endExclusive']):
            fail('Candidate outside publication-date scope.')
        for key in ('baseSigningDate', 'baseAwardDate', 'baseClosureDate'):
            if record[key] is not None and not iso_date(record[key]):
                fail('Invalid labelled source date.')
        if record['amount'] is not None and not number(record['amount']):
            fail('Invalid candidate amount.')
        if record['cpv'] is not None and (not isinstance(record['cpv'], str) or not re.fullmatch(r'[0-9]{8}', record['cpv'])):
            fail('Invalid candidate CPV classification.')
        if 'baseDurationOriginal' in record:
            duration = record['baseDurationOriginal']
            if (not isinstance(duration, dict) or set(duration) != {'value', 'unit'}
                    or duration['unit'] != 'unknown' or not number(duration['value'])):
                fail('Invalid original duration.')
        subject = record['description']
        raw = record.get('raw')
        if (not isinstance(subject, str) or not subject.strip()
                or re.search(r'(?<![0-9])[0-9]{9}(?![0-9])', subject)
                or not isinstance(raw, dict) or len(raw) != 1
                or not set(raw) <= {'descContrato', 'objectoContrato'} or next(iter(raw.values())) != subject):
            fail('Invalid minimized source subject.')


def validate_coverage(report, records, plan, provenance):
    required = {'schemaVersion', 'status', 'assessmentMode', 'dataStatus', 'primarySource', 'scope', 'completeScan',
                'completeness', 'counts', 'perBuyer', 'normalizationErrors', 'reviewQueue', 'notes', 'archives'}
    if not isinstance(report, dict) or set(report) != required:
        fail('Coverage fields violate publication whitelist.')
    fixed = {'schemaVersion': 1, 'status': 'candidate', 'assessmentMode': 'browse', 'dataStatus': 'unverified',
             'primarySource': plan['dataset'], 'scope': scope(plan), 'completeScan': True, 'notes': NOTES}
    if any(report[key] != value for key, value in fixed.items()):
        fail('Invalid coverage metadata.')
    counts = report['counts']
    if not isinstance(counts, dict) or set(counts) != set(COUNT_KEYS):
        fail('Invalid coverage counts.')
    reconcile(counts, national=True)
    if counts['extractedRows'] != len(records) or counts['inWindowRows'] > MAX_COHORT:
        fail('Candidate/count reconciliation failed.')
    if not counts['unknownBuyerRows'] <= counts['buyerParseErrorRows'] <= counts['nationalRows']:
        fail('Buyer parse reconciliation failed.')
    completeness = ('unknown' if any(counts[key] for key in
                    ('buyerParseErrorRows', 'invalidPublicationDateRows', 'rejectedNormalizationRows', 'conflictingRows'))
                    else 'complete-for-parseable-buyers')
    if report['completeness'] != completeness:
        fail('Invalid completeness claim.')
    buyers = report['perBuyer']
    if not isinstance(buyers, dict) or set(buyers) != set(plan['buyerNifs']):
        fail('Invalid buyer coverage scope.')
    for nif, entry in buyers.items():
        if not isinstance(entry, dict) or set(entry) != set(ROW_COUNTS):
            fail('Invalid per-buyer count fields.')
        reconcile(entry)
        if entry['extractedRows'] != sum(nif in row['buyerIds'] for row in records):
            fail('Per-buyer candidate reconciliation failed.')
        if any(entry[key] > counts[key] for key in ROW_COUNTS):
            fail('Per-buyer counts exceed national counts.')
    for key in ROW_COUNTS:
        if not counts[key] <= sum(entry[key] for entry in buyers.values()) <= counts[key] * len(buyers):
            fail('Multi-buyer count reconciliation failed.')
    errors = report['normalizationErrors']
    if (not isinstance(errors, dict) or not set(errors) <= ERRORS
            or any(type(value) is not int or value <= 0 for value in errors.values())
            or sum(errors.values()) != counts['rejectedNormalizationRows']):
        fail('Invalid normalization error aggregates.')
    queue = report['reviewQueue']
    if not isinstance(queue, list) or len(queue) > MAX_COHORT * 2:
        fail('Invalid review queue.')
    seen = set()
    candidate_ids = {row['contractId'] for row in records}
    for item in queue:
        if (not isinstance(item, dict) or set(item) != {'contractId', 'reason'}
                or not isinstance(item['contractId'], str) or contract_id(item['contractId']) is None
                or item['reason'] not in ('conflicting-variants', 'normalization-rejected')
                or (item['contractId'], item['reason']) in seen
                or item['contractId'] in candidate_ids):
            fail('Review queue violates minimized schema.')
        seen.add((item['contractId'], item['reason']))
    archives = report['archives']
    if not isinstance(archives, list) or len(archives) != 3:
        fail('Invalid scan provenance.')
    for actual, expected in zip(archives, provenance):
        if (not isinstance(actual, dict) or set(actual) != {'year', 'bytes', 'sha256', 'scannedRows'}
                or any(actual[key] != value for key, value in expected.items())
                or type(actual['scannedRows']) is not int or actual['scannedRows'] < 0):
            fail('Invalid archive scan fingerprint/count.')
    if sum(entry['scannedRows'] for entry in archives) != counts['nationalRows']:
        fail('Archive/national reconciliation failed.')


def publish_reviewed(candidate_dir, reviewer, candidate_sha256, plan_path=PLAN,
                     downloads_path=DOWNLOADS, output_dir=None):
    """No archive IO. Fingerprints bind review to the exact private candidate bytes."""
    directory = private_path(candidate_dir)
    if (not isinstance(reviewer, str) or not reviewer.strip() or len(reviewer) > 200
            or any(ord(char) < 32 for char in reviewer)):
        fail('A nonempty reviewer confirmation is required.')
    if not isinstance(candidate_sha256, str) or not re.fullmatch(r'[0-9a-f]{64}', candidate_sha256):
        fail('An explicit candidate SHA-256 confirmation is required.')
    if not directory.is_dir() or directory.stat().st_mode & 0o077:
        fail('Candidate directory must be private (mode 0700).')
    for name in ('candidate.json', 'coverage.json', 'manifest.json'):
        path = directory / name
        if path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o077:
            fail('Candidate documents must be private regular files.')
    candidate_blob = bounded_read(directory / 'candidate.json')
    coverage_blob = bounded_read(directory / 'coverage.json')
    manifest = decode_json(bounded_read(directory / 'manifest.json', 1024 * 1024))
    plan, provenance, fingerprints = read_inputs(plan_path, downloads_path)
    expected = {'schemaVersion': 1, 'status': 'candidate', **fingerprints,
                'candidateSha256': sha256(candidate_blob),
                'coverageSha256': sha256(coverage_blob), 'completeScan': True,
                'reviewRequired': True, 'assessmentMode': 'browse', 'dataStatus': 'unverified'}
    if manifest != expected or candidate_sha256 != expected['candidateSha256']:
        fail('Review/candidate/provenance fingerprint mismatch.')
    candidate, coverage = decode_json(candidate_blob), decode_json(coverage_blob)
    validate_candidate(candidate, plan)
    validate_coverage(coverage, candidate, plan, provenance)
    if not candidate:
        fail('No public cohort: reviewed candidate is empty; private review report retained.')
    published_coverage = {**coverage, 'status': 'reviewed', 'publicationReview': {
        'reviewer': reviewer.strip(), 'candidateSha256': candidate_sha256,
        'privateCoverageSha256': expected['coverageSha256'], **fingerprints,
        'confirmation': 'Reviewed minimized redistribution and published names; browse only, not factual verification.'}}
    output_dir = Path(output_dir) if output_dir is not None else ROOT / 'data'
    # The dataset is the final install/commit point: names are never installed
    # before the complete reviewer-bearing coverage document.
    payloads = {'portugal-base-coverage.json': json_bytes(published_coverage), 'portugal-base.json': candidate_blob}
    # Preflight BOTH destinations before touching either; differing existing output is never replaced.
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, blob in payloads.items():
        path = output_dir / name
        if path.is_symlink() or (path.exists() and bounded_read(path) != blob):
            fail('Existing published output differs; explicit manual review required, no overwrite.')
    staging = Path(tempfile.mkdtemp(prefix='.base-publication-', dir=output_dir))
    created = []
    try:
        for name, blob in payloads.items():
            write_private(staging / name, blob)
            (staging / name).chmod(0o644)
        for name, blob in payloads.items():
            destination = output_dir / name
            if destination.exists():
                if bounded_read(destination) != blob:
                    fail('Concurrent differing output; no overwrite.')
                continue
            # link is an atomic no-overwrite installation of a complete file.
            os.link(staging / name, destination)
            created.append(destination)
    except BaseException:
        for path in reversed(created):
            path.unlink()
        raise
    finally:
        shutil.rmtree(staging)
    return published_coverage['publicationReview']


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--extract', action='store_true')
    mode.add_argument('--publish-reviewed', action='store_true')
    parser.add_argument('--candidate-dir', type=Path, default=CACHE / 'base-candidate')
    parser.add_argument('--archive-dir', type=Path, default=CACHE / 'base-archives')
    parser.add_argument('--reviewer')
    parser.add_argument('--candidate-sha256')
    args = parser.parse_args(argv)
    try:
        if args.extract:
            manifest = extract(args.candidate_dir, args.archive_dir)
            print(f"Private candidate complete; SHA-256 {manifest['candidateSha256']}. No publication or UI changes.")
        elif args.publish_reviewed:
            publish_reviewed(args.candidate_dir, args.reviewer, args.candidate_sha256)
            print('Reviewed candidate published in browse/unverified mode; UI unchanged.')
        else:
            print(json.dumps(decode_json(bounded_read(PLAN, 1024 * 1024)), ensure_ascii=False, indent=2))
            print('Plan only: no network, archive reads, extraction, publication or UI changes.')
    except Exception:  # Sanitized diagnostics also cover corrupt ZIP decompression/input schemas.
        print('BASE operation stopped: invalid schema, limits, fingerprints, private storage or output conflict. No source values logged.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
