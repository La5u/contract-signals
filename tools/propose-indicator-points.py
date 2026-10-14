#!/usr/bin/env python3
"""Research only: propose indicator points from the Ukrainian verdict cohort (weight of evidence).

Inputs: per-row check statuses written by tools/analyze-ukraine-verdict-cohort.cjs (second argument),
and optionally the amendment features of tools/fetch-verdict-contract-changes.py.

For each check, in this order (owner rule: hit rate decides inclusion, the comparison rate only sets points):
  1. hit rate among convicted tenders (corruption, fraud, combined), per tender and per buyer;
  2. rate among same-buyer comparison tenders;
  3. likelihood ratio LR+ = positive rate / comparison rate, with the positive rate shrunk toward the
     comparison rate (LR 1, no evidence) by a prior worth PRIOR_BUYERS buyers; 95 % interval by
     resampling buyers (a scheme usually sits at one buyer, so buyers, not tenders, are independent);
  4. proposed points = PDO * log2(LR shrunk), floored at 0: PDO points each time the odds double
     (credit-scorecard convention). PDO is a scale for the owner to choose, not a fitted value.

Only competitive procedures are compared: the comparison sample (Prozorro site search filtered on the
tendering period) contains no direct-award reports or negotiated procedures, so positives of those kinds
are left out, and checks that need them (direct award) get a hit rate but no ratio or points.

Counts are buyer-weighted: each buyer contributes total weight 1, spread over its evaluable rows.
Comparisons are unlabelled, not proven clean; convictions over-represent what gets prosecuted.
Changes no score, weight or dataset.
"""
import argparse
import json
import math
import random
from collections import defaultdict
from pathlib import Path

POSITIVE = ('corruption', 'fraud')
ELIGIBLE = ('confirmed', 'presumed')
PRIOR_BUYERS = 10
PDO = 10
BOOT = 2000
SEED = 20261012
AMENDMENT_CHECK = 'amendments-3plus (from contract records)'
MIN_BUYERS = 10                         # fewer evaluable positive buyers: no proposal
NON_COMPETITIVE = ('reporting', 'negotiation', 'negotiation.quick')
NOT_COMPARABLE = {'ua-direct-award': 'comparisons contain no direct awards', 'ua-repeated-direct': 'comparisons contain no direct awards'}


def amendment_points(n):
    """Current points of ua-contract-amendments before the term-extension bonus (score 3.5; a flat 8 in 3.4)."""
    return 10 if n >= 5 else 6


def load_rows(rows_path, changes_path, positive=POSITIVE):
    rows = json.loads(Path(rows_path).read_text())
    changes = {}
    if changes_path:
        changes = {r['id']: r['features'] for r in json.loads(Path(changes_path).read_text())['rows'] if r.get('features')}
    out, skipped = [], defaultdict(int)
    for r in rows:
        if r.get('procedure') in NON_COMPETITIVE:
            skipped[r['label']] += 1
            continue
        if r['label'] in positive:
            if r['finality'] not in ELIGIBLE:
                continue
            groups = [r['label'], 'combined']
        elif r['label'] == 'comparison':
            groups = ['comparison']
        else:
            continue
        checks = {k: v for k, v in r['checks'].items() if k != 'ua-contract-amendments'}
        if changes_path:
            f = changes.get(r['id'])
            checks[AMENDMENT_CHECK] = {'status': 'unknown'} if f is None else \
                {'status': 'signal' if f['changes'] >= 3 else 'clear', 'points': amendment_points(f['changes']) if f['changes'] >= 3 else None,
                 'changes': f['changes']}
        out.append({'id': r['id'], 'buyer': r.get('buyerId') or r['id'], 'groups': groups, 'checks': checks})
    return out, dict(skipped)


def weighted(rows, check, group, test=lambda c: c['status'] == 'signal'):
    """Buyer-weighted (hits, n) and plain (hits, n) among evaluable rows of a group.

    A row may carry `weight` (default 1): the probability that its label holds (e.g. a decision still under
    appeal). A buyer counts with the largest weight of its rows in the group; plain counts are weighted sums.
    With every weight 1 this is the unweighted rate."""
    per_buyer = defaultdict(list)
    for r in rows:
        c = r['checks'].get(check)
        if group in r['groups'] and c and c['status'] in ('signal', 'clear'):
            per_buyer[r['buyer']].append((bool(test(c)), r.get('weight', 1)))
    if all(w == 1 for v in per_buyer.values() for _, w in v):
        hits = sum(sum(h for h, _ in v) / len(v) for v in per_buyer.values())
        plain = sum(sum(h for h, _ in v) for v in per_buyer.values()), sum(len(v) for v in per_buyer.values())
        return hits, len(per_buyer), plain
    hits = n = 0.0
    for v in per_buyer.values():
        total = sum(w for _, w in v)
        if total:
            bw = max(w for _, w in v)
            hits += bw * sum(w * h for h, w in v) / total
            n += bw
    plain = round(sum(w * h for v in per_buyer.values() for h, w in v), 2), round(sum(w for v in per_buyer.values() for _, w in v), 2)
    return hits, n, plain


def shrunk_lr(h1, n1, h0, n0):
    if not n1 or not n0:
        return None
    p0 = (h0 + 0.5) / (n0 + 1)
    p1 = (h1 + PRIOR_BUYERS * p0) / (n1 + PRIOR_BUYERS)
    return p1 / p0


def bootstrap(rows, check, group, test=lambda c: c['status'] == 'signal'):
    buyers = sorted({r['buyer'] for r in rows})
    # Each resampled copy is a distinct buyer, so the weighted() sums reduce to per-buyer summaries:
    # (hit fraction, evaluable) for the group and for the comparisons. Same draws, same result.
    summary = {}
    for g in (group, 'comparison'):
        per_buyer = defaultdict(list)
        for r in rows:
            c = r['checks'].get(check)
            if g in r['groups'] and c and c['status'] in ('signal', 'clear'):
                per_buyer[r['buyer']].append((bool(test(c)), r.get('weight', 1)))
        # (buyer weight, buyer weight x hit fraction): (1, fraction) when unweighted, as before.
        summary[g] = {b: (max(w for _, w in v), max(w for _, w in v) * sum(w * h for h, w in v) / sum(w for _, w in v))
                      for b, v in per_buyer.items() if sum(w for _, w in v)}
    rng = random.Random(f'{SEED}-{check}-{group}')
    values = []
    for _ in range(BOOT):
        drawn = rng.choices(buyers, k=len(buyers))
        (h1, n1), (h0, n0) = ((sum(summary[g][b][1] for b in drawn if b in summary[g]), sum(summary[g][b][0] for b in drawn if b in summary[g]))
                              for g in (group, 'comparison'))
        lr = shrunk_lr(h1, n1, h0, n0)
        if lr:
            values.append(lr)
    if len(values) < BOOT / 2:
        return None
    values.sort()
    return values[int(0.025 * len(values))], values[int(0.975 * len(values)) - 1]


def points(lr):
    return max(0.0, round(PDO * math.log2(lr), 1)) if lr else None


def current_points(rows, check):
    pts = sorted(c['points'] for r in rows for k, c in r['checks'].items() if k == check and c['status'] == 'signal' and c.get('points') is not None)
    return (pts[0], pts[-1]) if pts else None


def analyse(rows, check, test=lambda c: c['status'] == 'signal'):
    res = {'check': check}
    for g in ('corruption', 'fraud', 'combined', 'comparison'):
        h, n, (ph, pn) = weighted(rows, check, g, test)
        res[g] = {'buyer_hits': round(h, 2), 'buyers': n, 'tender_hits': ph, 'tenders': pn,
                  'rate': round(h / n, 3) if n else None}
    c, k = res['combined'], res['comparison']
    if check in NOT_COMPARABLE:
        return dict(res, lr_raw=f'NA: {NOT_COMPARABLE[check]}', lr_shrunk=None, lr_ci=None, proposed_points='NA', proposed_points_ci=None)
    lr = shrunk_lr(c['buyer_hits'], c['buyers'], k['buyer_hits'], k['buyers'])
    res['lr_raw'] = round((c['buyer_hits'] / c['buyers']) / ((k['buyer_hits'] + 0.5) / (k['buyers'] + 1)), 3) if c['buyers'] and k['buyers'] else None
    res['lr_shrunk'] = round(lr, 3) if lr else None
    ci = bootstrap(rows, check, 'combined', test) if lr else None
    res['lr_ci'] = [round(x, 3) for x in ci] if ci else None
    res['proposed_points'] = points(lr) if c['buyers'] >= MIN_BUYERS else f'too few ({c["buyers"]} buyers)'
    res['proposed_points_ci'] = [points(x) for x in ci] if ci and c['buyers'] >= MIN_BUYERS else None
    return res


def bands(rows, check):
    """Signals split at the median of their points: does a stronger signal carry more evidence?"""
    pts = sorted(c['points'] for r in rows for k, c in r['checks'].items() if k == check and c['status'] == 'signal' and c.get('points') is not None)
    if len(set(pts)) < 2 or check == AMENDMENT_CHECK:
        return []
    cut = pts[len(pts) // 2]
    low = analyse(rows, check, lambda c: c['status'] == 'signal' and c['points'] < cut)
    high = analyse(rows, check, lambda c: c['status'] == 'signal' and c['points'] >= cut)
    return [dict(low, band=f'points < {cut}'), dict(high, band=f'points >= {cut}')]


def fmt(res):
    def rate(g):
        x = res[g]
        return f"{x['rate'] * 100:.0f}% ({x['tender_hits']}/{x['tenders']} tenders, {x['buyers']} buyers)" if x['buyers'] else 'NA'
    ci = f" [{res['lr_ci'][0]}, {res['lr_ci'][1]}]" if res.get('lr_ci') else ''
    pci = f" [{res['proposed_points_ci'][0]}, {res['proposed_points_ci'][1]}]" if res.get('proposed_points_ci') else ''
    return (f"| {res['check']}{' ' + res['band'] if res.get('band') else ''} | {rate('combined')} | {rate('corruption')} | {rate('fraud')} | "
            f"{rate('comparison')} | {res['lr_raw']} | {res['lr_shrunk']}{ci} | {res['proposed_points']}{pci} | {res.get('current', '')} |")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('rows', help='per-row checks JSON from analyze-ukraine-verdict-cohort.cjs')
    p.add_argument('--changes', help='amendment features JSON from fetch-verdict-contract-changes.py')
    p.add_argument('--json', help='write full results here')
    p.add_argument('--positive-labels', default=','.join(POSITIVE),
                   help='labels pooled as positives (e.g. collusion for the AMCU bid-rigging cohort)')
    args = p.parse_args(argv)
    rows, skipped = load_rows(args.rows, args.changes, tuple(args.positive_labels.split(',')))
    checks = sorted({k for r in rows for k in r['checks']})
    results = []
    for check in checks:
        res = analyse(rows, check)
        cur = current_points(rows, check)
        res['current'] = '' if cur is None else (f'{cur[0]:g}' if cur[0] == cur[1] else f'{cur[0]:g}–{cur[1]:g}')
        if res['combined']['buyers'] or res['comparison']['buyers']:
            results.append(res)
            results += bands(rows, check)
    if args.changes:
        for lo, hi in ((1, 2), (3, 4), (5, 10**6)):
            res = analyse(rows, AMENDMENT_CHECK, lambda c, lo=lo, hi=hi: lo <= c.get('changes', 0) <= hi)
            results.append(dict(res, band=f'{lo}–{hi if hi < 10**6 else ""} amendments'))
    positives = [r for r in rows if 'combined' in r['groups']]
    print(f"{len(positives)} eligible positive rows ({len({r['buyer'] for r in positives})} buyers); "
          f"{sum('comparison' in r['groups'] for r in rows)} comparison rows. Prior {PRIOR_BUYERS} buyers; PDO {PDO}; {BOOT} buyer resamples.")
    print(f"Competitive procedures only; left out (direct-award reports and negotiated procedures): {skipped or 'none'}.\n")
    print('| Check | Hit rate, all convicted | Corruption | Fraud | Comparisons | LR+ raw | LR+ shrunk [95 %] | Proposed points [95 %] | Current points |')
    print('|---|---|---|---|---|---|---|---|---|')
    main_rows = sorted((r for r in results if not r.get('band')), key=lambda r: -(r['combined']['rate'] or 0))
    for r in main_rows:
        print(fmt(r))
    print('\nStrength bands\n')
    print('| Check / band | Hit rate, all convicted | Corruption | Fraud | Comparisons | LR+ raw | LR+ shrunk [95 %] | Proposed points [95 %] | |')
    print('|---|---|---|---|---|---|---|---|---|')
    for r in results:
        if r.get('band'):
            print(fmt(r))
    if args.json:
        Path(args.json).write_text(json.dumps({'prior_buyers': PRIOR_BUYERS, 'pdo': PDO, 'bootstrap': BOOT, 'seed': SEED,
                                               'left_out_non_competitive': skipped, 'results': results}, indent=1) + '\n')


if __name__ == '__main__':
    main()
