#!/usr/bin/env python3
"""Research only: pairs of group indicators (korea-labels-plan.md, "Pairs, fixed 2026-10-27", same-rival amendment of
the same day). Reads measures.tsv and rivals.tsv.gz of tools/korea-group-measures.py and writes measures.tsv again with
P1-P6 appended; rated by tools/korea-curves.py --group.

Per rival r of the opening, each continuous member (g1_r, g3_r, g5_r) becomes its oriented mid-rank percentile among
all (opening, rival) rows where it is known (label-blind; high = suspicious). A pair's score for r is the smaller of
its members' ranks, or a member's rank where r's flag (futile bid, pick match, consortium) is yes, else 0; P5 is yes/no
(shared contact and pick match on one rival). The opening's score is the maximum over its rivals.

--any-rival: the first version (members taken from measures.tsv, possibly from different rivals), kept to reproduce
group/rate19-*.
"""
import argparse
import gzip
from collections import defaultdict
from pathlib import Path

import numpy as np

GROUP = Path.home() / '.cache/contract-signals/korea/group'
# +1: high is suspicious, -1: low is suspicious; G5's 1,000 ("no repeated pair") is ranked lowest by the sign alone.
DIRECTION = {'G1': 1, 'G3': 1, 'G5': -1, 'G6': 1, 'G7': 1}
FLAGS = {'G9', 'G10'}
PAIRS = {'P1': ('G1', 'G3'), 'P2': ('G1', 'G5'), 'P3': ('G1', 'G6'), 'P4': ('G5', 'G7'), 'P5': ('G7', 'G9'),
         'P6': ('G1', 'G10')}


def ranks(values, sign):
    """Mid-rank percentile in (0, 1) of sign * value among the known values; NaN stays NaN."""
    out = np.full(len(values), np.nan)
    known = ~np.isnan(values)
    x = sign * values[known]
    s = np.sort(x)
    below = np.searchsorted(s, x, 'left')
    upto = np.searchsorted(s, x, 'right')
    out[known] = (below + upto) / 2 / len(s)
    return out


def any_rival(head, rows):
    """The first version: pairs of the opening-level members, possibly from different rivals."""
    col = {name: np.array([float(r[i]) if r[i] != '' else np.nan for r in rows]) for i, name in enumerate(head)
           if name in DIRECTION or name in FLAGS}
    rank = {name: ranks(col[name], sign) for name, sign in DIRECTION.items()}
    pairs = {}
    for pid, (x, y) in PAIRS.items():
        if y in FLAGS:
            flag = col[y]
            pairs[pid] = np.where(np.isnan(flag) | np.isnan(rank[x]), np.nan, np.where(flag > 0, rank[x], 0.0))
        else:
            pairs[pid] = np.minimum(rank[x], rank[y])
    return pairs


def rival_scores(r1, r3, r5, futile, pick, contact, joint):
    """P1-P6 for one (opening, rival) row; arguments are ranks or 0/1 flags, NaN = unknown."""
    def gated(rank, flag):
        return np.nan if np.isnan(flag) or np.isnan(rank) else (rank if flag > 0 else 0.0)
    return {'P1': np.minimum(r1, r3), 'P2': np.minimum(r1, r5), 'P3': gated(r1, futile), 'P4': gated(r5, pick),
            'P5': np.nan if np.isnan(contact) or np.isnan(pick) else float(contact > 0 and pick > 0),
            'P6': gated(r1, joint)}


def same_rival(head, rows, rivals_path):
    """Per opening, the maximum over its rivals of the same-rival pair scores (plan amendment 2026-10-27)."""
    with gzip.open(rivals_path, 'rt', encoding='utf-8') as f:
        rhead = f.readline().rstrip('\n').split('\t')
        rrows = [line.rstrip('\n').split('\t') for line in f]
    col = {name: np.array([float(r[i]) if r[i] != '' else np.nan for r in rrows]) for i, name in enumerate(rhead)
           if i >= 3}
    r1, r3, r5 = ranks(col['g1'], 1), ranks(col['g3'], 1), ranks(col['g5'], -1)
    best = defaultdict(dict)  # every opening with a rival row gets an entry, possibly empty (all unknown)
    for i, r in enumerate(rrows):
        scores = rival_scores(r1[i], r3[i], r5[i], col['futile'][i], col['pick'][i], col['contact'][i], col['joint'][i])
        mine = best[(r[0], r[1])]
        for pid, v in scores.items():
            if not np.isnan(v) and not (mine.get(pid, -1.0) >= v):
                mine[pid] = v
    idx = {(r[head.index('notice')], r[head.index('ord')]): i for i, r in enumerate(rows)}
    pairs = {pid: np.full(len(rows), np.nan) for pid in PAIRS}
    # An opening with G1 known but no rival row (G1 = 0 there) scores 0 on P1-P3, as the opening-level members would.
    g1 = np.array([r[head.index('G1')] != '' and (r[head.index('notice')], r[head.index('ord')]) not in best
                   for r in rows])
    for pid in ('P1', 'P2', 'P3'):
        pairs[pid][g1] = 0.0
    for key, scores in best.items():
        i = idx.get(key)
        if i is not None:
            for pid, v in scores.items():
                pairs[pid][i] = v
    return pairs


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--measures', type=Path, default=GROUP / 'measures.tsv')
    p.add_argument('--rivals', type=Path, default=GROUP / 'rivals.tsv.gz')
    p.add_argument('--out', type=Path, default=GROUP / 'measures-pairs.tsv')
    p.add_argument('--any-rival', action='store_true', help='the first version (group/rate19-*)')
    a = p.parse_args()
    with open(a.measures, encoding='utf-8') as f:
        head = f.readline().rstrip('\n').split('\t')
        rows = [line.rstrip('\n').split('\t') for line in f]
    pairs = any_rival(head, rows) if a.any_rival else same_rival(head, rows, a.rivals)
    with open(a.out, 'w', encoding='utf-8') as f:
        f.write('\t'.join(head + list(PAIRS)) + '\n')
        for i, r in enumerate(rows):
            f.write('\t'.join(r + ['' if np.isnan(pairs[pid][i]) else f'{pairs[pid][i]:.6f}' for pid in PAIRS]) + '\n')
    for pid, v in pairs.items():
        print(f'{pid} {PAIRS[pid]}: known {int((~np.isnan(v)).sum())}, mean {np.nanmean(v):.3f}')
    print(f'-> {a.out}')


if __name__ == '__main__':
    main()
