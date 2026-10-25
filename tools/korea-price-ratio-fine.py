#!/usr/bin/env python3
"""Research only: award / reserve price in 0.1 % bins, 70-100 %, rated bin by bin and graphed (owner request 2026-10-25).

Plan: research/calibration/korea-labels-plan.md, "Fine scan". Records, labels and weights as tools/korea-curves.py
(decision basis: all linked tenders). Per bin: buyer-weighted label and comparison shares, the decision rule's shrunk
LR (10-buyer prior), 2.5/25/97.5 % of 2,000 buyer resamples, points 10 x log2 of the 25th percentile; Benjamini-
Hochberg at 10 % on the resample share with LR <= 1. Replication: labelled cases in two halves by hash; correlation
of the label counts' fine-scale excess (over a +-1 % moving average) between halves against draws
from the smoothed label distribution and random case halves.
Writes <out>/price-ratio-fine-<name>.{svg,png,json}. --load reuses a saved .npz instead of the database.
"""
import argparse
import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('kc', ROOT / 'tools/korea-curves.py')
kc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(kc)
lc, pp = kc.lc, kc.pp

LO, HI, STEP = 0.70, 1.00, 0.001
NB = int(round((HI - LO) / STEP))  # 300 inner bins; index 0 = below LO, NB + 1 = at or above HI
WINDOW = 21                        # moving average for the fine-scale excess: +-1 %
DRAWS = 500
FDR = 0.10


def na(v, digits=3):
    return 'NA' if v is None or not np.isfinite(v) else f'{v:.{digits}f}'


def cells(x):
    i = np.floor(np.round((x - LO) / STEP, 9)).astype(int) + 1
    return np.clip(i, 0, NB + 1)


def half(case):
    return int(hashlib.sha256(f'half-{case}'.encode()).hexdigest()[:8], 16) % 2


def buyer_matrix(cell, buyer, w, mask, nb):
    """(buyer x bin) shares, each buyer adding its largest weight over its records (pp.weighted), and that weight."""
    m = np.zeros((nb, NB + 2))
    eff = np.where(mask, w, 0.0)
    sumw = np.bincount(buyer, eff, nb)
    maxw = np.zeros(nb)
    np.maximum.at(maxw, buyer, np.where(mask, w, 0.0))
    share = np.divide(eff * maxw[buyer], sumw[buyer], out=np.zeros_like(eff), where=sumw[buyer] > 0)
    np.add.at(m, (buyer, cell), share)
    return m, maxw


def shrunk(h1, n1, h0, n0):
    p0 = (h0 + 0.5) / (n0 + 1)
    p1 = (h1 + pp.PRIOR_BUYERS * p0) / (n1 + pp.PRIOR_BUYERS)
    return p1 / p0


def rate(cell, lab, w, buyer, nb, rng):
    m1, b1 = buyer_matrix(cell, buyer, w, lab, nb)
    m0, b0 = buyer_matrix(cell, buyer, w, ~lab, nb)
    lr = shrunk(m1.sum(0), b1.sum(), m0.sum(0), b0.sum())
    draws = np.full((pp.BOOT, NB + 2), np.nan)
    for k in range(pp.BOOT):
        mult = np.bincount(rng.integers(0, nb, nb), minlength=nb).astype(float)
        if mult @ b1 and mult @ b0:  # a draw without labels or comparisons is rejected, as shrunk_lr does
            draws[k] = shrunk(mult @ m1, mult @ b1, mult @ m0, mult @ b0)
    ok = ~np.isnan(draws[:, 0])
    if ok.sum() < pp.BOOT / 2:
        q = np.full((3, NB + 2), np.nan)
    else:
        q = np.quantile(draws[ok], [0.025, pp.CONFIDENT_Q, 0.975], axis=0)
    p_le1 = (draws[ok] <= 1).mean(0)
    # Points only with at least MIN_BUYERS labelled buyers (buyer weight), as propose-indicator-points.analyse.
    eligible = b1.sum() >= pp.MIN_BUYERS
    return {'label_share': m1.sum(0) / b1.sum(), 'comp_share': m0.sum(0) / b0.sum(), 'lr': lr, 'lo': q[0],
            'conf': np.minimum(q[1], lr), 'hi': q[2], 'p': p_le1, 'label_buyers': int((b1 > 0).sum()), 'eligible': eligible}


def bh(p, alpha):
    order = np.argsort(p)
    ok = p[order] <= alpha * np.arange(1, len(p) + 1) / len(p)
    keep = np.zeros(len(p), bool)
    if ok.any():
        keep[order[:np.nonzero(ok)[0].max() + 1]] = True
    return keep


_SMOOTHERS = {}


def movavg(v):
    """Local-linear smooth over a +-1 % window, truncated at the ends: reproduces linear trends up to the edges (Sol
    review 2026-10-25: edge-padded moving averages made shared structure from a plain slope). A fixed linear
    operator, built once per length."""
    n, h = len(v), WINDOW // 2
    if n not in _SMOOTHERS:
        S = np.zeros((n, n))
        for i in range(n):
            lo, hi = max(0, i - h), min(n, i + h + 1)
            t = np.arange(lo, hi) - i
            A = np.vstack([np.ones(len(t)), t]).T
            S[i, lo:hi] = np.linalg.pinv(A)[0]
        _SMOOTHERS[n] = S
    return _SMOOTHERS[n] @ v


def resid(counts, comp):
    """Fine-scale excess of label counts, in standard units, over what the smooth label curve predicts once the
    comparisons' own fine structure (heaping at legal floors) is applied: expected = movavg(labels) x comp /
    movavg(comp). Labels only carry noise: the comparisons are ~300k records."""
    e = np.maximum(movavg(counts) * comp / np.maximum(movavg(comp), 1e-12), 1e-9)
    e = e * counts.sum() / e.sum()
    return (counts - e) / np.sqrt(e)


def replication(cell, lab, case, comp_share, rng):
    """Correlation of the two case halves' fine-scale excess, counting cases rather than tenders: each case at most
    once per bin, so a case with many tenders at one price counts once and cases are close to independent units.
    Null: each half's case-bin counts drawn from the smooth curve times the comparisons' own heaping (Sol review
    2026-10-25: tender-level draws ignored clustering). Random case halves are descriptive only."""
    hs = np.array([half(c) for c in case])
    comp = comp_share[1:NB + 1]

    def counts(m):
        sel = lab & m & (cell >= 1) & (cell <= NB)
        pairs = np.unique(np.stack([case[sel], cell[sel] - 1]), axis=1)
        return np.bincount(pairs[1], minlength=NB).astype(float)

    def corr(a, b):
        if a.sum() < 2 or b.sum() < 2:
            return float('nan')
        ra, rb = resid(a, comp), resid(b, comp)
        if ra.std() == 0 or rb.std() == 0:
            return float('nan')
        return float(np.corrcoef(ra, rb)[0, 1])

    halves = [counts(hs == h) for h in (0, 1)]
    obs = corr(*halves)
    both = halves[0] + halves[1]
    smooth = np.maximum(movavg(both), 0) * comp / np.maximum(movavg(comp), 1e-12)
    smooth = smooth / smooth.sum()
    null = np.array([corr(*(rng.multinomial(int(h.sum()), smooth).astype(float) for h in halves)) for _ in range(DRAWS)])
    null = null[np.isfinite(null)]
    cases = np.unique(case[lab])
    splits = []
    for _ in range(DRAWS):
        m = np.isin(case, rng.choice(cases, len(cases) // 2, replace=False))
        splits.append(corr(counts(m), counts(~m)))
    ok = np.isfinite(obs) and len(null) >= DRAWS / 2
    return {'corr': obs, 'null_95': float(np.quantile(null, 0.95)) if ok else None,
            'null_mean': float(null.mean()) if ok else None, 'p': float(np.mean(null >= obs)) if ok else None,
            'random_splits_mean': float(np.nanmean(splits)), 'case_bins_per_half': [int(h.sum()) for h in halves]}


def svg(name, title, r, rep, flagged, half_lr):
    W, H, L, R = 1500, 900, 80, 70
    panels = [(60, 300), (400, 640), (700, 860)]  # (top, bottom) y of the three panels
    x = lambda i: L + (i - 0.5) / NB * (W - L - R)  # i = inner bin 1..NB, centre
    bw = (W - L - R) / NB
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" font-family="sans-serif" font-size="12">',
           f'<rect width="{W}" height="{H}" fill="white"/>',
           f'<text x="{L}" y="30" font-size="17" font-weight="bold">{title}</text>']
    inner = slice(1, NB + 1)
    ls, cs = r['label_share'][inner] * 100, r['comp_share'][inner] * 100
    top = max(ls.max(), 3 * np.quantile(cs, 0.99)) * 1.05  # heaping at a legal floor would flatten the rest: clipped
    t, b = panels[0]
    ys = lambda v: b - min(v, top) / top * (b - t)
    out.append(f'<text x="{L}" y="{t - 8}">Share of contracts per 0.1 % bin (buyer-weighted): '
               f'<tspan fill="#888">comparisons</tspan>, <tspan fill="#c0392b">labelled</tspan></text>')
    for i in range(NB):
        out.append(f'<rect x="{x(i + 1) - bw / 2:.1f}" y="{ys(cs[i]):.1f}" width="{bw:.2f}" height="{b - ys(cs[i]):.1f}" fill="#bbb"/>')
        if cs[i] > top:
            out.append(f'<text x="{x(i + 1):.1f}" y="{t + 12}" text-anchor="middle" fill="#666">{cs[i]:.0f}% ▲</text>')
    pts = ' '.join(f'{x(i + 1):.1f},{ys(ls[i]):.1f}' for i in range(NB))
    out.append(f'<polyline points="{pts}" fill="none" stroke="#c0392b" stroke-width="1.3"/>')
    for v in np.linspace(0, top, 5)[1:]:
        out.append(f'<text x="{L - 6}" y="{ys(v) + 4:.1f}" text-anchor="end">{v:.1f}%</text>'
                   f'<line x1="{L}" x2="{W - R}" y1="{ys(v):.1f}" y2="{ys(v):.1f}" stroke="#eee"/>')
    # LR panel, log2 scale
    lo_v, hi_v = -3, 5
    t, b = panels[1]
    yl = lambda v: b - (np.clip(np.log2(v), lo_v, hi_v) - lo_v) / (hi_v - lo_v) * (b - t)
    out.append(f'<text x="{L}" y="{t - 8}">Likelihood ratio per bin (shrunk, log scale), 95 % band; '
               f'<tspan fill="#1f6fb2">LR</tspan>, <tspan fill="#e67e22">25th percentile (decision rule)</tspan>, '
               f'red dot = above 1 after Benjamini–Hochberg 10 %</text>')
    band = [f'{x(i):.1f},{yl(r["hi"][i]):.1f}' for i in range(1, NB + 1)] + \
           [f'{x(i):.1f},{yl(r["lo"][i]):.1f}' for i in range(NB, 0, -1)]
    out.append(f'<polygon points="{" ".join(band)}" fill="#1f6fb2" fill-opacity="0.15"/>')
    for key, col in (('lr', '#1f6fb2'), ('conf', '#e67e22')):
        out.append(f'<polyline points="{" ".join(f"{x(i):.1f},{yl(r[key][i]):.1f}" for i in range(1, NB + 1))}" '
                   f'fill="none" stroke="{col}" stroke-width="1.3"/>')
    for i in np.nonzero(flagged)[0]:
        out.append(f'<circle cx="{x(i):.1f}" cy="{yl(r["lr"][i]):.1f}" r="3" fill="#c0392b"/>')
    for v in (0.125, 0.25, 0.5, 1, 2, 4, 8, 16, 32):
        pts_ = max(0, 10 * np.log2(v))
        out.append(f'<line x1="{L}" x2="{W - R}" y1="{yl(v):.1f}" y2="{yl(v):.1f}" stroke="{"#555" if v == 1 else "#eee"}"/>'
                   f'<text x="{L - 6}" y="{yl(v) + 4:.1f}" text-anchor="end">{v:g}</text>'
                   f'<text x="{W - R + 6}" y="{yl(v) + 4:.1f}">{pts_:.0f} pts</text>')
    # halves panel
    t, b = panels[2]
    out.append(f'<text x="{L}" y="{t - 8}">Two halves of the labelled cases (shrunk LR, log scale): '
               f'<tspan fill="#16a085">half A</tspan>, <tspan fill="#8e44ad">half B</tspan>. Fine-scale correlation (cases once per bin) '
               f'{na(rep["corr"], 2)} (null 95th percentile {na(rep["null_95"], 2)}, p = {na(rep["p"])})</text>')
    yh = lambda v: b - (np.clip(np.log2(v), -3, 5) + 3) / 8 * (b - t)
    for hl, col in zip(half_lr, ('#16a085', '#8e44ad')):
        out.append(f'<polyline points="{" ".join(f"{x(i):.1f},{yh(hl[i]):.1f}" for i in range(1, NB + 1))}" '
                   f'fill="none" stroke="{col}" stroke-width="1.1"/>')
    out.append(f'<line x1="{L}" x2="{W - R}" y1="{yh(1):.1f}" y2="{yh(1):.1f}" stroke="#555"/>')
    for v in (0.25, 1, 4, 16):
        out.append(f'<text x="{L - 6}" y="{yh(v) + 4:.1f}" text-anchor="end">{v:g}</text>')
    for pct in range(70, 101, 1):
        i = (pct / 100 - LO) / STEP + 0.5
        major = pct % 5 == 0
        for t, b in panels:
            out.append(f'<line x1="{x(i):.1f}" x2="{x(i):.1f}" y1="{t}" y2="{b}" stroke="{"#ccc" if major else "#f2f2f2"}"/>')
        if major or pct >= 85:
            out.append(f'<text x="{x(i):.1f}" y="{panels[2][1] + 18}" text-anchor="middle">{pct}</text>')
    out.append(f'<text x="{W / 2}" y="{H - 8}" text-anchor="middle">Award ÷ reserve price, % (bins of 0.1 %)</text></svg>')
    return '\n'.join(out)


def main():
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--name', required=True, help='collusion, court or audit (file names and title)')
    p.add_argument('--family', choices=('collusion', 'corruption', 'both'), default='collusion')
    p.add_argument('--court-links', type=Path, default=lc.BASE / 'prec/extract/links.jsonl')
    p.add_argument('--db', type=Path, default=lc.BASE / 'opnstd.sqlite')
    p.add_argument('--buyer', choices=('contract', 'demand'), default='contract')
    p.add_argument('--out', type=Path, default=lc.BASE / 'plots')
    p.add_argument('--load', action='store_true', help='reuse <out>/price-ratio-<name>.npz')
    args = p.parse_args()
    args.out.mkdir(exist_ok=True)
    npz = args.out / f'price-ratio-{args.name}.npz'
    if args.load:
        z = np.load(npz, allow_pickle=True)
        xv, lab, w, buyer, case = z['x'], z['lab'], z['w'], z['buyer'], z['case']
    else:
        rows, _, _ = lc.prepare(args, lambda contracts: (lambda c: {'PRICE-RATIO': kc.price_ratio(c)}))
        d = kc.Data(rows(lambda c: True, True), 'PRICE-RATIO')
        xv, lab, w, buyer, case = d.x, d.lab, d.w, d.buyer, d.case
        np.savez_compressed(npz, x=xv, lab=lab, w=w, buyer=buyer, case=case)
    nb = int(buyer.max()) + 1
    cell = cells(xv)
    rng = np.random.default_rng(20261025)
    r = rate(cell, lab, w, buyer, nb, rng)
    inner = np.zeros(NB + 2, bool)
    inner[1:NB + 1] = True
    flagged = inner & bh(np.where(inner, r['p'], 1.0), FDR) & (r['lr'] > 1)
    rep = replication(cell, lab, case, r['comp_share'], rng)
    hs = np.array([half(c) for c in case])
    m0, b0 = buyer_matrix(cell, buyer, w, ~lab, nb)
    half_lr = []
    for h in (0, 1):  # each half's labels against all comparisons
        m1, b1 = buyer_matrix(cell, buyer, w, lab & (hs == h), nb)
        half_lr.append(shrunk(m1.sum(0), b1.sum(), m0.sum(0), b0.sum()))
    n_lab, n_cases = int(lab.sum()), len(set(case[lab].tolist()))
    case_count = np.array([len(set(case[lab & (cell == i)].tolist())) for i in range(NB + 2)])
    title = (f'Korea, {args.name} labels: award ÷ reserve, 0.1 % bins ({n_lab} labelled tenders, {n_cases} cases, '
             f'{r["label_buyers"]} buyers; {int((~lab).sum()):,} comparisons)')
    (args.out / f'price-ratio-fine-{args.name}.svg').write_text(svg(args.name, title, r, rep, flagged, half_lr))
    subprocess.run(['magick', '-density', '110', str(args.out / f'price-ratio-fine-{args.name}.svg'),
                    str(args.out / f'price-ratio-fine-{args.name}.png')], check=False)
    label = lambda i: '< 70 %' if i == 0 else '>= 100 %' if i == NB + 1 else f'{(LO + (i - 1) * STEP) * 100:.1f} %'
    print(title)
    print(f'below 70 %: labels {r["label_share"][0] * 100:.1f} %, comparisons {r["comp_share"][0] * 100:.1f} %; '
          f'at or above 100 %: labels {r["label_share"][-1] * 100:.1f} %, comparisons {r["comp_share"][-1] * 100:.1f} %')
    print(f'bins with the 95 % band above 1: {int((inner & (r["lo"] > 1)).sum())} of {NB} '
          f'(about {NB * 0.025:.0f} expected by chance); above 1 after Benjamini-Hochberg {FDR:.0%}: {int(flagged.sum())}')
    print(f'replication (cases counted once per bin): correlation between case halves {na(rep["corr"])}; null mean '
          f'{na(rep["null_mean"])}, 95th percentile {na(rep["null_95"])}, p = {na(rep["p"])}; random case halves mean '
          f'{na(rep["random_splits_mean"])} (descriptive); case-bins per half {rep["case_bins_per_half"]}')
    print('\n| Bin | Labelled | Comparisons | LR [95 %] | Points (25th pct) | Cases | Half A / B LR | BH |')
    print('|---|---|---|---|---|---|---|---|')
    for i in sorted(range(NB + 2), key=lambda i: -r['conf'][i])[:25]:
        print(f'| {label(i)} | {r["label_share"][i] * 100:.2f} % | {r["comp_share"][i] * 100:.2f} % | {r["lr"][i]:.2f} '
              f'[{r["lo"][i]:.2f}, {r["hi"][i]:.2f}] | {pp.points(r["conf"][i]) if r["eligible"] else "too few buyers"} | {case_count[i]} | {half_lr[0][i]:.2f} / {half_lr[1][i]:.2f} | '
              f'{"yes" if flagged[i] else ""} |')
    (args.out / f'price-ratio-fine-{args.name}.json').write_text(json.dumps({
        'bins': [{'bin': label(i), **{k: float(r[k][i]) for k in ('label_share', 'comp_share', 'lr', 'lo', 'conf', 'hi', 'p')},
                  'half_lr': [float(half_lr[0][i]), float(half_lr[1][i])], 'cases': int(case_count[i]), 'bh': bool(flagged[i])} for i in range(NB + 2)],
        'replication': rep}, indent=1) + '\n')


if __name__ == '__main__':
    main()
