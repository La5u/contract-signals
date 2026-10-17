#!/usr/bin/env python3
"""Research only: related-party candidates R1–R3 from the Ukrainian company register (ЄДР).

Fixed in research/calibration/ukraine-candidate-indicators-plan.md, part 5, before any was computed.
  ids      collect the company codes (EDRPOU) of bidders and winners in the given cohorts
  extract  stream the register file (UO.zip, open data) and keep only those companies
  run      compute R1–R3 for a cohort and apply the plan's method and decision rule

Names are compared in memory. The register extract stays in the private cache
(~/.cache/contract-signals/ukraine-edr/); only yes/no statuses and aggregate results are written
elsewhere. Changes no score, weight or dataset.
"""
import argparse
import gzip
import importlib.util
import json
import re
import zipfile
from datetime import date
from pathlib import Path
from xml.etree.ElementTree import iterparse

ROOT = Path(__file__).resolve().parents[1]
CACHE = Path.home() / '.cache/contract-signals'
SNAPSHOT = CACHE / 'ukraine-edr/2026-10-13'
CANDIDATES = ['R1 shared-owner', 'R2 official-owner', 'R3 young-winner']
YOUNG_DAYS = 365


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ci = load('ukraine_candidate_indicators', 'tools/ukraine-candidate-indicators.py')
pp = ci.pp

# Latin capitals that look like Cyrillic ones, as typed in some records.
LOOKALIKE = str.maketrans('ABCEHIKMOPTXY', 'АВСЕНІКМОРТХУ')
FULL_NAME = re.compile(r"[А-ЯҐЄІЇ'\-]+(?: [А-ЯҐЄІЇ'\-]+){2}")


def norm_name(text):
    t = str(text or '').upper().translate(LOOKALIKE)
    t = re.sub(r"[’ʼ`‘´]", "'", t)
    t = re.sub(r'\s*-\s*', '-', t)
    return re.sub(r'\s+', ' ', t).strip()


def person(text):
    """A person's full normalised name (surname, first name, patronymic), or None.

    Register entries read 'NAME; share …', 'NAME - керівник' or 'Name; громадянство: …'."""
    head = re.split(r'\s+-\s+', str(text or '').split(';')[0])[0]
    name = norm_name(head)
    return name if FULL_NAME.fullmatch(name) else None


def edrpou(value):
    v = str(value or '').strip()
    return v if re.fullmatch(r'\d{8}', v) else None


def iso(ddmmyyyy):
    m = re.match(r'\s*(\d{2})\.(\d{2})\.(\d{4})', str(ddmmyyyy or ''))
    return f'{m[3]}-{m[2]}-{m[1]}' if m else None


def cohort_tenders(cohort, cache):
    """(row, tender record or None) for every cohort row, from the cache only."""
    vc = load('verdict_cohort', 'tools/build-ukraine-verdict-cohort.py')
    f = vc.bc.Fetcher(Path(cache).expanduser(), budget=0, network=False, prior=0, opener=vc.opener)
    for row in json.loads(gzip.open(cohort).read())['rows']:
        r = f.fetch(vc.bc.tender_url(row['procedureId']))
        yield row, (json.loads(r['body'])['data'] if r and r['status'] == 200 else None)


def winner_of(row):
    ids = row.get('supplierIds') or []
    return ids[0] if len(ids) == 1 else None


def collect_ids(cohorts, cache):
    out = set()
    for cohort in cohorts:
        for row, tender in cohort_tenders(cohort, cache):
            w = winner_of(row)
            if w and edrpou(w.get('id')):
                out.add(w['id'])
            for bid in (tender or {}).get('bids') or []:
                for t in bid.get('tenderers') or []:
                    code = edrpou((t.get('identifier') or {}).get('id'))
                    if code:
                        out.add(code)
    return out


def extract(zip_path, wanted):
    """Register entries for the wanted codes: registration dates, people (founders, beneficial
    owners, signers) by full name, and founders that are legal entities by code."""
    out = {}
    with zipfile.ZipFile(zip_path) as z, z.open('UO.xml') as f:
        for _, el in iterparse(f, events=('end',)):
            if el.tag != 'SUBJECT':
                continue
            code = edrpou(el.findtext('EDRPOU'))
            if code in wanted:
                people, codes = set(), set()
                for path in ('FOUNDERS/FOUNDER', 'BENEFICIARIES/BENEFICIARY', 'SIGNERS/SIGNER'):
                    for x in el.iterfind(path):
                        name = person(x.text)
                        if name:
                            people.add(name)
                        if path.startswith('FOUNDERS'):
                            parts = [p.strip() for p in (x.text or '').split(';')]
                            if len(parts) > 1 and edrpou(parts[1]):
                                codes.add(parts[1])
                e = out.setdefault(code, {'registered': [], 'states': [], 'people': [], 'founderCodes': []})
                e['registered'].append(iso(el.findtext('REGISTRATION')))
                e['states'].append(el.findtext('STAN'))
                e['people'] = sorted(set(e['people']) | people)
                e['founderCodes'] = sorted(set(e['founderCodes']) | codes)
            el.clear()
    return out


def shared(token_sets, too_few):
    """As part 3: known matches win; a missing party cannot turn a potential match into clear."""
    if too_few:
        return False
    seen, missing = set(), False
    for tokens in token_sets:
        if tokens is None:
            missing = True
            continue
        if seen & tokens:
            return True
        seen |= tokens
    return None if missing else False


def party_tokens(code, published_name, register):
    """A bidder's people and codes; None when the register (or the published name) cannot tell."""
    if edrpou(code):
        e = register.get(code)
        if e is None:
            return None
        return {('person', p) for p in e['people']} | {('code', c) for c in e['founderCodes']} | {('code', code)}
    name = person(published_name)  # an individual entrepreneur is the person
    return {('person', name)} if name else None


def features(row, tender, register):
    out = dict.fromkeys(CANDIDATES)
    if tender is None:
        return out
    # R1: bidders on the awarded lot sharing an owner, manager or founder, or one founding another.
    scope = ci.awarded_lot_bids(row, tender)
    if scope is not None:
        selected, bidders, unidentified = scope
        too_few = len(selected) < 2 or (not unidentified and len(bidders) < 2)
        sets = [party_tokens(code, tenderer.get('name'), register) for code, (_, _, tenderer) in bidders.items()]
        if unidentified:
            sets.append(None)
        out['R1 shared-owner'] = shared(sets, too_few)
    # R2: the buyer's named contact person is an owner or manager of the winner (or is the winner).
    w = winner_of(row)
    contact = person(((tender.get('procuringEntity') or {}).get('contactPoint') or {}).get('name'))
    if w and contact:
        award = next((a for a in tender.get('awards') or [] if a.get('id') == row.get('awardId')), {})
        names = [s.get('name') for s in award.get('suppliers') or []]
        tokens = party_tokens(w.get('id'), names[0] if len(names) == 1 else None, register)
        out['R2 official-owner'] = None if tokens is None else ('person', contact) in tokens
    # R3: the winner (a legal entity) registered less than a year before the tender was created.
    if w and edrpou(w.get('id')) and w['id'] in register and row.get('tenderCreated'):
        dates = {d for d in register[w['id']]['registered'] if d}
        if len(dates) == 1:
            days = (date.fromisoformat(row['tenderCreated'][:10]) - date.fromisoformat(dates.pop())).days
            out['R3 young-winner'] = 0 <= days < YOUNG_DAYS if days >= 0 else None
    return out


def coverage(feature_rows, positive):
    """Share of rows where each candidate is known, labelled vs comparison (plan: report bias)."""
    out = {}
    for k in CANDIDATES:
        res = {}
        for group, test in (('labelled', lambda r: r['label'] in positive), ('comparison', lambda r: r['label'] == 'comparison')):
            rows = [r for r in feature_rows if test(r) and r.get('procedure') not in pp.NON_COMPETITIVE]
            known = sum(r['checks'][k]['status'] != 'unknown' for r in rows)
            res[group] = {'rows': len(rows), 'known': known, 'share': round(known / len(rows), 3) if rows else None}
        out[k] = res
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = p.add_subparsers(dest='cmd', required=True)
    a = sub.add_parser('ids')
    a.add_argument('cohorts', nargs='+')
    a.add_argument('--cache', default=str(CACHE / 'labels/verdict-cohort'))
    a.add_argument('--out', default=str(SNAPSHOT / 'wanted-codes.json'))
    b = sub.add_parser('extract')
    b.add_argument('--register', default=str(SNAPSHOT / 'UO.zip'))
    b.add_argument('--ids', default=str(SNAPSHOT / 'wanted-codes.json'))
    b.add_argument('--out', default=str(SNAPSHOT / 'extract.json.gz'))
    c = sub.add_parser('run')
    c.add_argument('--cohort', required=True)
    c.add_argument('--cache', default=str(CACHE / 'labels/verdict-cohort'))
    c.add_argument('--extract', default=str(SNAPSHOT / 'extract.json.gz'))
    c.add_argument('--features', required=True, help='write per-row statuses here (yes/no only)')
    c.add_argument('--only', help='keep only the row IDs of this rows file (e.g. one row per case)')
    c.add_argument('--positive-labels', default=','.join(pp.POSITIVE))
    c.add_argument('--json', help='write full results here')
    args = p.parse_args(argv)

    if args.cmd == 'ids':
        codes = sorted(collect_ids(args.cohorts, args.cache))
        Path(args.out).write_text(json.dumps({'cohorts': args.cohorts, 'codes': codes}) + '\n')
        print(f'{len(codes)} company codes from {len(args.cohorts)} cohort(s) → {args.out}')
    elif args.cmd == 'extract':
        wanted = set(json.loads(Path(args.ids).read_text())['codes'])
        register = extract(args.register, wanted)
        with gzip.open(args.out, 'wt', encoding='utf-8') as f:
            json.dump(register, f, ensure_ascii=False)
        print(f'{len(register)} of {len(wanted)} wanted companies found in the register → {args.out}')
    else:
        register = json.loads(gzip.open(args.extract, 'rt', encoding='utf-8').read())
        positive = tuple(args.positive_labels.split(','))
        rows = []
        for row, tender in cohort_tenders(args.cohort, args.cache):
            feats = features(row, tender, register)
            rows.append({'id': row['id'], 'procedureId': row['procedureId'], 'procedure': row.get('procedure'), 'group': row.get('group'),
                         'label': row['label'], 'finality': row.get('finality'), 'buyerId': row.get('buyerId'),
                         'checks': {k: {'status': ci.status(feats[k]), 'points': None} for k in CANDIDATES}})
        if args.only:
            data = json.loads(Path(args.only).read_text())
            keep = {r['id'] for r in (data['rows'] if isinstance(data, dict) else data)}
            rows = [r for r in rows if r['id'] in keep]
        Path(args.features).write_text(json.dumps(rows) + '\n')
        cov = coverage(rows, positive)
        ci.CANDIDATES = CANDIDATES
        loaded, skipped = pp.load_rows(args.features, None, positive)
        results = ci.evaluate(loaded)
        positives = [r for r in loaded if 'combined' in r['groups']]
        print(f"{len(positives)} eligible positive rows ({len({r['buyer'] for r in positives})} buyers); "
              f"{sum('comparison' in r['groups'] for r in loaded)} comparison rows; left out (non-competitive): {skipped}.")
        print('Coverage (rows with a known status, competitive): ' + '; '.join(
            f"{k}: labelled {v['labelled']['share']}, comparison {v['comparison']['share']}" for k, v in cov.items()) + '\n')
        print(ci.table(results))
        if args.json:
            Path(args.json).write_text(json.dumps({'plan': 'research/calibration/ukraine-candidate-indicators-plan.md#part-5-related-parties-from-the-company-register-fixed-2026-10-17-before-any-was-computed',
                                                   'register': 'data.gov.ua a1799820-195b-4982-8141-6e84f58103e7, UO.zip 2026-10-13',
                                                   'coverage': cov, 'results': results}, indent=1) + '\n')


if __name__ == '__main__':
    main()
