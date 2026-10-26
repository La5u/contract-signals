#!/usr/bin/env python3
"""Research only: global and Korean checks against KONEPS tenders a Fair Trade Commission decision found rigged.

Plan: research/calibration/korea-labels-plan.md (fixed before any rate was computed). Inputs in
~/.cache/contract-signals/korea: ftc/extract/links.jsonl (tools/match-korea-kftc-tenders.py: rigged tenders linked
to one KONEPS notice), ftc/decisions/<serial>.xml.gz (decision number, used to group a case's per-respondent
decisions), ftc-suits/finality.json (court outcome per case, optional: without it every case counts as "no
challenge found", which the output says), opnstd.sqlite `versions` (PPS open-standard contracts 2010-2026).

--family corruption / both adds court convictions (prec/extract/links.jsonl, tools/match-korea-court-contracts.py),
weighted as in load_court_labels; collusion alone stays the default.

Labels: one representative contract per linked notice (the original version with the largest amount); the
notice's other contracts are left out of the comparisons. Comparisons: every other contract of the same buyer
(`--buyer contract`: 계약기관 `buyer_code`, as the plan says; `--buyer demand`: 수요기관 `demand_code`, a
sensitivity, because most rigged tenders were run by the PPS for another body) signed in the same year.
Decision rule (amendment 2026-10-20): all linked tenders, buyer-weighted rates (each buyer counts once), LR shrunk by
10 buyers, at least 10 labelled buyers, points 10 x log2 of the LR at the 25th percentile of the buyer resamples
(propose-indicator-points.decide). One tender per case and the learn/check halves are reported, not decided on. Bid-level
checks B1-B9 (B1 is the plan's G1 single offer), N6 and N7 come from --bids (tools/korea-bid-features.py);
B10/B11 use --history (tools/korea-bid-history.py), joined to that same selected opening by notice and order.
Unknown where the opening, CEO rows, notice or complete history needed by the check is missing.
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
from fractions import Fraction
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
# Bid-level checks (plan, "Bid-level checks" and "Further checks", 2026-10-22); unknown without their inputs.
BID_CHECKS = ['B1 single bid', 'B2 two or three bids', 'B3 just above the lower limit', 'B4 low bid dispersion',
              'B5 large first gap', 'B6 better bids disqualified', 'B7 same-minute bids', 'B8 exact floor hit', 'B9 shared CEO',
              'B10 rotation', 'B11 repeated quote pair']
NOTICE_CHECKS = ['N6 short notice period', 'N7 just below a threshold']
# Round-number checks (plan, "Round-number checks", 2026-10-24); appended last so site letter positions stay.
ROUND_CHECKS = ['A1 round-percentage increase', 'A1b any whole-percent increase', 'A1c round-percentage increase, not +10 %',
                'A2 same step repeated', 'A3 round amount (1 digit)', 'A4 round amount (2 digits)',
                'A5 round budget (1 digit)', 'A6 round budget (2 digits)']
# Ukraine's checks on Korean data (owner 2026-10-24: every check in every country; cross-country-matrix.md). Same
# rules as in ukraine-candidate-indicators-plan.md where the data allow; appended last so site letter positions stay.
UA_CHECKS = ['UA-C1 exactly two bids', 'UA-C2 only one valid bid', 'UA-C9 award >= 98 % of reserve',
             'UA-C11 price increase', 'UA-C12 term extension', 'UA-C13 amount cut', 'UA-C15 individual supplier',
             'UA-D2 private contract above the small-value limit', 'UA-K5 tight bids (CV < 3 %)']
# Standard bid indicators (indicator-standard.md; plan "Standard bid indicators", 2026-10-24): one bin per letter,
# mutually exclusive within BID-COUNT.
COUNT_BINS = [(1, 1), (2, 2), (3, 3), (4, 5), (6, 10), (11, 10**9)]
STD_CHECKS = [f'BID-COUNT {lo}' if lo == hi else f'BID-COUNT {lo}+' if hi > 10**8 else f'BID-COUNT {lo}-{hi}'
              for lo, hi in COUNT_BINS] + ['BID-VALID only one valid of 2+', 'BID-VALID 2+ better rejected']
# Price slot (owner 2026-10-25, korea-collusion-results.md "One range per indicator, counter-ranges and two ranges"):
# PRICE-RATIO's chosen range and FLOOR-GAP's cut, as tools/korea-curves.py measures them. B12 is clear below the cut,
# which carries FLOOR-GAP's negative points; unknown without a stated floor. K7 is unknown wherever the opening states a
# floor, also when its winning rate is missing, so the two never both score. Appended last so site letters stay.
# FLOOR-GAP's cut: 0.97 on 2026-10-25 (cross-validated 0.9672), 1.01 since 2026-10-26 (1.00926 once the 2021-2024
# openings were backfilled; korea-collusion-results.md, "Rerun on the backfilled bid openings").
FLOOR_GAP_CUT = 1.01
PRICE_CHECKS = ['K7 award 92.2-100 % of reserve, no floor', f'B12 win >= {FLOOR_GAP_CUT} points above floor']
CHECKS += BID_CHECKS + NOTICE_CHECKS + ROUND_CHECKS + UA_CHECKS + STD_CHECKS + PRICE_CHECKS
NOTICE_THRESHOLDS = (100_000_000, 200_000_000, 300_000_000, 1_000_000_000, 5_000_000_000,
                     10_000_000_000, 20_000_000_000, 30_000_000_000)
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


COURT_LINKED = LINKED + ('buyer-only', 'bid-opening')
COURT_DROP = {'acquitted', 'sanction_annulled', 'no_liability'}


STATUS = {s: {'status': s} for s in ('unknown', 'signal', 'clear')}  # shared, never mutated: one dict per check per row ran out of memory


def status(v):
    """Tri-state check result: None unknown, truthy signal, falsy clear."""
    return STATUS['unknown' if v is None else 'signal' if v else 'clear']


def load_court_labels(path=None):
    """Corruption labels (plan: court convictions tied to a public contract): prec/extract/links.jsonl
    (tools/match-korea-court-contracts.py). Rulings citing each other's case numbers are one case; the highest court's
    outcome decides. Weight 1 for a Supreme Court ruling or a lower ruling at least two years old with no later ruling
    found, UPHELD_P for a younger one or a remand without a retrial found; audit findings (level 'audit') 1. Links with
    an acquittal, an annulled sanction or no finding proven are left out one by one; a notice named in several cases
    takes the best-weighted case."""
    links = [json.loads(l) for l in open(path or BASE / 'prec/extract/links.jsonl')]
    parent = {}

    def root(x):
        while parent.setdefault(x, x) != x:
            x = parent[x]
        return x
    rulings = {}
    for l in links:
        rulings[l['serial']] = l
        for low in l.get('lower_case_nos') or []:
            parent[root(re.sub(r'\s', '', low))] = root(re.sub(r'\s', '', l['case_no'] or l['serial']))
    level_rank = {'대법원': 3, '고등법원': 2}
    top = {}  # case root -> deciding ruling
    for l in rulings.values():
        key = root(re.sub(r'\s', '', l['case_no'] or l['serial']))
        rank = (level_rank.get(l.get('level'), 1), l.get('decision_date') or '')
        if key not in top or rank > top[key][0]:
            top[key] = (rank, l)
    weights, labels = {}, {}
    for l in links:
        if l['link'] not in COURT_LINKED:
            continue
        key = root(re.sub(r'\s', '', l['case_no'] or l['serial']))
        deciding = top[key][1]
        proven = [f.get('proven') for f in l.get('findings') or []]
        if deciding.get('outcome') in COURT_DROP or l.get('outcome') in COURT_DROP or True not in proven:
            continue  # left out per link: an acquitted or unproven link must not inherit its case's weight
        if deciding.get('level') == 'audit':
            w = 1.0  # plan "Audit family": an audit finding is not appealed like a ruling
        elif deciding.get('outcome') == 'quashed_remanded':
            w = UPHELD_P  # set aside and sent back; no retrial found: never more than an undecided case
        elif deciding.get('level') == '대법원':
            w = 1.0
        else:
            d = parse_date(deciding.get('decision_date'))
            w = 1.0 if d and (DATA_END - d).days >= 730 else UPHELD_P
        case = f'court:{key}'
        weights[case] = max(weights.get(case, 0.0), w)
        c = l['candidates'][0]
        lab = labels.setdefault(c['notice_no'], {'notice': c['notice_no'], 'contracts': set(), 'case': case,
                                                 'serials': set(), 'link': l['link'], 'family': 'corruption'})
        if w > weights.get(lab['case'], 0.0):  # a notice named in several cases takes the best-weighted one
            lab['case'] = case
        lab['contracts'] |= set(c['contracts'])
        lab['serials'].add(l['serial'])
    return labels, weights


def scan(db, labels, buyer_mode):
    """One pass over `versions`: the labelled contracts, then every version of their buyers' contracts."""
    con = sqlite3.connect(f'file:{db}?mode=ro', uri=True)
    cols = ['cntrct_no', 'ord', 'signed', 'method', 'amount', 'total_amount', 'business_type', 'buyer_code', 'demand_code',
            'supplier_bizrno', 'notice_no', 'notice_ord', 'legal_ref', 'reserve_price', 'term_type', 'period', 'supplier_kind']
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
        seq = [a for a in (amt(v) for v in [first] + later) if a]
        steps = [(a, b) for a, b in zip(seq, seq[1:]) if b > a]  # price increases between consecutive versions
        cuts = sum(1 for a, b in zip(seq, seq[1:]) if b < a)
        periods = [v.get('period') for v in [first] + later]
        out[no] = {'no': no, 'buyer': first[key_col], 'year': d.year, 'date': d, 'method': first['method'] or '',
                   'amount': amt(first) or 0, 'last_amount': amt(last) or 0, 'business': first['business_type'],
                   'supplier': first['supplier_bizrno'], 'notice': (first['notice_no'] or '').strip(),
                   'ref': first['legal_ref'] or '', 'reserve': first['reserve_price'], 'changes': len(later),
                   'window_complete': horizon <= DATA_END, 'long_term': '장기' in (first['term_type'] or ''),
                   'original': (first['ord'] or 0) == 0, 'notice_ord': (first.get('notice_ord') or '').strip(),
                   'steps': steps, 'cuts': cuts, 'periods': periods, 'kind': first.get('supplier_kind')}
    return out


class Bids:
    """Bid features per opening (tools/korea-bid-features.py), looked up by notice."""

    def __init__(self, path=BASE / 'bid-features.sqlite', history_path=None):
        self.con = sqlite3.connect(f'file:{path}?mode=ro', uri=True)
        self.con.row_factory = sqlite3.Row
        self.refs = {(r['type'], r['year']): r for r in self.con.execute('SELECT * FROM refs')}
        self.has_notices = bool(self.con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='notices'").fetchone())
        history_path = Path(history_path) if history_path is not None else Path(path).with_name('bid-history.sqlite')
        self.history_con = sqlite3.connect(f'file:{history_path}?mode=ro', uri=True) if history_path.exists() else None
        self.history_integer_keys = False
        if self.history_con:
            self.history_con.row_factory = sqlite3.Row
            tables = {r[0] for r in self.history_con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            self.history_integer_keys = any(r[1] == 'notice' and r[2].upper() == 'INTEGER'
                                            for r in self.history_con.execute('PRAGMA table_info(checks)'))
            if not {'checks', 'meta'} <= tables:
                self.history_con.close()
                self.history_con = None

    def opening(self, notice, notice_ord):
        """The contract's opening: same order as its notice_ord, else the latest with a winner, else the latest."""
        rows = self.con.execute('SELECT * FROM openings WHERE notice = ? ORDER BY day, ord', (notice,)).fetchall()
        if not rows:
            return None
        same = [r for r in rows if r['ord'] == notice_ord]
        pool = same or rows
        won = [r for r in pool if r['winner']]
        return (won or pool)[-1]

    def notice(self, notice):
        """Latest notice order, independently of the contract's opening."""
        if self.has_notices:
            return self.con.execute('SELECT * FROM notices WHERE notice = ?', (notice,)).fetchone()
        return None

    def history(self, opening):
        """Same opening as B1-B9; absent/unfinished history is unknown, including partial rebuilds."""
        if self.history_con and opening is not None:
            notice, order = opening['notice'], str(opening['ord']).zfill(3)
            if self.history_integer_keys:
                text = str(notice)
                if text.isascii() and text.isdigit() and int(text) < 2**63:
                    notice = int(text)
                else:
                    row = self.history_con.execute(
                        "SELECT id FROM identities WHERE kind = 'notice' AND value = ?", (text,)).fetchone()
                    if row is None:
                        return None
                    notice = row[0]
                order = int(order)
            return self.history_con.execute('''SELECT b10, b11 FROM checks
                WHERE notice = ? AND ord = ?
                  AND (SELECT value FROM meta WHERE key = 'checks_ready') = '1' ''',
                                            (notice, order)).fetchone()
        return None


def bid_checks(o, refs, history=None):
    st = status
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
        'B8 exact floor hit': st(None if wr is None or lr is None else 0 <= wr - lr < 0.01),
        'B9 shared CEO': st(o['shared_ceo'] if 'shared_ceo' in o.keys() else None),
        'B10 rotation': st(history['b10'] if history is not None else None),
        'B11 repeated quote pair': st(history['b11'] if history is not None else None),
    }


def price_checks(c, o):
    """PRICE-RATIO in [0.922, 1) where no floor is stated, and FLOOR-GAP >= FLOOR_GAP_CUT; FLOOR-GAP is null exactly where
    korea-curves.py's measure is, PRICE-RATIO also where the opening states a floor."""
    st = status
    floor = o is not None and bool(o['lower_rate'])
    ratio = c['amount'] / float(c['reserve']) if c['reserve'] and c['amount'] and float(c['reserve']) > 0 else None
    gap = None if not floor or not o['winner_rate'] else o['winner_rate'] - o['lower_rate']
    k7, b12 = PRICE_CHECKS
    return {k7: st(None if ratio is None or floor else 0.922 <= ratio < 1),
            b12: st(None if gap is None else gap >= FLOOR_GAP_CUT)}


def notice_checks(n):
    """N6 general notice minima; N7's fixed estimated-price breakpoints."""
    st = status
    if n is None:
        return {k: st(None) for k in NOTICE_CHECKS}
    price = n['presmpt']
    start, close = parse_date(n['notice_date']), parse_date(n['close_date'])
    minimum = None
    if n['type'] in ('공사', 'works') and price is not None:
        minimum = 7 if price < 1_000_000_000 else 15 if price < 5_000_000_000 else 40
    elif n['type'] in ('물품', '용역', '외자', 'goods', 'services', 'foreign'):
        minimum = 7
    short = None if not start or not close or minimum is None else (close - start).days < minimum
    if '재' in (n['status'] or ''):
        short = False
    return {
        'N6 short notice period': st(short),
        'N7 just below a threshold': st(None if price is None else any(0.97 * t <= price < t for t in NOTICE_THRESHOLDS)),
    }


class Budgets:
    """Allocated budget per notice (tools/korea-notice-budgets.py), looked up on demand."""

    def __init__(self, path=BASE / 'notice-budgets.sqlite'):
        self.con = sqlite3.connect(f'file:{path}?mode=ro', uri=True)

    def get(self, notice):
        row = self.con.execute('SELECT budget FROM budgets WHERE notice = ?', (notice,)).fetchone()
        return row[0] if row else None


def significant_digits(x):
    x = int(x)
    return len(str(x).rstrip('0')) if x > 0 else None


def whole_percent(a, b):
    """(exact whole percent, small-ratio) of an increase a -> b: small-ratio when b/a is p/q with q <= 9."""
    a, b = int(round(a)), int(round(b))  # some amounts are stored as floats (whole won)
    exact = (b - a) * 100 % a == 0
    return (exact and (b - a) * 100 // a), Fraction(b, a).denominator <= 9


def extended(periods):
    """Term extended in a later version: a later end date (YYYY-MM-DD) or more days than the original; None when the
    original period is missing or not comparable."""
    first = (periods or [None])[0]
    if not first:
        return None
    date = lambda p: re.fullmatch(r'\d{4}-\d\d-\d\d', str(p or '')) is not None
    days = lambda p: str(p or '').isdigit() and int(p) > 0
    if date(first):
        return any(date(p) and p > first for p in periods[1:])
    if days(first):
        return any(days(p) and int(p) > int(first) for p in periods[1:])
    return None


def ua_checks(c, o):
    st = status
    window = c['window_complete'] and not c['long_term']
    return {
        'UA-C1 exactly two bids': st(None if o is None else o['bids'] == 2),
        'UA-C2 only one valid bid': st(None if o is None or o['valid'] is None else o['bids'] >= 2 and o['valid'] == 1),
        'UA-C9 award >= 98 % of reserve': st(None if not c['reserve'] or not c['amount'] else c['amount'] >= 0.98 * float(c['reserve'])),
        'UA-C11 price increase': st(None if not window else bool(c.get('steps'))),
        'UA-C12 term extension': st(None if not window else extended(c.get('periods'))),
        'UA-C13 amount cut': st(None if not window else c.get('cuts', 0) > 0),
        'UA-C15 individual supplier': st(None if c.get('kind') in (None, 'unknown') else c['kind'] == 'individual'),
        'UA-D2 private contract above the small-value limit': st(c['method'] == '수의계약' and c['amount'] > SMALL_LIMIT),
        'UA-K5 tight bids (CV < 3 %)': st(None if o is None or o['cv'] is None else o['cv'] < 0.03),
    }


def std_checks(o):
    st = status
    out = {name: st(None if o is None else lo <= o['bids'] <= hi) for name, (lo, hi) in zip(STD_CHECKS, COUNT_BINS)}
    out['BID-VALID only one valid of 2+'] = st(None if o is None or o['valid'] is None else o['bids'] >= 2 and o['valid'] == 1)
    out['BID-VALID 2+ better rejected'] = st(None if o is None or o['dq_lower'] is None else o['dq_lower'] >= 2)
    return out


def round_checks(c, budget):
    st = status
    steps = None if not c['window_complete'] or c['long_term'] else c.get('steps', [])
    marks = [whole_percent(a, b) for a, b in steps or []]
    pct = [round((b - a) * 100 / a, 2) for a, b in steps or []]
    pct = [p for p in pct if p >= 1]
    digits = significant_digits(c['amount']) if c['amount'] else None
    bdigits = significant_digits(budget) if budget and budget >= 1_000_000 else None  # tiny budgets are placeholders (10 KRW)
    return {
        'A1 round-percentage increase': st(None if steps is None else any(w and not small for w, small in marks)),
        'A1b any whole-percent increase': st(None if steps is None else any(w for w, _ in marks)),
        'A1c round-percentage increase, not +10 %': st(None if steps is None else any(w and w != 10 and not small for w, small in marks)),
        'A2 same step repeated': st(None if steps is None else any(k >= 2 for k in Counter(pct).values())),
        'A3 round amount (1 digit)': st(None if digits is None else digits == 1),
        'A4 round amount (2 digits)': st(None if digits is None else digits == 2),
        'A5 round budget (1 digit)': st(None if bdigits is None else bdigits == 1),
        'A6 round budget (2 digits)': st(None if bdigits is None else bdigits == 2),
    }


def build_checks(contracts, first_year=None, bids=None, budgets=None):
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
            return {k: STATUS['unknown'] for k in CHECKS}
        opening = bids.opening(c['notice'], c.get('notice_ord', '')) if bids and c['notice'] else None
        return {**contract_checks(c), **bid_checks(opening, bids.refs if bids else {}, bids.history(opening) if bids else None),
                **notice_checks(bids.notice(c['notice']) if bids and c['notice'] else None),
                **round_checks(c, budgets.get(c['notice']) if budgets and c['notice'] else None),
                **ua_checks(c, opening), **std_checks(opening), **price_checks(c, opening)}

    def contract_checks(c):
        key, s = (c['buyer'], c['year']), c['supplier']
        st = status
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


def one_per_case(rs):
    seen, out = set(), []
    for r in sorted(rs, key=lambda r: (r['case'] or '', r['id'])):
        if r['case']:
            if r['case'] in seen:
                continue
            seen.add(r['case'])
        out.append(r)
    return out


def prepare(args, make_checks):
    """Labels, comparisons and weights as main() prints them; returns rows(universe, weighted) -> label and comparison
    rows whose `checks` come from make_checks(contracts) (tools/korea-curves.py passes raw measures)."""
    labels = load_labels() if args.family != 'corruption' else {}
    court_weights = {}
    if args.family != 'collusion':
        court, court_weights = load_court_labels(args.court_links)
        for notice, lab in court.items():
            if notice in labels:  # a KFTC-rigged tender also named in a ruling: kept as collusion, the case found first
                labels[notice]['contracts'] |= lab['contracts']
            else:
                labels[notice] = lab
    fin_path = BASE / 'ftc-suits/finality.json'
    finality = json.loads(fin_path.read_text()) if fin_path.exists() else {}
    versions, key_col = scan(args.db, labels, args.buyer)
    contracts = contracts_from(versions, key_col)
    checks = make_checks(contracts)
    members, reps = set(), {}
    for lab in labels.values():
        cs = [contracts[n] for n in lab['contracts'] if n in contracts]
        members |= {c['no'] for c in cs}
        cs = [c for c in cs if c['original']]  # an amendment-only record cannot stand for the awarded contract
        if cs:
            rep = max(cs, key=lambda c: (c['amount'], c['no']))
            reps.setdefault(rep['no'], lab)
    status = lambda case: (finality.get(case) or {}).get('status', 'none')
    weight = lambda case: court_weights.get(case, 0.0) if case.startswith('court:') else WEIGHTS[status(case)]
    buyer_years = {(contracts[n]['buyer'], contracts[n]['year']) for n in reps}
    print(f'{len(labels)} linked notices in {len({l["case"] for l in labels.values()})} cases; {len(reps)} with a contract in the data; '
          f'{len(buyer_years)} buyer-years ({key_col}); {sum(1 for c in contracts.values() if (c["buyer"], c["year"]) in buyer_years)} contracts')
    print('families:', dict(Counter(l.get('family', 'collusion') for l in reps.values())),
          'court weights:', dict(Counter(weight(l['case']) for l in reps.values() if l['case'].startswith('court:'))))
    print('finality:', dict(Counter(status(l['case']) for l in reps.values() if not l['case'].startswith('court:'))),
          '' if finality else '(ftc-suits/finality.json missing: no court outcome checked yet)')

    def rows(universe, weighted):
        out = []
        for c in contracts.values():
            if (c['buyer'], c['year']) not in buyer_years or not c['original'] or not universe(c):
                continue
            lab = reps.get(c['no'])
            if c['no'] in members and not lab:
                continue
            if lab and lab['case'].startswith('court:') and weight(lab['case']) == 0:
                continue  # acquitted or annulled: neither a label nor a comparison (plan)
            w = weight(lab['case']) if lab and weighted else 1.0
            ch = checks(c)
            if lab and w > 0:
                out.append({'id': c['no'], 'buyer': c['buyer'], 'groups': [lab.get('family', 'collusion'), 'combined'], 'case': lab['case'],
                            'checks': ch, **({'weight': w} if w < 1 else {})})
            if not lab or w < 1:
                out.append({'id': c['no'], 'buyer': c['buyer'], 'groups': ['comparison'], 'case': None, 'checks': ch,
                            **({'weight': 1 - w} if lab else {})})
        return out
    return rows, key_col, finality


def main():
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--db', type=Path, default=BASE / 'opnstd.sqlite')
    p.add_argument('--buyer', choices=('contract', 'demand'), default='contract')
    p.add_argument('--json', type=Path)
    p.add_argument('--budgets', type=Path, default=BASE / 'notice-budgets.sqlite',
                   help='tools/korea-notice-budgets.py output; without it A5/A6 are unknown')
    p.add_argument('--court-links', type=Path, default=BASE / 'prec/extract/links.jsonl',
                   help='corruption labels in the court-matcher format (e.g. bai/links.jsonl for audit findings)')
    p.add_argument('--family', choices=('collusion', 'corruption', 'both'), default='collusion',
                   help='labels: KFTC bid rigging, court convictions (prec/extract/links.jsonl) or both (the plan\'s decision set)')
    p.add_argument('--bids', type=Path, default=BASE / 'bid-features.sqlite', help='tools/korea-bid-features.py output; '
                   'without it the B checks, N6 and N7 are unknown')
    p.add_argument('--history', type=Path, default=BASE / 'bid-history.sqlite',
                   help='tools/korea-bid-history.py output; without complete history B10/B11 are unknown')
    args = p.parse_args()

    def make_checks(contracts):
        budgets = Budgets(args.budgets) if args.budgets.exists() else None
        return build_checks(contracts, bids=Bids(args.bids, args.history) if args.bids.exists() else None, budgets=budgets)

    rows, key_col, finality = prepare(args, make_checks)
    every = lambda c: True
    competitive = lambda c: c['method'] in COMPETITIVE and bool(c['notice'])
    # Built one at a time: all four at once ran out of memory on the audit family (2026-10-25).
    sets = {'weighted, one per case, all contracts (decision basis until 2026-10-20)': lambda: one_per_case(rows(every, True)),
            'weighted, all linked tenders, all contracts (decision rule, amendment 2026-10-20)': lambda: rows(every, True),
            'weighted, one per case, competitive tenders with a notice': lambda: one_per_case(rows(competitive, True)),
            'unweighted (court outcome ignored), one per case, all contracts': lambda: one_per_case(rows(every, False))}
    out = {'buyer': key_col, 'finality_checked': bool(finality), 'sets': {}}
    for name, build in sets.items():
        rs = build()
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
        del rs
    if args.json:
        args.json.write_text(json.dumps(out, indent=1, ensure_ascii=False, default=list) + '\n')


if __name__ == '__main__':
    main()
