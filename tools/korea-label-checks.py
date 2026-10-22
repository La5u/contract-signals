#!/usr/bin/env python3
"""Research only: global and Korean checks against KONEPS tenders a Fair Trade Commission decision found rigged.

Plan: research/calibration/korea-labels-plan.md (fixed before any rate was computed). Inputs in
~/.cache/contract-signals/korea: ftc/extract/links.jsonl (tools/match-korea-kftc-tenders.py: rigged tenders linked
to one KONEPS notice), ftc/decisions/<serial>.xml.gz (decision number, used to group a case's per-respondent
decisions), ftc-suits/finality.json (court outcome per case, optional: without it every case counts as "no
challenge found", which the output says), opnstd.sqlite `versions` (PPS open-standard contracts 2010-2026).

Labels: one representative contract per linked notice (the original version with the largest amount); the
notice's other contracts are left out of the comparisons. Comparisons: every other contract of the same buyer
(`--buyer contract`: 계약기관 `buyer_code`, as the plan says; `--buyer demand`: 수요기관 `demand_code`, a
sensitivity, because most rigged tenders were run by the PPS for another body) signed in the same year.
Decision rule (amendment 2026-10-20): all linked tenders, buyer-weighted rates (each buyer counts once), LR shrunk by
10 buyers, at least 10 labelled buyers, points 10 x log2 of the LR at the 25th percentile of the buyer resamples
(propose-indicator-points.decide). One tender per case and the learn/check halves are reported, not decided on. Bid-level
checks B1-B7 (B1 is the plan's G1 single offer) come from --bids (tools/korea-bid-features.py) and are unknown for
tenders whose opening day was not downloaded.
"""
import argparse
import datetime as dt
import gzip
import importlib.util
import json
import os
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('pp', ROOT / 'tools/propose-indicator-points.py')
pp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pp)
cspec = importlib.util.spec_from_file_location('cand', ROOT / 'tools/ukraine-candidate-indicators.py')
cand = importlib.util.module_from_spec(cspec)
cspec.loader.exec_module(cand)

BASE = Path(os.environ.get('XDG_CACHE_HOME', str(Path.home() / '.cache'))) / 'contract-signals/korea'
LINKED = ('notice', 'amount', 'amount-buyer', 'buyer-name')
DATA_END = dt.date(2026, 9, 1)
UPHELD_P = 0.91  # plan: KFTC yearbook 2024 Table 6-4, 2020-2024 (won + partly won) / all
WEIGHTS = {'none': 1.0, 'upheld': 1.0, 'pending': UPHELD_P, 'annulled-first-instance': 0.5, 'annulled': 0.0}
CHECKS = ['G2 private contract', 'G3 buyer share >= 5 %', 'G4 concentration', 'G5 3+ changes', 'G6 amount increase > 20 %',
          'N1 December signature', 'N2 weekend signature', 'N4 supplier dependence >= 25 %', 'N5 first-time supplier',
          'U2 repeated private contract', 'K1 single-bidder private contract', 'K2 re-tender private contract',
          'K3 just under small-value limit', 'K4 split contracts', 'K5 restricted competition', 'K6 award >= 95 % of reserve']
# Bid-level checks (plan, "Bid-level checks", 2026-10-22), from tools/korea-bid-features.py; unknown without bid rows.
BID_CHECKS = ['B1 single bid', 'B2 two or three bids', 'B3 just above the lower limit', 'B4 low bid dispersion',
              'B5 large first gap', 'B6 better bids disqualified', 'B7 same-minute bids']
CHECKS += BID_CHECKS
COMPETITIVE = ('일반경쟁', '제한경쟁', '지명경쟁')
# Legal grounds as cited in prvtcntrctRsn (normalize-korea-opnstd.py `legal_ref`): decree articles of the State and
# Local Contract Acts.
K1_REFS = ('국가계약법 제27조제3항', '지방계약법 제26조제2항')
K2_REFS = ('국가계약법 제27조제1항', '지방계약법 제26조제1항')
SMALL_REFS = ('국가계약법 제26조제1항5호가2목', '지방계약법 제25조제1항5호나목')
SMALL_LIMIT = 22_000_000  # 추정가격 2천만원 + 10 % VAT


def field(text, tag):
    m = re.search(f'<{tag}>(?:<!\\[CDATA\\[)?(.*?)(?:\\]\\]>)?</{tag}>', text, re.S)
    return m.group(1).strip() if m else ''


def case_key(serial):
    """Decision type and number (의결 제2020-216호 -> 의결 2020-216); a case split into per-respondent decisions shares it."""
    path = BASE / 'ftc/decisions' / f'{serial}.xml.gz'
    no = field(gzip.open(path, 'rt', encoding='utf-8').read(), '결정번호') if path.exists() else ''
    m = re.search(r'(\d{4})\s*-\s*(\d+)', no)
    kind = re.sub(r'[^가-힣]', '', no.split('제')[0])  # 의결, 결정, 재결, 의결약: numbered separately
    return f'{kind} {m.group(1)}-{int(m.group(2)):03d}' if m else f'serial:{serial}'


def parse_date(s):
    try:
        return dt.date.fromisoformat(str(s or '')[:10])
    except ValueError:
        return None


def load_labels():
    links = [json.loads(l) for l in open(BASE / 'ftc/extract/links.jsonl')]
    labels, cases = {}, {}
    for l in links:
        if l['link'] not in LINKED:
            continue
        c = l['candidates'][0]
        if l['serial'] not in cases:
            cases[l['serial']] = case_key(l['serial'])
        labels.setdefault(c['notice_no'], {'notice': c['notice_no'], 'contracts': set(), 'case': cases[l['serial']],
                                          'serials': set(), 'link': l['link']})
        labels[c['notice_no']]['contracts'] |= set(c['contracts'])
        labels[c['notice_no']]['serials'].add(l['serial'])
    return labels


def scan(db, labels, buyer_mode):
    """One pass over `versions`: the labelled contracts, then every version of their buyers' contracts."""
    con = sqlite3.connect(f'file:{db}?mode=ro', uri=True)
    cols = ['cntrct_no', 'ord', 'signed', 'method', 'amount', 'total_amount', 'business_type', 'buyer_code', 'demand_code',
            'supplier_bizrno', 'notice_no', 'notice_ord', 'legal_ref', 'reserve_price', 'term_type']
    wanted = {n for lab in labels.values() for n in lab['contracts']}
    marks = {}
    q = f'SELECT {", ".join(cols)} FROM versions WHERE cntrct_no IN ({",".join("?" * len(wanted))})'
    for rec in con.execute(q, sorted(wanted)):
        r = dict(zip(cols, rec))
        marks.setdefault(r['cntrct_no'], r)
    key_col = 'buyer_code' if buyer_mode == 'contract' else 'demand_code'
    buyers = {r[key_col] for r in marks.values() if r[key_col]}
    years = [parse_date(r['signed']).year for r in marks.values() if parse_date(r['signed'])]
    lo, hi = f'{min(years) - 3}-01-01', f'{max(years) + 1}-12-31'
    versions = defaultdict(list)
    for rec in con.execute(f'SELECT {", ".join(cols)} FROM versions WHERE signed BETWEEN ? AND ?', (lo, hi)):
        r = dict(zip(cols, rec))
        if r[key_col] in buyers:
            versions[r['cntrct_no']].append(r)
    return versions, key_col


def contracts_from(versions, key_col):
    """One record per contract from its earliest version in `versions` (its buyer: tools/korea-site-checks.py
    partitions by the same attribution). original False: the original (ord 0) is missing, so date, amount and
    supplier are an amendment's; build_checks leaves such a contract out of every total and its checks unknown."""
    out = {}
    for no, vs in versions.items():
        # Ties on ord: the smallest buyer code, as tools/korea-site-checks.py attributes.
        vs.sort(key=lambda r: (r['ord'] or 0, r[key_col] is None, r[key_col] or ''))
        first, last = vs[0], vs[-1]
        d = parse_date(first['signed'])
        if not d or not first[key_col]:
            continue
        horizon = d + dt.timedelta(days=730)
        later = [v for v in vs[1:] if (parse_date(v['signed']) or d) <= horizon]
        amt = lambda r: r['total_amount'] or r['amount']
        out[no] = {'no': no, 'buyer': first[key_col], 'year': d.year, 'date': d, 'method': first['method'] or '',
                   'amount': amt(first) or 0, 'last_amount': amt(last) or 0, 'business': first['business_type'],
                   'supplier': first['supplier_bizrno'], 'notice': (first['notice_no'] or '').strip(),
                   'ref': first['legal_ref'] or '', 'reserve': first['reserve_price'], 'changes': len(later),
                   'window_complete': horizon <= DATA_END, 'long_term': '장기' in (first['term_type'] or ''),
                   'original': (first['ord'] or 0) == 0, 'notice_ord': (first.get('notice_ord') or '').strip()}
    return out


class Bids:
    """Bid features per opening (tools/korea-bid-features.py), looked up by notice."""

    def __init__(self, path=BASE / 'bid-features.sqlite'):
        self.con = sqlite3.connect(f'file:{path}?mode=ro', uri=True)
        self.con.row_factory = sqlite3.Row
        self.refs = {(r['type'], r['year']): r for r in self.con.execute('SELECT * FROM refs')}

    def opening(self, notice, notice_ord):
        """The contract's opening: same order as its notice_ord, else the latest with a winner, else the latest."""
        rows = self.con.execute('SELECT * FROM openings WHERE notice = ? ORDER BY day, ord', (notice,)).fetchall()
        if not rows:
            return None
        same = [r for r in rows if r['ord'] == notice_ord]
        pool = same or rows
        won = [r for r in pool if r['winner']]
        return (won or pool)[-1]


def bid_checks(o, refs):
    st = lambda v: {'status': 'unknown' if v is None else 'signal' if v else 'clear'}
    if o is None:
        return {k: st(None) for k in BID_CHECKS}
    ref = refs.get((o['type'], o['year']))
    wr, lr = o['winner_rate'], o['lower_rate']
    return {
        'B1 single bid': st(o['bids'] == 1),
        'B2 two or three bids': st(o['bids'] in (2, 3)),
        'B3 just above the lower limit': st(None if wr is None or lr is None else 0 <= wr - lr < 0.1),
        'B4 low bid dispersion': st(None if o['cv'] is None or not ref or ref['cv_p10'] is None else o['cv'] < ref['cv_p10']),
        'B5 large first gap': st(None if o['rd'] is None or not ref or ref['rd_p90'] is None else o['rd'] > ref['rd_p90']),
        'B6 better bids disqualified': st(None if o['dq_lower'] is None else o['dq_lower'] >= 2),
        'B7 same-minute bids': st(2 <= o['bids'] <= 20 and bool(o['same_minute'])),
    }


def build_checks(contracts, first_year=None, bids=None):
    """first_year: the data's first year (N5 needs three earlier years); default the earliest in contracts.
    tools/korea-site-checks.py passes it, since it calls this one buyer at a time."""
    total, value_by, n_private = Counter(), Counter(), Counter()
    groups = defaultdict(Counter)
    years_with = defaultdict(set)
    small = defaultdict(list)
    # Amendment-only contracts are left out of the totals: their signing year and original amount are unknown, and an
    # amended amount counted in the amendment's year would misstate that year.
    originals = [c for c in contracts.values() if c.get('original', True)]
    for c in originals:
        key = (c['buyer'], c['year'])
        total[key] += c['amount']
        if c['supplier']:
            value_by[key + (c['supplier'],)] += c['amount']
            groups[key + (c['business'],)][c['supplier']] += 1
            years_with[(c['buyer'], c['supplier'])].add(c['year'])
            if c['method'] == '수의계약':
                n_private[key + (c['supplier'],)] += 1
                if c['ref'] in SMALL_REFS:
                    small[(c['buyer'], c['supplier'])].append(c)
    first_year = first_year or min((c['year'] for c in originals), default=None)
    split = set()
    for cs in small.values():
        cs.sort(key=lambda c: c['date'])
        for i, c in enumerate(cs):
            near = [o for o in cs if abs((o['date'] - c['date']).days) <= 30]
            if len(near) >= 2 and sum(o['amount'] for o in near) > SMALL_LIMIT:
                split.add(c['no'])

    def checks(c):
        if not c.get('original', True):
            return {k: {'status': 'unknown'} for k in CHECKS}
        return {**contract_checks(c), **bid_checks(bids.opening(c['notice'], c.get('notice_ord', '')) if bids and c['notice'] else None,
                                                   bids.refs if bids else {})}

    def contract_checks(c):
        key, s = (c['buyer'], c['year']), c['supplier']
        st = lambda v: {'status': 'unknown' if v is None else 'signal' if v else 'clear'}
        private = c['method'] == '수의계약'
        g = groups.get(key + (c['business'],), {})
        n = sum(g.values())
        return {
            'G2 private contract': st(private),
            'G3 buyer share >= 5 %': st(None if not total[key] else c['amount'] / total[key] >= 0.05),
            'G4 concentration': st(None if not s or n < 10 else g[s] / n >= 0.6),
            'G5 3+ changes': st(None if not c['window_complete'] or c['long_term'] else c['changes'] >= 3),
            'G6 amount increase > 20 %': st(None if not c['amount'] or not c['window_complete'] or c['long_term'] else c['last_amount'] > 1.2 * c['amount']),
            'N1 December signature': st(c['date'].month == 12),
            'N2 weekend signature': st(c['date'].weekday() >= 5),
            'N4 supplier dependence >= 25 %': st(None if not s or not total[key] else value_by[key + (s,)] / total[key] >= 0.25),
            'N5 first-time supplier': st(None if not s or c['year'] - 3 < first_year
                                         else not any(c['year'] - 3 <= y < c['year'] for y in years_with[(c['buyer'], s)])),
            'U2 repeated private contract': st(None if not s else private and n_private[key + (s,)] >= 3),
            'K1 single-bidder private contract': st(private and c['ref'] in K1_REFS),
            'K2 re-tender private contract': st(private and c['ref'] in K2_REFS),
            'K3 just under small-value limit': st(private and c['ref'] in SMALL_REFS and 19_800_000 <= c['amount'] <= SMALL_LIMIT),
            'K4 split contracts': st(c['no'] in split),
            'K5 restricted competition': st(c['method'] in ('제한경쟁', '지명경쟁')),
            'K6 award >= 95 % of reserve': st(None if not c['reserve'] or not c['amount'] else c['amount'] >= 0.95 * float(c['reserve'])),
        }
    return checks


def main():
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--db', type=Path, default=BASE / 'opnstd.sqlite')
    p.add_argument('--buyer', choices=('contract', 'demand'), default='contract')
    p.add_argument('--json', type=Path)
    p.add_argument('--bids', type=Path, default=BASE / 'bid-features.sqlite', help='tools/korea-bid-features.py output; '
                   'without it the B checks are unknown')
    args = p.parse_args()
    labels = load_labels()
    fin_path = BASE / 'ftc-suits/finality.json'
    finality = json.loads(fin_path.read_text()) if fin_path.exists() else {}
    versions, key_col = scan(args.db, labels, args.buyer)
    contracts = contracts_from(versions, key_col)
    checks = build_checks(contracts, bids=Bids(args.bids) if args.bids.exists() else None)
    members, reps = set(), {}
    for lab in labels.values():
        cs = [contracts[n] for n in lab['contracts'] if n in contracts]
        members |= {c['no'] for c in cs}
        cs = [c for c in cs if c['original']]  # an amendment-only record cannot stand for the awarded contract
        if cs:
            rep = max(cs, key=lambda c: (c['amount'], c['no']))
            reps.setdefault(rep['no'], lab)
    status = lambda case: (finality.get(case) or {}).get('status', 'none')
    buyer_years = {(contracts[n]['buyer'], contracts[n]['year']) for n in reps}
    print(f'{len(labels)} linked notices in {len({l["case"] for l in labels.values()})} cases; {len(reps)} with a contract in the data; '
          f'{len(buyer_years)} buyer-years ({key_col}); {sum(1 for c in contracts.values() if (c["buyer"], c["year"]) in buyer_years)} contracts')
    print('finality:', dict(Counter(status(l['case']) for l in reps.values())),
          '' if finality else '(ftc-suits/finality.json missing: no court outcome checked yet)')

    def rows(universe, weighted):
        out = []
        for c in contracts.values():
            if (c['buyer'], c['year']) not in buyer_years or not c['original'] or not universe(c):
                continue
            lab = reps.get(c['no'])
            if c['no'] in members and not lab:
                continue
            w = WEIGHTS[status(lab['case'])] if lab and weighted else 1.0
            ch = checks(c)
            if lab and w > 0:
                out.append({'id': c['no'], 'buyer': c['buyer'], 'groups': ['collusion', 'combined'], 'case': lab['case'],
                            'checks': ch, **({'weight': w} if w < 1 else {})})
            if not lab or w < 1:
                out.append({'id': c['no'], 'buyer': c['buyer'], 'groups': ['comparison'], 'case': None, 'checks': ch,
                            **({'weight': 1 - w} if lab else {})})
        return out

    def one_per_case(rs):
        seen, out = set(), []
        for r in sorted(rs, key=lambda r: (r['case'] or '', r['id'])):
            if r['case']:
                if r['case'] in seen:
                    continue
                seen.add(r['case'])
            out.append(r)
        return out

    every = lambda c: True
    competitive = lambda c: c['method'] in COMPETITIVE and bool(c['notice'])
    sets = {'weighted, one per case, all contracts (decision basis until 2026-10-20)': one_per_case(rows(every, True)),
            'weighted, all linked tenders, all contracts (decision rule, amendment 2026-10-20)': rows(every, True),
            'weighted, one per case, competitive tenders with a notice': one_per_case(rows(competitive, True)),
            'unweighted (court outcome ignored), one per case, all contracts': one_per_case(rows(every, False))}
    out = {'buyer': key_col, 'finality_checked': bool(finality), 'sets': {}}
    for name, rs in sets.items():
        pos = [r for r in rs if 'combined' in r['groups']]
        print(f'\n### {name}: {len(pos)} labelled ({len({r["buyer"] for r in pos})} buyers), '
              f'{sum(1 for r in rs if "comparison" in r["groups"])} comparisons\n')
        print('| Check | Hit rate, rigged | Comparisons | LR+ [95 %] | Learn / check | Points [95 %] | Decision |')
        print('|---|---|---|---|---|---|---|')
        res_list = []
        for check in CHECKS:
            res = pp.analyse(rs, check)
            halves = {h: pp.analyse([r for r in rs if cand.half(r['buyer']) == h], check) for h in ('learn', 'check')}
            decision = pp.decide(res)
            f = lambda g: (f"{res[g]['rate'] * 100:.0f}% ({res[g]['tender_hits']}/{res[g]['tenders']}, {res[g]['buyers']} buyers)"
                           if res[g]['rate'] is not None else 'NA')
            ci = f" [{res['lr_ci'][0]:.2f}, {res['lr_ci'][1]:.2f}]" if res.get('lr_ci') else ''
            print(f"| {check} | {f('combined')} | {f('comparison')} | {res.get('lr_shrunk')}{ci} | "
                  f"{halves['learn'].get('lr_shrunk')} / {halves['check'].get('lr_shrunk')} | "
                  f"{res.get('proposed_points')} {res.get('proposed_points_ci') or ''} | {decision} |")
            res_list.append({**res, 'learn_half': halves['learn'], 'check_half': halves['check'], 'decision': decision})
        out['sets'][name] = res_list
    if args.json:
        args.json.write_text(json.dumps(out, indent=1, ensure_ascii=False, default=list) + '\n')


if __name__ == '__main__':
    main()
