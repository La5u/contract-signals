#!/usr/bin/env python3
"""Research only: Romanian checks RO0-RO5 against procedures found rigged by the Competition Council.

Plan: research/calibration/romania-bid-rigging-plan.md (fixed before this ran). Inputs in ~/.cache/contract-signals:
romania-cc/procedures-ocr.jsonl (procedures per decision, role rigged/mentioned), romania-cc/court-cases.jsonl
(court portal), romania-seap/normalized/<year>/*.jsonl.gz (SEAP contract exports).

Linking: a rigged procedure resolves to SEAP contracts by its notice number (participation/initiation or award
notice, digits compared without prefixes) in the procedure's years; otherwise by buyer CUI + year + winner CUI
when that leaves one procedure. One representative contract per procedure (largest value).
Challenges: a decision is challenged when a court case names it or is an annulment action filed within a year
of it; the outcome at the High Court is not visible in the portal, so challenged decisions are not used for the
decision rule (reported as robustness).
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

CC = Path.home() / '.cache/contract-signals/romania-cc'
SEAP = Path.home() / '.cache/contract-signals/romania-seap/normalized'
SHARE, CONC_SHARE, CONC_MIN = 0.05, 0.6, 10
CHECKS = ['RO0 single offer', 'RO1 direct award', 'RO2 buyer share >= 5 %', 'RO3 concentration', 'RO5 framework / subsequent']


def digits(s):
    return re.sub(r'\D', '', str(s or '')).lstrip('0')


def cui(s):
    return digits(str(s or '').upper().replace('RO', ''))


def year_of(rec):
    m = re.search(r'(20\d\d)', str(rec.get('contract_date') or ''))
    if m:
        return int(m.group(1))
    m = re.search(r'/(20\d\d)', str(rec.get('source') or ''))
    return int(m.group(1)) if m else None


def notice_numbers(proc):
    out = set()
    for s in proc.get('notice_ids') or []:
        s = str(s)
        if re.search(r'monitorul|\bMO\b|JOUE|contract\b|hotar|PV |raport|adresa|documenta', s, re.I) and not re.search(r'SEAP|CN|SCN|CAN|DA|ADV|anun', s):
            continue
        for m in re.finditer(r'(?:CN|SCN|CAN|DA|ADV)\s?(\d{5,8})|anun\w*\s+(?:de\s+)?(?:participare|atribuire|initiere)\w*\s+(?:nr\.?\s*)?(\d{4,8})', s, re.I):
            out.add((m.group(1) or m.group(2)).lstrip('0'))
    return out


def proc_years(proc):
    ys = sorted({int(y) for d in (proc.get('dates') or []) for y in re.findall(r'(20\d\d)', str(d))})
    return ys


def stream_seap(years):
    for y in years:
        for p in sorted((SEAP / str(y)).glob('*.jsonl.gz')) if (SEAP / str(y)).exists() else []:
            with gzip.open(p, 'rt', encoding='utf-8') as fh:
                for line in fh:
                    yield json.loads(line)


KEEP = ('buyer', 'title', 'buyer_cui', 'procedure', 'concluded_by', 'notice_init', 'notice_award', 'offers_num', 'contract_no',
        'contract_date', 'cpv', 'value_ron_num', 'winner_cui', 'source')


def row_key(r):
    return (r.get('source'), r.get('contract_no'), r.get('notice_init'), r.get('notice_award'), r.get('winner_cui'), r.get('value_ron_num'))


def procedure_key(o):
    return '|'.join(str(o.get(k) or '') for k in ('decision', 'buyer', 'subject', 'lot')) + '|' + ','.join(o.get('dates') or [])


def candidate_rows(years, notices, cuis, winners):
    """Pass 1: rows that can link a procedure (notice number, buyer CUI or winner CUI)."""
    out = []
    for r in stream_seap(years):
        if (digits(r.get('notice_init')) in notices or digits(r.get('notice_award')) in notices
                or cui(r.get('buyer_cui')) in cuis or cui(r.get('winner_cui')) in winners):
            out.append({k: r.get(k) for k in KEEP})
    return out


def buyer_rows(years, buyers):
    """Pass 2: every row of the labelled buyers (the comparison universe)."""
    return [{k: r.get(k) for k in KEEP} for r in stream_seap(years) if cui(r.get('buyer_cui')) in buyers]


NAME_STOP = set('societatea nationala compania directia generala judetul judetean consiliul primaria comuna orasul municipiul '
                'romania romana sa srl regia autonoma unitatea administrativ teritoriala pentru si de din a al'.split())


def iso_dates(values):
    """yyyy-mm-dd from 'dd.mm.yyyy', 'dd/mm/yyyy', 'yyyy-mm-dd' or 'mm/dd/yyyy hh:mm' (2024 export)."""
    out = set()
    for v in values:
        v = str(v or '')
        for d, m, y in re.findall(r'\b(\d{1,2})[./](\d{1,2})[./](20\d\d)', v):
            out.add(f'{y}-{int(m):02d}-{int(d):02d}')
            if '/' in v and int(d) <= 12:
                out.add(f'{y}-{int(d):02d}-{int(m):02d}')
        out.update(re.findall(r'(20\d\d-\d\d-\d\d)', v))
    return out


def name_words(s):
    s = str(s or '').lower().translate(str.maketrans('ăâîșşțţ', 'aaisstt'))
    return {w for w in re.findall(r'[a-z]{4,}', s) if w not in NAME_STOP}


def challenged(decisions, cases):
    out = {}
    for d in decisions:
        num, yr = (d.split('/') + [''])[:2]
        hits = []
        for c in cases:
            if c['decision'] != d:
                continue
            obj = (c.get('object') or '').lower()
            named = re.search(rf'\b{num}\s*/', obj) is not None
            filed = re.search(r'/(20\d\d)', c.get('number') or '')
            near = filed and yr.isdigit() and int(yr) <= int(filed.group(1)) <= int(yr) + 1
            if 'anulare' in obj and (named or near):
                hits.append(c['number'])
        out[d] = hits
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--json')
    args = p.parse_args()
    lines = [json.loads(l) for l in (CC / 'procedures-ocr.jsonl').read_text().splitlines() if l.strip()]
    procs = [o for o in lines if o.get('type') != 'decision' and o.get('role') == 'rigged']
    cases = [json.loads(l) for l in (CC / 'court-cases.jsonl').read_text().splitlines() if l.strip()]
    chal = challenged(sorted({o['decision'] for o in procs}), cases)
    years = sorted({y for o in procs for y in proc_years(o)} | {y + 1 for o in procs for y in proc_years(o)})
    years = [y for y in years if (SEAP / str(y)).exists()]
    notices = {n for o in procs for n in notice_numbers(o)}
    win = lambda o: {cui(w) for w in (o['winner_cui'] if isinstance(o.get('winner_cui'), list) else [o.get('winner_cui')]) if w}
    cands_all = candidate_rows(years, notices, {cui(o.get('buyer_cui')) for o in procs if o.get('buyer_cui')},
                               set().union(*(win(o) for o in procs)) - {''})
    by_notice, by_winner_year = defaultdict(list), defaultdict(list)
    for i, r in enumerate(cands_all):
        for f in ('notice_init', 'notice_award'):
            if digits(r.get(f)):
                by_notice[digits(r.get(f))].append(i)
        by_winner_year[(cui(r.get('winner_cui')), year_of(r))].append(i)
    resolved, report, ambiguous = [], Counter(), []
    review = {}
    if (CC / 'ambiguous-resolved.jsonl').exists():   # reviewed choices: procedure key -> chosen SEAP row key
        for line in (CC / 'ambiguous-resolved.jsonl').read_text().splitlines():
            if line.strip():
                x = json.loads(line)
                review[x['procedure_key']] = x
    for o in procs:
        ys = set(proc_years(o)) | {y + 1 for y in proc_years(o)}
        idx = sorted({i for n in notice_numbers(o) for i in by_notice.get(n, []) if year_of(cands_all[i]) in ys})
        how = 'notice'
        pk = procedure_key(o)
        if not idx and pk in review and review[pk].get('chosen'):
            chosen = {tuple(c) for c in review[pk]['chosen']}
            idx = [i for i, r in enumerate(cands_all) if row_key(r) in chosen]
            how = 'reviewed choice' if idx else how
        if not idx and win(o):
            pool = [i for w in win(o) for y in ys for i in by_winner_year.get((w, y), [])]
            if o.get('buyer_cui'):
                pool = [i for i in pool if cui(cands_all[i].get('buyer_cui')) == cui(o['buyer_cui'])]
                how = 'buyer CUI + winner'
            else:
                pool = [i for i in pool if name_words(o.get('buyer')) & name_words(cands_all[i].get('buyer'))]
                how = 'buyer name + winner'
            subject = name_words(o.get('subject'))
            if subject:
                pool = [i for i in pool if subject & name_words(cands_all[i].get('title'))] or (pool if not any(cands_all[i].get('title') for i in pool) else [])
            groups = {(cands_all[i].get('notice_init') or cands_all[i].get('notice_award') or cands_all[i].get('contract_no')) for i in pool}
            if len(groups) > 1:   # tie-break only on an exact date of the decision
                dated = [i for i in pool if iso_dates([cands_all[i].get('contract_date')]) & iso_dates(o.get('dates') or [])]
                dgroups = {(cands_all[i].get('notice_init') or cands_all[i].get('notice_award') or cands_all[i].get('contract_no')) for i in dated}
                if len(dgroups) == 1:
                    pool, groups, how = dated, dgroups, how + ' + date'
            idx = pool if len(groups) == 1 else []
            if not idx:
                how = 'ambiguous' if pool else 'none'
                if pool:
                    ambiguous.append({'procedure': o, 'candidates': [cands_all[i] for i in pool[:60]]})
        if not idx:
            report['unresolved: ' + ('no notice match' if notice_numbers(o) and how == 'notice' else how)] += 1
            continue
        report[f'resolved by {how}'] += 1
        resolved.append((o, [cands_all[i] for i in idx]))
    (CC / 'ambiguous.jsonl').write_text(''.join(json.dumps({'procedure_key': procedure_key(a['procedure']), **a,
                                                    'candidate_keys': [row_key(c) for c in a['candidates']]}, ensure_ascii=False) + '\n' for a in ambiguous))
    buyers_set = {cui(r.get('buyer_cui')) for _, rs in resolved for r in rs} - {''}
    seap = buyer_rows(years, buyers_set)
    print(f'{len(procs)} rigged procedures in {len({o["decision"] for o in procs})} decisions; SEAP years {years[0]}-{years[-1]}; '
          f'{len(cands_all)} candidate rows, {len(seap)} rows of {len(buyers_set)} labelled buyers')
    pos_of = defaultdict(list)
    for i, r in enumerate(seap):
        pos_of[row_key(r)].append(i)
    by_buyer_year = defaultdict(list)
    for i, r in enumerate(seap):
        by_buyer_year[(cui(r.get('buyer_cui')), year_of(r))].append(i)
    labelled = {}
    for o, rs in resolved:
        idx = sorted({i for r in rs for i in pos_of.get(row_key(r), [])})
        if not idx:
            continue
        rep = max(idx, key=lambda i: seap[i].get('value_ron_num') or 0)
        labelled.setdefault(rep, {'decision': o['decision'], 'challenged': bool(chal.get(o['decision'])), 'members': set(idx)})
        labelled[rep]['members'] |= set(idx)
    print('linking:', dict(report), '| challenged decisions:', {d: len(v) for d, v in chal.items() if v})
    members = set().union(*(v['members'] for v in labelled.values())) if labelled else set()
    # Buyer-year totals and concentration (CPV division) over all SEAP rows of those buyers.
    buyers = {(cui(seap[i].get('buyer_cui')), year_of(seap[i])) for i in labelled}
    total, conc = Counter(), {}
    groups = defaultdict(Counter)
    for key in buyers:
        for i in by_buyer_year.get(key, []):
            r = seap[i]
            total[key] += r.get('value_ron_num') or 0
            w = cui(r.get('winner_cui'))
            if w:
                groups[key + (str(r.get('cpv') or '')[:2],)][w] += 1
    for g, cnt in groups.items():
        n = sum(cnt.values())
        conc[g] = {w: (k / n >= CONC_SHARE) for w, k in cnt.items()} if n >= CONC_MIN else {}

    def checks(r, key):
        proc = (r.get('procedure') or '').lower()
        direct = 'fara publicare' in proc.replace('ă', 'a').replace('ţ', 't') or 'negociere fara' in proc
        purchase = 'directa' in proc or 'cumparare' in proc
        offers = r.get('offers_num')
        st = lambda v: {'status': 'unknown' if v is None else 'signal' if v else 'clear'}
        value = r.get('value_ron_num')
        g = conc.get(key + (str(r.get('cpv') or '')[:2],), None)
        w = cui(r.get('winner_cui'))
        concluded = (r.get('concluded_by') or '').lower()
        return {'RO0 single offer': st(None if not proc or direct or purchase or offers is None else offers == 1),
                'RO1 direct award': st(None if not proc else direct),
                'RO2 buyer share >= 5 %': st(None if not value or not total[key] else value / total[key] >= SHARE),
                'RO3 concentration': st(None if g is None or not w else g.get(w, False)),
                'RO5 framework / subsequent': st(None if not concluded else ('acord' in concluded or 'subsecvent' in concluded)),
                '_offers': offers}

    def rows(keep):
        out = []
        for key in buyers:
            for i in by_buyer_year.get(key, []):
                if i in members and i not in labelled:
                    continue
                lab = labelled.get(i)
                if lab and not keep(lab):
                    continue
                c = checks(seap[i], key)
                out.append({'id': str(i), 'buyer': key[0], 'groups': ['collusion', 'combined'] if lab else ['comparison'],
                            'decision': lab['decision'] if lab else None, 'offers': c.pop('_offers'), 'checks': c})
        return out

    def one_per_decision(rs):
        seen, out = set(), []
        for r in sorted(rs, key=lambda r: (r['decision'] or '', r['id'])):
            if r['decision']:
                if r['decision'] in seen:
                    continue
                seen.add(r['decision'])
            out.append(r)
        return out

    sets = {'unchallenged, one per decision (decision rule)': one_per_decision(rows(lambda l: not l['challenged'])),
            'unchallenged, all procedures': rows(lambda l: not l['challenged']),
            'all Council findings, one per decision': one_per_decision(rows(lambda l: True)),
            'all Council findings, all procedures': rows(lambda l: True)}
    sets['all findings, 2+ offers (sensitivity)'] = [r for r in sets['all Council findings, all procedures'] if (r['offers'] or 0) >= 2]
    out = {'linking': dict(report), 'challenged': chal, 'sets': {}}
    for name, rs in sets.items():
        pos = [r for r in rs if 'combined' in r['groups']]
        print(f'\n### {name}: {len(pos)} labelled ({len({r["buyer"] for r in pos})} buyers), {len(rs) - len(pos)} comparisons\n')
        print('| Check | Hit rate, rigged | Comparisons | LR+ [95 %] | Learn / check | Points [95 %] | Decision |')
        print('|---|---|---|---|---|---|---|')
        res_list = []
        for check in CHECKS:
            res = pp.analyse(rs, check)
            halves = {h: pp.analyse([r for r in rs if cand.half(r['buyer']) == h], check) for h in ('learn', 'check')}
            decision = 'proposal' if halves['learn'].get('lr_ci') and halves['learn']['lr_ci'][0] > 1 and (halves['check'].get('lr_shrunk') or 0) > 1 else 'fails rule'
            f = lambda g: f"{res[g]['rate'] * 100:.0f}% ({res[g]['tender_hits']}/{res[g]['tenders']})" if res[g]['rate'] is not None else 'NA'
            ci = f" [{res['lr_ci'][0]:.2f}, {res['lr_ci'][1]:.2f}]" if res.get('lr_ci') else ''
            print(f"| {check} | {f('combined')} | {f('comparison')} | {res.get('lr_shrunk')}{ci} | {halves['learn'].get('lr_shrunk')} / {halves['check'].get('lr_shrunk')} | {res.get('proposed_points')} {res.get('proposed_points_ci') or ''} | {decision} |")
            res_list.append({**res, 'learn_half': halves['learn'], 'check_half': halves['check'], 'decision': decision})
        out['sets'][name] = res_list
    if args.json:
        Path(args.json).write_text(json.dumps(out, indent=1, ensure_ascii=False, default=list) + '\n')


if __name__ == '__main__':
    main()
