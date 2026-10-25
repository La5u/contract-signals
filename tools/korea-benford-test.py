#!/usr/bin/env python3
"""Exploratory: Benford first-two-digit deviation (MAD) per supplier; labelled firms vs other firms."""
import sqlite3, json, math, collections, os, gzip, random
K = os.path.expanduser('~/.cache/contract-signals/korea')
c = sqlite3.connect(f'file:{K}/opnstd.sqlite?mode=ro', uri=True)
B1 = {d: math.log10(1 + 1 / d) for d in range(1, 10)}
B2 = {d: math.log10(1 + 1 / d) for d in range(10, 100)}
first1 = collections.Counter(); by_firm = collections.defaultdict(collections.Counter)
for amount, bizno in c.execute("SELECT amount, supplier_bizrno FROM versions WHERE ord = 0 OR ord IS NULL"):
    if not amount or amount < 100: continue
    s = str(int(amount))
    first1[int(s[0])] += 1
    if bizno: by_firm[bizno.replace('-', '')][int(s[:2])] += 1
n = sum(first1.values())
print('all contracts, first digit: observed vs Benford')
for d in range(1, 10): print(f'  {d}: {first1[d]/n:6.2%}  {B1[d]:6.2%}')
def mad(cnt):
    t = sum(cnt.values()); return sum(abs(cnt[d] / t - B2[d]) for d in B2) / 90
firms = {b: (sum(v.values()), mad(v)) for b, v in by_firm.items() if sum(v.values()) >= 50}
print('firms with >= 50 contracts:', len(firms))
# labelled firms
lab = collections.defaultdict(set)
for l in open(f'{K}/debarments/links-2026-10-24.jsonl'):
    lab['debarred (fraud-type)'].add(json.loads(l)['bizno'])
for l in open(f'{K}/ftc/extract/links.jsonl'):
    x = json.loads(l)
    if x['link'] in ('notice', 'amount', 'amount-buyer', 'buyer-name'):
        b = (x['candidates'][0].get('supplier_bizrno') or '').replace('-', '')
        if b: lab['cartel winners (KFTC)'].add(b)
for l in open(f'{K}/prec/extract/links.jsonl'):
    x = json.loads(l)
    if x['link'] not in ('unmatched', 'ambiguous') and x.get('candidates'):
        b = (x['candidates'][0].get('supplier_bizrno') or '').replace('-', '')
        if b: lab['court-linked suppliers'].add(b)
# size bands (MAD falls with more contracts, so compare within bands)
def band(n): return 0 if n < 100 else 1 if n < 300 else 2 if n < 1000 else 3
bands = collections.defaultdict(list)
for b, (n, m) in firms.items(): bands[band(n)].append(m)
for k in bands: bands[k].sort()
def pct(n, m):  # percentile of this firm's MAD among firms of its size band
    xs = bands[band(n)]; lo = 0; hi = len(xs)
    while lo < hi:
        mid = (lo + hi) // 2
        if xs[mid] < m: lo = mid + 1
        else: hi = mid
    return lo / len(xs)
allp = [pct(n, m) for n, m in firms.values()]
top = lambda ps: sum(p >= 0.9 for p in ps) / len(ps)
print(f'all firms: mean percentile {sum(allp)/len(allp):.2f}, share in worst 10 % {top(allp):.1%}')
for name, ids in lab.items():
    ps = [pct(*firms[b]) for b in ids if b in firms]
    if not ps: print(name, 'no firm with >= 50 contracts'); continue
    rnd = random.Random(1); boots = sorted(sum(rnd.choice(ps) for _ in ps) / len(ps) for _ in range(2000))
    print(f'{name}: {len(ids)} firms, {len(ps)} with >= 50 contracts; mean percentile {sum(ps)/len(ps):.2f} '
          f'[{boots[50]:.2f}, {boots[1949]:.2f}], in worst 10 % {top(ps):.1%}')
