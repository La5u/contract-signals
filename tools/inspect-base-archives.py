#!/usr/bin/env python3
"""Inspect ZIP directories and at most 64 KiB of JSON per annual BASE archive.

No whole extraction, full-file hash, filtering, conversion or network access.
Retains schema/type/shape aggregates for at most three initial records per year,
never actual contract IDs, party names, NIF values or raw record text.
"""
import argparse
import codecs
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
CACHE = Path(os.environ.get('XDG_CACHE_HOME', str(Path.home() / '.cache'))) / 'contract-signals' / 'base-archives'
PREFIX_BYTES, SAMPLE_ROWS = 65536, 3
REPORT = ROOT / 'data/portugal-base-inspection.json'


def shape(value):
    if value in (None, ''):
        return 'empty'
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return 'json-number'
    if isinstance(value, str):
        if re.fullmatch(r'\d{2}/\d{2}/\d{4}', value):
            return 'DD/MM/YYYY-shaped text'
        if re.fullmatch(r'\d{2}-\d{2}-\d{4}', value):
            return 'DD-MM-YYYY-shaped text'
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
            return 'YYYY-MM-DD-shaped text'
        if re.fullmatch(r'\d+', value):
            return 'digit-only text'
    return type(value).__name__


def sample_prefix(prefix):
    text = codecs.getincrementaldecoder('utf-8-sig')().decode(prefix, final=False)
    position = len(text) - len(text.lstrip())
    if not text[position:].startswith('['):
        raise ValueError('Expected a JSON array; no alternate format inferred.')
    position += 1
    rows, decoder = [], json.JSONDecoder()
    while len(rows) < SAMPLE_ROWS:
        while position < len(text) and text[position] in ' \r\n\t,':
            position += 1
        try:
            row, end = decoder.raw_decode(text, position)
        except json.JSONDecodeError:
            break  # Prefix can end inside a later record; never read the whole member.
        if not isinstance(row, dict):
            raise ValueError('Expected record objects.')
        rows.append(row)
        position = end
    return rows


def summarize(rows):
    fields = []
    for key in sorted({key for row in rows for key in row}):
        values = [row.get(key) for row in rows]
        entry = {'field': key, 'types': sorted({type(value).__name__ for value in values}),
                 'nonemptySampleRows': sum(value not in (None, '', [], {}) for value in values),
                 'shapes': sorted({shape(value) for value in values})}
        if all(value is None or isinstance(value, (int, float)) for value in values):
            entry['zeroSampleRows'] = sum(value == 0 for value in values if value is not None)
        if any(isinstance(value, list) for value in values):
            items = [item for value in values if isinstance(value, list) for item in value]
            entry['listItemTypes'] = sorted({type(item).__name__ for item in items})
            # Structured property names only, never party identifiers/names.
            entry['listObjectFields'] = sorted({k for item in items if isinstance(item, dict) for k in item if not re.search(r'\d{5}', k)})
            if key in ('adjudicante', 'adjudicatarios', 'concorrentes', 'adjudicatarioPMEs'):
                entry['nifNameShapedStringItems'] = sum(isinstance(item, str) and bool(re.match(r'^\s*\d{9}\s*[-–]\s*\S', item)) for item in items)
        fields.append(entry)
    return fields


def inspect():
    report = {'schemaVersion': 1, 'inspectedAt': datetime.now(timezone.utc).isoformat(),
              'scope': 'ZIP directory plus first 64 KiB of each JSON member; at most three initial records per year. Not representative and not the selected-buyer cohort.',
              'limits': {'maxPrefixBytesPerArchive': PREFIX_BYTES, 'maxSampleRowsPerArchive': SAMPLE_ROWS, 'networkRequests': 0},
              'archiveProvenance': 'data/portugal-base-downloads.json', 'archives': []}
    for year in (2024, 2025, 2026):
        filename = f'contratos{year}.zip'
        with zipfile.ZipFile(CACHE / filename) as archive:
            members = archive.infolist()
            expected = f'Contratos{year}.json'
            selected = [member for member in members if member.filename == expected]
            if len(selected) != 1 or selected[0].flag_bits & 1 or selected[0].file_size > 512 * 1024 * 1024:
                raise ValueError('Unexpected, encrypted or oversized archive member; inspection stopped.')
            member = selected[0]
            with archive.open(member) as stream:
                prefix = stream.read(PREFIX_BYTES)
            rows = sample_prefix(prefix)
            report['archives'].append({'year': year, 'filename': filename, 'memberCount': len(members),
                                       'jsonMember': member.filename, 'compressedMemberBytes': member.compress_size,
                                       'uncompressedMemberBytes': member.file_size, 'prefixBytesRead': len(prefix),
                                       'sampleRows': len(rows), 'fields': summarize(rows)})
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true', help='Retain only aggregate schema inspection in the repository.')
    args = parser.parse_args()
    report = inspect()
    text = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    if args.write:
        REPORT.write_text(text)
        print(f'Wrote {REPORT.relative_to(ROOT)}: bounded schema sample only, no record values.')
    else:
        print(text)


if __name__ == '__main__':
    main()
