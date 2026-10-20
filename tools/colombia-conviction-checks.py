#!/usr/bin/env python3
"""Research only: Colombian checks CO1-CO5 against conviction-linked SECOP I contracts.

Plan: research/calibration/colombia-convictions-plan.md (fixed before this ran). Inputs: conviction records
(~/.cache/contract-signals/colombia-leads/sol/out-1.jsonl) and the entity-year SECOP I downloads of
tools/fetch-colombia-secop1.py. A judgment's contract resolves when exactly one record of that entity and
signing year carries the same contract number (digits, ignoring a trailing year); several candidates are
broken only by a clearly better object match, otherwise the contract is ambiguous and unused.
Changes no score, weight or dataset.
"""
import argparse
import gzip
import importlib.util
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('pp', ROOT / 'tools/propose-indicator-points.py')
pp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pp)
cspec = importlib.util.spec_from_file_location('cand', ROOT / 'tools/ukraine-candidate-indicators.py')
cand = importlib.util.module_from_spec(cspec)
cspec.loader.exec_module(cand)

LEADS = Path.home() / '.cache/contract-signals/colombia-leads/sol/out-1.jsonl'
CACHE = Path.home() / '.cache/contract-signals/colombia-secop1'
INCREASE, SHARE, CONC_SHARE, CONC_MIN = 0.20, 0.05, 0.6, 10
CHECKS = ['CO1 direct award', 'CO2 amount increase > 20 %', 'CO3 term extension', 'CO4 buyer share >= 5 %', 'CO5 concentration',
          'U2 repeated direct award', 'N1 December signature', 'N2 weekend signature', 'N3 long duration >= 36 months',
          'N4 supplier dependence >= 25 %']   # U/N: research/calibration/untested-checks-plan.md
STOP = set('de la el los las del y en para por con a al su sus que se un una prestar servicios contrato'.split())


def num(x):
    try:
        return float(str(x).replace(',', ''))
    except (TypeError, ValueError):
        return None


def contract_digits(s, year):
    """Main number of a contract reference: '152 de 2013' -> '152'; 'CPS No 1523 DE 2013' -> '1523'; '11522013' -> '1152'."""
    s = str(s or '').upper()
    s = re.sub(rf'\s*(?:DE|DEL|-|/)\s*{year}\b', ' ', s)
    groups = re.findall(r'\d+', s)
    if not groups:
        return None
    g = max(groups, key=len)
    if len(g) > 4 and g.endswith(str(year)):
        g = g[:-4]
    return g.lstrip('0') or '0'


def words(s):
    return {w for w in re.findall(r'[a-záéíóúñ]{4,}', str(s or '').lower()) if w not in STOP}


def signed_year(r):
    y = str(r.get('anno_firma_del_contrato') or '')
    return int(y) if y.isdigit() else None


def load_years():
    """SECOP I (historical and 2018+) and SECOP II files of an entity-year are merged; uids are unique per table."""
    data = defaultdict(dict)
    for p in sorted(CACHE.glob('*.json.gz')):
        nit, year = p.name.split('.')[0].split('-')
        for r in json.loads(gzip.decompress(p.read_bytes())):
            if signed_year(r) == int(year) and r.get('uid'):
                data[(nit, int(year))].setdefault(r['uid'], r)
    return {k: list(v.values()) for k, v in data.items()}


def resolve(records, years):
    labelled, report = [], Counter()
    for case, r in enumerate(records):
        nit = ''.join(ch for ch in str(r.get('entity_nit') or '') if ch.isdigit())[:9]
        for c in r.get('contracts') or []:
            year = c.get('year')
            if not (nit and c.get('number') and isinstance(year, int) and year >= 2010):
                continue
            rows = years.get((nit, year))
            if rows is None:
                report['entity-year not downloaded'] += 1
                continue
            want = contract_digits(c['number'], year)
            cands = [x for x in rows if contract_digits(x.get('numero_del_contrato'), year) == want]
            if len(cands) > 1:
                scored = sorted(((len(words(c.get('object')) & words(x.get('detalle_del_objeto_a_contratar'))), x) for x in cands),
                                key=lambda t: -t[0])
                cands = [scored[0][1]] if scored[0][0] >= 2 and scored[0][0] > scored[1][0] else cands
            if len(cands) != 1:
                report['ambiguous' if cands else 'not found'] += 1
                continue
            report['resolved'] += 1
            labelled.append({'uid': cands[0]['uid'], 'label': r.get('label'), 'case': case, 'nit': nit, 'year': year,
                             'number': c['number'], 'secop_number': cands[0].get('numero_del_contrato')})
    return labelled, report


def signed_date(x):
    import datetime
    m = re.match(r'(20\d\d)-(\d\d)-(\d\d)', str(x.get('fecha_de_firma_del_contrato') or ''))
    try:
        return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None
    except ValueError:
        return None


def months(x):
    n, unit = num(x.get('plazo_de_ejec_del_contrato')), str(x.get('rango_de_ejec_del_contrato') or '').upper()[:1]
    return None if n is None or unit not in ('M', 'D') else (n if unit == 'M' else n / 30)


def checks(x, total, conc, directs=None, value_by=None):
    value, added = num(x.get('cuantia_contrato')), num(x.get('valor_total_de_adiciones'))
    days = (num(x.get('tiempo_adiciones_en_dias')) or 0) + 30 * (num(x.get('tiempo_adiciones_en_meses')) or 0)
    st = lambda v: {'status': 'unknown' if v is None else 'signal' if v else 'clear'}
    proc = (x.get('tipo_de_proceso') or '').lower()
    k = conc.get(x.get('contractor_hash'))
    return {
        'CO1 direct award': st(None if not proc else 'directa' in proc),
        'CO2 amount increase > 20 %': st(None if not value or added is None else added / value > INCREASE),
        'CO3 term extension': st(days > 0 if x.get('tiempo_adiciones_en_dias') is not None or x.get('tiempo_adiciones_en_meses') is not None else None),
        'CO4 buyer share >= 5 %': st(None if not value or not total else value / total >= SHARE),
        'CO5 concentration': st(None if k is None else k),
        'U2 repeated direct award': st(None if not proc or not x.get('contractor_hash') else ('directa' in proc and (directs or {}).get(x['contractor_hash'], 0) >= 3)),
        'N1 December signature': st(None if signed_date(x) is None else signed_date(x).month == 12),
        'N2 weekend signature': st(None if signed_date(x) is None else signed_date(x).weekday() >= 5),
        'N3 long duration >= 36 months': st(None if months(x) is None else months(x) >= 36),
        'N4 supplier dependence >= 25 %': st(None if not x.get('contractor_hash') or not total else (value_by or {}).get(x['contractor_hash'], 0) / total >= 0.25),
    }


def analysis_rows(years, labelled, one_per_case):
    by_uid = {l['uid']: l for l in labelled}
    if one_per_case:
        first = {}
        for l in sorted(labelled, key=lambda l: (l['case'], l['uid'])):
            first.setdefault(l['case'], l['uid'])
        keep = set(first.values())
    out = []
    for (nit, year), rows in years.items():
        total = sum(num(x.get('cuantia_contrato')) or 0 for x in rows)
        known = [x for x in rows if x.get('contractor_hash')]
        counts = Counter(x['contractor_hash'] for x in known)
        conc = {h: (n / len(known) >= CONC_SHARE) for h, n in counts.items()} if len(known) >= CONC_MIN else {}
        directs = Counter(x['contractor_hash'] for x in known if 'directa' in (x.get('tipo_de_proceso') or '').lower())
        value_by = Counter()
        for x in known:
            value_by[x['contractor_hash']] += num(x.get('cuantia_contrato')) or 0
        for x in rows:
            l = by_uid.get(x['uid'])
            if l and one_per_case and x['uid'] not in keep:
                continue
            groups = [l['label'], 'combined'] if l else ['comparison']
            out.append({'id': x['uid'], 'buyer': nit, 'groups': groups, 'checks': checks(x, total, conc, directs, value_by)})
    return out


def report_rows(rows, title):
    print(f'\n### {title}\n')
    print('| Check | Final | First instance | Combined (buyers) | Comparisons | LR+ [95 %] | Learn / check | Points [95 %] | Decision |')
    print('|---|---|---|---|---|---|---|---|---|')
    results = []
    for check in CHECKS:
        res = pp.analyse(rows, check)
        for lab in ('final', 'first-instance'):
            h, n, (ph, pn) = pp.weighted(rows, check, lab)
            res[lab] = {'rate': round(h / n, 3) if n else None, 'tender_hits': ph, 'tenders': pn, 'buyers': n}
        halves = {name: pp.analyse([r for r in rows if cand.half(r['buyer']) == name], check) for name in ('learn', 'check')}
        decision = pp.decide(res)
        f = lambda g: f"{res[g]['rate'] * 100:.0f}% ({res[g]['tender_hits']}/{res[g]['tenders']})" if res[g]['rate'] is not None else 'NA'
        ci = f" [{res['lr_ci'][0]:.2f}, {res['lr_ci'][1]:.2f}]" if res.get('lr_ci') else ''
        pci = f" {res['proposed_points_ci']}" if res.get('proposed_points_ci') else ''
        print(f"| {check} | {f('final')} | {f('first-instance')} | {f('combined')} ({res['combined']['buyers']}) | {f('comparison')} | "
              f"{res.get('lr_shrunk')}{ci} | {halves['learn'].get('lr_shrunk')} / {halves['check'].get('lr_shrunk')} | {res.get('proposed_points')}{pci} | {decision} |")
        results.append({**res, 'learn_half': halves['learn'], 'check_half': halves['check'], 'decision': decision})
    return results


def main():
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--json')
    args = p.parse_args()
    records = [json.loads(l) for l in LEADS.read_text().splitlines() if l.strip().startswith('{"lead')]
    records = [r for r in records if r.get('outcome') in ('conviction', 'plea') and r.get('label') in ('final', 'first-instance')]
    years = load_years()
    labelled, rep = resolve(records, years)
    print(f'{len(records)} conviction records; {len(years)} entity-years; contracts: {dict(rep)}; '
          f"labelled by label: {dict(Counter(l['label'] for l in labelled))}; cases: {len({l['case'] for l in labelled})}")
    out = {'resolution': dict(rep), 'labelled': labelled}
    out['one_per_case'] = report_rows(analysis_rows(years, labelled, True), 'One contract per case (points basis until 2026-10-20)')
    out['all'] = report_rows(analysis_rows(years, labelled, False), 'All labelled contracts (points basis, amendment 2026-10-20)')
    if args.json:
        Path(args.json).write_text(json.dumps(out, indent=1, ensure_ascii=False) + '\n')


if __name__ == '__main__':
    main()
