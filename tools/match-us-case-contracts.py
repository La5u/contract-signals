#!/usr/bin/env python3
"""Research only: match US label cases to FPDS awards in the slim yearly copies (tools/import-us-fpds.py).

Reads us-labels/sol-cases-1.tsv and us-labels/cases/<case_id>/contracts.json (tools/research-us-case-contracts.py)
and writes us-labels/matches/:

- `raw-id-matches.tsv`: every award whose PIID, parent IDV PIID or solicitation number equals a number named for
  the case (compared without case, spaces and dashes). `matched_on` says which field.
- `raw-name-matches.tsv`: awards whose recipient or parent recipient name equals a company named in the case
  (upper case, punctuation and legal suffixes removed), or whose UEI/DUNS was given, within the case's conduct
  years plus one fiscal year either side (all years when none are stated).
- `id-matches.tsv`, `name-matches.tsv`: the raw files filtered. A parent-IDV or solicitation match is kept only
  when the awardee is one of the case's companies (a schedule or IDV number otherwise pulls in every vendor's
  orders); a name match only at one of the case's agencies (case row and contracts.json); placeholder names
  ("Company A", "co-conspirator") never match. `--filter-only` reruns this step without scanning FPDS.
- `summary.tsv`: per case, numbers named, numbers found, awards by number and by name after filtering.

One row per award and case; amounts are the award's summed transaction obligations, shown for review only. This
is a candidate list: name matches in particular need review before any award counts as a label.
"""
import argparse
import csv
import json
import os
import re
import sqlite3
from collections import defaultdict
from pathlib import Path

CACHE = Path(os.environ.get('XDG_CACHE_HOME', str(Path.home() / '.cache'))) / 'contract-signals'
SUFFIXES = {'INC', 'INCORPORATED', 'LLC', 'L L C', 'LLP', 'LP', 'LTD', 'LIMITED', 'CO', 'COMPANY', 'CORP',
            'CORPORATION', 'PLLC', 'PC', 'PLC', 'GMBH', 'AG', 'SA', 'THE'}
AWARD_COLS = ['contract_award_unique_key', 'award_id_piid', 'parent_award_id_piid', 'awarding_agency_code',
              'awarding_sub_agency_code', 'awarding_office_code', 'recipient_name', 'recipient_uei', 'recipient_duns',
              'recipient_parent_name']
AGENCY_ALIASES = {'NASA': '080', 'USAID': '072', 'DOD': '097', 'VA': '036', 'GSA': '047', 'DHS': '070', 'DOT': '069',
                  'DOE': '089', 'USDA': '012', 'EPA': '068', 'HHS': '075', 'DOJ': '015', 'NSF': '049',
                  'AGENCY FOR INTERNATIONAL DEVELOPMENT': '072', 'US AGENCY FOR INTERNATIONAL DEVELOPMENT': '072',
                  'NATIONAL AERONAUTICS AND SPACE ADMINISTRATION': '080'}
PLACEHOLDER = re.compile(r'^(CO CONSPIRATOR|COMPANY|BUSINESS|CONTRACTOR|ENTITY|FIRM|SUBCONTRACTOR)( [A-Z0-9]{1,2})?$|CONSPIRATOR')
SUMMARY = ('min(action_date), max(action_date), sum(federal_action_obligation), count(*), '
           "max(case when modification_number = '0' then number_of_offers_received end), "
           "max(case when modification_number = '0' then extent_competed_code end)")
OUT_COLS = ['case_id', 'matched_on', 'matched_value'] + AWARD_COLS + ['first_action', 'last_action', 'obligated',
                                                                       'transactions', 'offers', 'extent_competed']


def norm_id(v):
    return re.sub(r'[\s\-_/.]', '', (v or '').upper())


def norm_name(v):
    words = re.sub(r'[^A-Z0-9 ]', ' ', (v or '').upper().replace('&', ' AND ')).split()
    while words and words[-1] in SUFFIXES:
        words.pop()
    while words and words[0] == 'THE':
        words.pop(0)
    return ' '.join(words)


def usable_name(v):
    n = norm_name(v)
    return len(n) >= 4 and not PLACEHOLDER.search(n)


def agency_codes(texts, names):
    """FPDS agency codes for free-text agency names: exact (normalised) name or a known abbreviation."""
    out = set()
    for t in texts:
        for part in re.split(r'[;,/]| and the ', t or ''):
            n = norm_name(re.sub(r'^U ?S ', '', norm_name(part)))
            n = re.sub(r'^(UNITED STATES|US) ', '', n)
            if n in AGENCY_ALIASES:
                out.add(AGENCY_ALIASES[n])
            out |= names.get(n, set())
            out |= names.get(n.replace('DEPT ', 'DEPARTMENT OF '), set())
    return out


def filter_matches(out, cases, db_dir):
    names = defaultdict(set)
    for path in sorted(db_dir.glob('fy*.sqlite'))[-1:]:
        db = sqlite3.connect(f'file:{path}?mode=ro', uri=True)
        for code, description in db.execute("SELECT code, description FROM codes WHERE field = 'awarding_agency_code'"):
            names[norm_name(description)].add(code)
        db.close()
    agencies = {cid: agency_codes(c['agencies'], names) for cid, c in cases.items()}
    kept = {}
    for name in ('id-matches.tsv', 'name-matches.tsv'):
        rows = []
        with (out / f'raw-{name}').open(newline='') as f:
            for r in csv.DictReader(f, delimiter='\t'):
                c = cases.get(r['case_id'])
                if not c:
                    continue
                awardee = {norm_name(r['recipient_name']), norm_name(r['recipient_parent_name'])} & c['names']
                if name == 'id-matches.tsv':
                    ok = r['matched_on'] == 'award_id_piid' or bool(awardee)
                elif r['matched_on'] == 'name':
                    ok = r['matched_value'] in c['names'] and r['awarding_agency_code'] in agencies[r['case_id']]
                else:
                    ok = r['awarding_agency_code'] in agencies[r['case_id']] or not agencies[r['case_id']]
                if ok:
                    rows.append(r)
        with (out / name).open('w', newline='') as f:
            w = csv.DictWriter(f, OUT_COLS, delimiter='\t', extrasaction='ignore')
            w.writeheader()
            w.writerows(rows)
        kept[name] = rows
    with (out / 'summary.tsv').open('w', newline='') as f:
        w = csv.writer(f, delimiter='\t')
        w.writerow(['case_id', 'researched', 'numbers_named', 'numbers_found', 'awards_by_number', 'awards_by_name',
                    'agencies', 'names'])
        for cid, c in cases.items():
            by_number = [r for r in kept['id-matches.tsv'] if r['case_id'] == cid]
            w.writerow([cid, int(c['researched']), len(c['ids']), len({r['matched_value'] for r in by_number}),
                        len(by_number), sum(1 for r in kept['name-matches.tsv'] if r['case_id'] == cid),
                        ','.join(sorted(agencies[cid])), '; '.join(sorted(c['names']))])


def years(text):
    found = [int(y) for y in re.findall(r'(?:19|20)\d\d', text or '')]
    if not found:
        return None
    hi = 2026 if re.search(r'onward|present|ongoing', text or '', re.I) else max(found)
    return min(found) - 1, hi + 2  # fiscal years: conduct year, one either side (FY = calendar year + 1 from Oct)


def load_cases(base):
    rows = list(csv.reader((base / 'sol-cases-1.tsv').open(), delimiter='\t'))
    header = rows[0]
    cases = {}
    for r in rows[1:]:
        if not r or not r[0].strip():
            continue
        row = dict(zip(header, r))
        case = {'row': row, 'ids': set(), 'names': set(), 'ueis': set(), 'duns': set(),
                'years': years(row.get('conduct_years'))}
        case['agencies'] = set(row.get('federal_agency', '').split(';'))
        for n in (row.get('defendant_companies') or '').split(';'):
            if usable_name(n):
                case['names'].add(norm_name(n))
        for n in (row.get('contract_ids') or '').split(';'):
            if norm_id(n):
                case['ids'].add(norm_id(n))
        path = base / 'cases' / r[0] / 'contracts.json'
        case['researched'] = path.exists()
        if path.exists():
            data = json.loads(path.read_text())
            for c in data.get('contracts') or []:
                for key in ('id', 'parent_idv'):
                    if norm_id(c.get(key)):
                        case['ids'].add(norm_id(c.get(key)))
            for c in data.get('contracts') or []:
                case['agencies'].add(c.get('agency') or '')
            for c in data.get('companies') or []:
                if usable_name(c.get('name')):
                    case['names'].add(norm_name(c.get('name')))
                if (c.get('uei') or '').strip():
                    case['ueis'].add(c['uei'].strip().upper())
                if re.fullmatch(r'\d{9}', (c.get('duns') or '').strip()):
                    case['duns'].add(c['duns'].strip())
        cases[r[0]] = case
    return cases


def award_rows(db, where, params):
    cols = ', '.join(AWARD_COLS)
    return db.execute(f'SELECT {cols}, {SUMMARY} FROM tx WHERE contract_award_unique_key IN '
                      f'(SELECT contract_award_unique_key FROM tx WHERE {where}) GROUP BY contract_award_unique_key',
                      params).fetchall()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--labels', type=Path, default=CACHE / 'us-labels')
    ap.add_argument('--db', type=Path, default=CACHE / 'us-fpds/db')
    ap.add_argument('--filter-only', action='store_true', help='refilter the raw-*.tsv files without scanning FPDS')
    a = ap.parse_args()
    cases = load_cases(a.labels)
    out = a.labels / 'matches'
    if a.filter_only:
        filter_matches(out, cases, a.db)
        return
    by_id, by_name, by_uei, by_duns = defaultdict(set), defaultdict(set), defaultdict(set), defaultdict(set)
    for cid, c in cases.items():
        for v in c['ids']:
            by_id[v].add(cid)
        for v in c['names']:
            by_name[v].add(cid)
        for v in c['ueis']:
            by_uei[v].add(cid)
        for v in c['duns']:
            by_duns[v].add(cid)
    id_hits, name_hits, found_ids = {}, {}, defaultdict(set)
    for path in sorted(a.db.glob('fy*.sqlite')):
        fy = int(path.stem[2:])
        db = sqlite3.connect(f'file:{path}?mode=ro', uri=True)
        db.execute('CREATE TEMP TABLE ids (id TEXT PRIMARY KEY)')
        db.executemany('INSERT INTO temp.ids VALUES (?)', [(v,) for v in by_id])
        for field in ('award_id_piid', 'parent_award_id_piid', 'solicitation_identifier'):
            expr = f"replace(replace(replace(replace(upper({field}), '-', ''), ' ', ''), '/', ''), '.', '')"
            for r in award_rows(db, f'{expr} IN (SELECT id FROM temp.ids)', ()):
                award = dict(zip(AWARD_COLS + OUT_COLS[-6:], r))
                value = norm_id(award.get(field) if field != 'solicitation_identifier' else None)
                if field == 'solicitation_identifier':
                    value = norm_id(db.execute('SELECT solicitation_identifier FROM tx WHERE contract_award_unique_key = ? '
                                               'AND solicitation_identifier IS NOT NULL LIMIT 1',
                                               (award['contract_award_unique_key'],)).fetchone()[0])
                for cid in by_id.get(value, ()):
                    found_ids[cid].add(value)
                    key = (cid, award['contract_award_unique_key'])
                    if key not in id_hits:
                        id_hits[key] = dict(award, case_id=cid, matched_on=field, matched_value=value)
        raw_names = defaultdict(set)
        for (raw,) in db.execute('SELECT DISTINCT recipient_name FROM tx UNION SELECT DISTINCT recipient_parent_name FROM tx'):
            n = norm_name(raw)
            if n in by_name:
                raw_names[raw].add(n)
        db.execute('CREATE TEMP TABLE names (v TEXT PRIMARY KEY)')
        db.executemany('INSERT INTO temp.names VALUES (?)', [(v,) for v in raw_names])
        db.execute('CREATE TEMP TABLE codes (v TEXT PRIMARY KEY)')
        db.executemany('INSERT OR IGNORE INTO temp.codes VALUES (?)', [(v,) for v in list(by_uei) + list(by_duns)])
        hits = defaultdict(set)  # award key -> {(case, matched_on, value)}
        for key, name, parent, uei, puei, duns, pduns in db.execute(
                'SELECT DISTINCT contract_award_unique_key, recipient_name, recipient_parent_name, recipient_uei, '
                'recipient_parent_uei, recipient_duns, recipient_parent_duns FROM tx '
                'WHERE recipient_name IN temp.names OR recipient_parent_name IN temp.names '
                'OR recipient_uei IN temp.codes OR recipient_parent_uei IN temp.codes '
                'OR recipient_duns IN temp.codes OR recipient_parent_duns IN temp.codes'):
            for raw in (name, parent):
                for n in raw_names.get(raw, ()):
                    hits[key] |= {(cid, 'name', n) for cid in by_name[n]}
            for v in (uei, puei):
                hits[key] |= {(cid, 'uei', v) for cid in by_uei.get(v, ())}
            for v in (duns, pduns):
                hits[key] |= {(cid, 'duns', v) for cid in by_duns.get(v, ())}
        for key, matches in hits.items():
            matches = [m for m in matches if not cases[m[0]]['years']
                       or cases[m[0]]['years'][0] <= fy <= cases[m[0]]['years'][1]]
            if not matches:
                continue
            award = dict(zip(AWARD_COLS + OUT_COLS[-6:], award_rows(db, 'contract_award_unique_key = ?', (key,))[0]))
            for cid, matched_on, value in sorted(matches):
                if (cid, key) not in name_hits:
                    name_hits[(cid, key)] = dict(award, case_id=cid, matched_on=matched_on, matched_value=value)
        db.close()
        print(f'{path.name}: {len(id_hits)} awards by number, {len(name_hits)} by name so far', flush=True)
    out.mkdir(exist_ok=True)
    for name, hits in (('raw-id-matches.tsv', id_hits), ('raw-name-matches.tsv', name_hits)):
        with (out / name).open('w', newline='') as f:
            w = csv.DictWriter(f, OUT_COLS, delimiter='\t', extrasaction='ignore')
            w.writeheader()
            for key in sorted(hits):
                w.writerow(hits[key])
    filter_matches(out, cases, a.db)

if __name__ == '__main__':
    main()
