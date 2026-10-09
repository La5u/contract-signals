#!/usr/bin/env python3
"""Offline inventory of published rows, not validation of contracts or payments.

Only script.js's explicit datasets registry is scanned: no glob of data/*.json,
no raw/coverage/metadata files, no network and no third-party dependencies.
Default: private exact-ID review.jsonl under ~/.cache/contract-signals/accuracy-review.
Public-safe aggregate JSON is written only with --output (use '-' for stdout).
"""

import argparse
from collections import Counter
from datetime import date, datetime
import json
import math
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUEUE = Path.home() / '.cache/contract-signals/accuracy-review'
PLACEHOLDERS = frozenset({
    'unknown', 'not available', 'not provided', 'not disclosed', 'n/a', 'na',
    'null', 'none', '-', '—', 'objet non renseigné', 'acheteur non renseigné',
    'fournisseur non renseigné', 'non renseigné',
})
NOTES = [
    'Inventory of published normalized rows, not validated contracts, payments, legality or accuracy.',
    'Rows may be notices, lots, awards or aggregate audit dossiers; counts are not unique contracts.',
    'Null and missing amounts are absent; numeric zero is separately declared, not inferred erroneous.',
    'Currency unknown means absent/blank or not uppercase three-letter syntax; ISO membership is not validated. No currency conversion or amount sums.',
    'Legacy UI defaults absent currency to EUR when assessmentMode is absent; this inventory never fills currency.',
    'Dates check only top-level date (YYYY-MM-DD) and publicationDate (ISO date or zoned timestamp); no chronology or source semantics validation.',
    'Placeholder matching is a conservative exact vocabulary plus identifier-only supplier labels; no semantic correctness inference.',
    'Conflict counts overlap and describe exclusion markers used by the UI, not a reproduction of every indicator eligibility rule.',
    'Review reasons are triage signals, including expected unavailable fields on notice rows. No source URLs are fetched.',
]


FILE_KEYS = {'data/decp-cities.json': 'cities'}  # the six-city import inside the merged France DECP dataset


def published_datasets(root):
    """Read the current one-entry-per-line JS registry; fail on format drift."""
    text = (root / 'script.js').read_text(encoding='utf-8')
    match = re.search(r'\bconst datasets = \{\n(.*?)^  \};', text, re.M | re.S)
    if not match:
        raise ValueError('Cannot locate explicit datasets registry')
    entries = []
    for line in match[1].splitlines():
        if not line.strip():
            continue
        key = re.match(r'\s*([a-z][a-z0-9]*): \{', line)
        single = re.search(r"\bpath: '([^']+)'", line)
        several = re.search(r"\bpath: \[([^\]]+)\]", line)
        if not key or (not single and not several and not re.search(r'\bpath: null\b', line)):
            raise ValueError('Unsupported datasets registry format')
        files = [single[1]] if single else re.findall(r"'([^']+)'", several[1]) if several else []
        for file in files:
            relative = Path(file)
            if relative.is_absolute() or '..' in relative.parts or relative.suffix != '.json' or relative.parts[0] != 'data':
                raise ValueError('Unsupported published path')
            # One explorer dataset may load several import files; each keeps its audit key.
            entries.append((FILE_KEYS.get(relative.as_posix(), key[1]), relative.as_posix()))
    if not entries or len(set(k for k, _ in entries)) != len(entries):
        raise ValueError('Empty or duplicate datasets registry')
    return entries


def amount_category(row):
    if 'amount' not in row:
        return 'missing'
    value = row['amount']
    if value is None:
        return 'null'
    if type(value) not in (int, float) or (isinstance(value, float) and not math.isfinite(value)):
        return 'non_numeric'
    return 'zero_declared' if value == 0 else 'negative' if value < 0 else 'positive'


def date_category(value, timestamp=False):
    if value is None or (isinstance(value, str) and not value.strip()):
        return 'missing'
    if not isinstance(value, str):
        return 'invalid'
    try:
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
            date.fromisoformat(value)
        elif timestamp and re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})', value):
            # Python versions may accept 24:00 or normalize offset minutes.
            if int(value[11:13]) >= 24 or int(value[14:16]) >= 60 or int(value[17:19]) >= 60:
                return 'invalid'
            if value[-1] != 'Z' and (int(value[-5:-3]) >= 24 or int(value[-2:]) >= 60):
                return 'invalid'
            datetime.fromisoformat(value.replace('Z', '+00:00'))
        else:
            return 'invalid'
    except ValueError:
        return 'invalid'
    return 'valid'


def text_category(value, field):
    if value is None or (isinstance(value, str) and not value.strip()):
        return 'empty'
    if not isinstance(value, str):
        return 'non_text'
    normalized = ' '.join(value.casefold().split())
    if normalized in PLACEHOLDERS:
        return 'placeholder'
    if field == 'supplier' and re.fullmatch(r'(?:siret|siren|identifiant) \S+(?: / (?:siret|siren|identifiant) \S+)*', normalized):
        return 'identifier_only'
    return 'present'


def source_category(value):
    if value is None or (isinstance(value, str) and not value.strip()):
        return 'missing'
    if not isinstance(value, str):
        return 'invalid'
    try:
        parsed = urlsplit(value)
        return 'present' if parsed.scheme in ('http', 'https') and parsed.hostname else 'invalid'
    except ValueError:
        return 'invalid'


def histogram(categories):
    return dict.fromkeys(categories, 0)


def audit_rows(rows, dataset_path):
    if not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows):
        raise ValueError('Published dataset must be an array of row objects')
    ids = Counter(r['id'] for r in rows if isinstance(r.get('id'), str) and r['id'].strip())
    # Mirrors script.js enrichContracts' DECP buyer/contract identity scope.
    identities = Counter((r['buyerSiret'], r['contractId']) for r in rows
                         if isinstance(r.get('buyerSiret'), str) and r['buyerSiret']
                         and isinstance(r.get('contractId'), str) and r['contractId'])
    counts = {
        'rows': len(rows),
        'amounts': histogram(['missing', 'null', 'zero_declared', 'negative', 'positive', 'non_numeric']),
        'currency': histogram(['missing', 'invalid_syntax', 'declared', 'legacy_ui_default_eur']),
        'dates': {k: histogram(['missing', 'invalid', 'valid']) for k in ('date', 'publicationDate')},
        'text': {k: histogram(['empty', 'placeholder', 'identifier_only', 'non_text', 'present']) for k in ('description', 'buyer', 'supplier')},
        'source_urls': histogram(['missing', 'invalid', 'present']),
        'dataStatus': histogram(['verified', 'unverified', 'synthetic', 'missing', 'other']),
        'record_ids': {'missing_or_invalid': 0, 'duplicate_groups': sum(n > 1 for n in ids.values()),
                       'duplicate_rows': sum(n for n in ids.values() if n > 1),
                       'duplicate_excess': sum(n - 1 for n in ids.values() if n > 1)},
        'conflict_exclusions': histogram(['initial', 'modification', 'identity_ambiguous', 'any']),
        'review_rows': 0,
    }
    queue = []
    for row in rows:
        reasons = []
        category = amount_category(row)
        counts['amounts'][category] += 1
        if category != 'positive':
            reasons.append('amount_' + category)
        currency = row.get('currency')
        missing_currency = currency is None or (isinstance(currency, str) and not currency.strip())
        category = 'missing' if missing_currency else 'declared' if isinstance(currency, str) and re.fullmatch('[A-Z]{3}', currency) else 'invalid_syntax'
        counts['currency'][category] += 1
        if category != 'declared':
            reasons.append('currency_' + category)
        if not currency and not row.get('assessmentMode'):
            counts['currency']['legacy_ui_default_eur'] += 1
        for field in counts['dates']:
            category = date_category(row.get(field), timestamp=field == 'publicationDate')
            counts['dates'][field][category] += 1
            if category != 'valid':
                reasons.append(field + '_' + category)
        for field in counts['text']:
            category = text_category(row.get(field), field)
            counts['text'][field][category] += 1
            if category != 'present':
                reasons.append(field + '_' + category)
        category = source_category(row.get('source'))
        counts['source_urls'][category] += 1
        if category != 'present':
            reasons.append('source_' + category)
        status = row.get('dataStatus')
        category = status if isinstance(status, str) and status in ('verified', 'unverified', 'synthetic') else 'missing' if status is None or status == '' else 'other'
        counts['dataStatus'][category] += 1
        if category != 'verified':
            reasons.append('dataStatus_' + category)
        rid = row.get('id')
        if not isinstance(rid, str) or not rid.strip():
            counts['record_ids']['missing_or_invalid'] += 1
            reasons.append('record_id_missing_or_invalid')
            rid = None
        elif ids[rid] > 1:
            reasons.append('duplicate_record_id')
        identity = (row.get('buyerSiret'), row.get('contractId'))
        ambiguous = bool(row.get('identityAmbiguous')) or (
            row.get('dataFamily') == 'decp' and all(isinstance(v, str) and v for v in identity)
            and identities[identity] > 1)
        flags = {'initial': bool(row.get('initialConflicts')), 'modification': bool(row.get('modificationConflicts')), 'identity_ambiguous': ambiguous}
        for field, flagged in flags.items():
            if flagged:
                counts['conflict_exclusions'][field] += 1
                reasons.append('conflict_' + field)
        counts['conflict_exclusions']['any'] += int(any(flags.values()))
        if reasons:
            queue.append({'id': rid, 'dataset_path': dataset_path, 'reasons': reasons})
    counts['review_rows'] = len(queue)
    return counts, queue


def inventory(root):
    aggregates, queue = {}, []
    for key, path in published_datasets(root):
        rows = json.loads((root / path).read_text(encoding='utf-8'))
        counts, reviews = audit_rows(rows, path)
        aggregates[key] = {'path': path, **counts}
        queue.extend(reviews)
    return {'schema_version': 1, 'notes': NOTES, 'datasets': aggregates}, queue


def write_queue(directory, queue):
    """Atomic mode-0600 queue in a mode-0700 directory, never follows file links."""
    directory = Path(directory).expanduser()
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    if directory.is_symlink():
        raise ValueError('Review directory must not be a symlink')
    directory.chmod(0o700)
    fd, name = tempfile.mkstemp(prefix='.review-', dir=directory)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            for item in queue:
                stream.write(json.dumps(item, ensure_ascii=True, allow_nan=False) + '\n')
        os.replace(name, directory / 'review.jsonl')
    finally:
        if os.path.exists(name):
            os.unlink(name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT, help='Repository root')
    parser.add_argument('--review-dir', type=Path, default=DEFAULT_QUEUE, help='Private queue directory (replaced each run)')
    parser.add_argument('--output', help='Explicit public-safe aggregate JSON destination; - for stdout')
    args = parser.parse_args()
    report, queue = inventory(args.root)
    if args.output and args.output != '-' and Path(args.output).resolve() == (args.review_dir.expanduser() / 'review.jsonl').resolve():
        parser.error('Aggregate output cannot overwrite the private review queue')
    write_queue(args.review_dir, queue)
    if args.output:
        encoded = json.dumps(report, indent=2, ensure_ascii=True, allow_nan=False) + '\n'
        if args.output == '-':
            print(encoded, end='')
        else:
            Path(args.output).write_text(encoded, encoding='utf-8')
    else:
        print(f"Audited {len(report['datasets'])} datasets / {sum(d['rows'] for d in report['datasets'].values())} rows; {len(queue)} private review rows. Not validated contracts. No aggregate JSON written.")


if __name__ == '__main__':
    main()
