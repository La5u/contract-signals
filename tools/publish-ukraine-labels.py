#!/usr/bin/env python3
"""Prepare the Ukrainian label files for publication, in place (owner decision, 2026-10-14).

Run after any rebuild and before committing. For every label file under research/labels:
  - a positive label whose tender is not yet final keeps its label and gets a `finality_note`: under
    appeal, or decided under three months ago (by build-ukraine-verdict-cohort.classify_finality). The
    analysis leaves these tenders out, as before;
  - the status line says the file is published, with its caveats;
  - court-text snippets (`context`) and 10-digit individual tax numbers are removed.
Comparison rows and excluded verdicts are unchanged. Keep unredacted copies outside the repository.
"""
import argparse
import gzip
import importlib.util
import json
import re
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('builder', ROOT / 'tools' / 'build-ukraine-verdict-cohort.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)

ELIGIBLE = ('confirmed', 'presumed')
POSITIVE_ROW_LABELS = ('corruption', 'fraud', 'collusion')
NOTES = {
    'pending-appeal': {'conviction': 'convicted; under appeal, not final',
                       'collusion': 'AMCU decision upheld by a court; under appeal, not final'},
    'quashed': {'conviction': 'conviction quashed on appeal, retrial ordered; not final',
                'collusion': 'court decision quashed on appeal, retrial ordered; not final'},
    'too-recent': {'conviction': 'convicted less than three months before {day}; an appeal may still be filed, not final',
                   'collusion': 'AMCU decision upheld by a court less than three months before {day}; an appeal may still be filed, not final'},
}
PUBLISHED = ('Published by the owner on {day} so the indicator points can be checked against the court register; '
             'labels come from automatic scans, a model review and rule-based linking (20 of 20 sampled links correct), '
             'not from a court finding about the indicators. Labels not yet final carry a finality_note and are not used '
             'in the analysis. To contest a label, see research/labels/README.md')
INDIVIDUAL_ID = re.compile(r'^\d{10}$')


def note(finality, label, day):
    kind = 'collusion' if label in ('collusion', 'bid rigging (AMCU decision upheld)') else 'conviction'
    return NOTES[finality][kind].format(day=day) if finality in NOTES else None


def set_note(record, text):
    """Set the note, or drop one that no longer applies (the label became final). 1 if changed."""
    if record.get('finality_note') == text:
        return 0
    if text:
        record['finality_note'] = text
    elif 'finality_note' in record:
        del record['finality_note']
    else:
        return 0
    return 1


def verdict_file(data, today, day):
    """Verdict-level records: note each positive label whose tender is not final; drop notes that no longer apply."""
    records = data.get('verdicts')
    if not isinstance(records, list):
        return 0
    by_tender = defaultdict(list)
    for v in records:
        if v.get('tender_id_normalised'):
            by_tender[v['tender_id_normalised']].append(v)
    n = 0
    for v in records:
        if v.get('proposed_label') in builder.LABELS and v.get('tender_id_normalised'):
            text = note(builder.classify_finality(by_tender[v['tender_id_normalised']], today), v['proposed_label'], day)
            n += set_note(v, text)
    return n


def row_file(data, day):
    """Cohort tenders and rows, amendment rows: note positive labels that are not final."""
    lists = [data.get('rows'), data.get('tenders')] if isinstance(data, dict) else [data]
    n = 0
    for r in (r for rows in lists if isinstance(rows, list) for r in rows):
        if isinstance(r, dict) and r.get('label') in POSITIVE_ROW_LABELS:
            n += set_note(r, note(r.get('finality'), r['label'], day))
    return n


def scrub(x):
    """Remove court-text snippets and individual tax numbers anywhere in the file."""
    n = 0
    if isinstance(x, dict):
        if isinstance(x.get('context'), str):
            del x['context']
            n += 1
        for k, v in list(x.items()):
            if k in ('supplier_code', 'bidder_code') and isinstance(v, str) and INDIVIDUAL_ID.match(v):
                x[k] = 'individual tax number (masked)'
                n += 1
            elif k == 'bidder_codes' and isinstance(v, list):
                x[k] = ['individual tax number (masked)' if isinstance(c, str) and INDIVIDUAL_ID.match(c) else c for c in v]
            else:
                n += scrub(v)
    elif isinstance(x, list):
        n += sum(scrub(v) for v in x)
    return n


def mark_published(data, day):
    if not isinstance(data, dict):
        return
    status = data.get('status') or (data.get('summary') or {}).get('status')
    note = PUBLISHED.format(day=day)
    if isinstance(status, str) and note not in status:
        data['status'] = re.sub(r';?\s*not (?:yet )?owner-approved', '', status) + '. ' + note


def process(path, today, day):
    gz = path.suffix == '.gz'
    text = gzip.open(path, 'rt', encoding='utf-8').read() if gz else path.read_text(encoding='utf-8')
    data = json.loads(text)
    counts = {'noted': (verdict_file(data, today, day) if isinstance(data, dict) else 0) + row_file(data, day), 'scrubbed': scrub(data)}
    mark_published(data, day)
    out = json.dumps(data, ensure_ascii=False, indent=None if gz else 1) + ('' if gz else '\n')
    if data != json.loads(text):  # rewrite only real changes, never just the formatting
        if gz:
            with gzip.open(path, 'wt', encoding='utf-8', compresslevel=9) as f:
                f.write(out)
        else:
            path.write_text(out, encoding='utf-8')
    return counts


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('files', nargs='*', help='default: research/labels/ukraine-*.json[.gz]')
    p.add_argument('--today', default=date.today().isoformat(), help='finality reference day (YYYY-MM-DD)')
    a = p.parse_args(argv)
    today = date.fromisoformat(a.today)
    files = [Path(f) for f in a.files] or sorted((ROOT / 'research' / 'labels').glob('ukraine-*.json*'))
    for f in files:
        print(f.name, process(f, today, a.today))


if __name__ == '__main__':
    main()
