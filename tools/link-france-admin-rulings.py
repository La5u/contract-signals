#!/usr/bin/env python3
"""Research only: link the contracts named in French administrative-court rulings to the national DECP
(research/calibration/france-labels-plan.md, "Contracts and linking").

Class per ruling (plan notes of 2026-10-30): Dawid-Skene over all readings (Luna, Haiku, DeepSeek, Terra; readers
identified by model): EM estimates each reader's confusion matrix and the class frequencies of court-reported wins
and rejections, and gives each ruling a probability per class. The most probable class decides which rulings are
linked (A1-A3 labels, C litigated comparison); its probability is stored, and uses weight a label by class
probability x link probability. The contracts are those of the most accurate reader who read that class.
Linking (plan notes 2026-10-30, linking): Fellegi-Sunter record linkage. Candidates are all DECP contracts of the
buyers whose names could be meant (blocking: the 10 best names by bigram overlap, overlap >= 0.5). Each field gives a
graded level: buyer name overlap; description and winner as the rarity-weighted share of the named words found (a word
counts log2(N / its frequency among the candidates' descriptions or suppliers)), SIREN equal one level above; amount as
|ln ratio|, the closest of with and without any French VAT rate; date gap in days. Weights log2(m / u) per level come
from EM over all pairs; a missing field adds nothing. A candidate's probability is its likelihood ratio against the
prior 1/N, with the prior that the contract is in DECP at all estimated (EM) for signed and unknown; contracts the ruling says were
not signed are not linked, since a DECP match could only be the relaunched procedure; several DECP
publications of one contract (same winner SIREN, dates within 7 days, same or missing amount) add up. No acceptance
cut: the best candidate and its probability are stored, and uses weight a link by its probability.
Every unresolved case is written with its reason.

Output: france-admin/links/links.jsonl (one line per named contract), summary.json; stdout: counts.
"""
import argparse
import datetime as dt
import json
import os
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import duckdb
import numpy as np

CACHE = Path(os.environ.get('XDG_CACHE_HOME', str(Path.home() / '.cache'))) / 'contract-signals'
BASE = CACHE / 'france-admin'
READERS = ('extract', 'extract-haiku', 'extract-luna', 'extract-deepseek')  # first reading, then second readers, in this order
LINKED = {'A1', 'A2', 'A3', 'C'}
STOP = {'de', 'du', 'des', 'la', 'le', 'les', 'l', 'd', 'et', 'en', 'a', 'au', 'aux', 'sur', 'pour', 'sa', 'sas',
        'sarl', 'societe', 'ste', 'commune', 'ville', 'mairie'}


def norm(s):
    s = unicodedata.normalize('NFKD', (s or '').lower())
    s = ''.join(ch for ch in s if not unicodedata.combining(ch))
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def bigrams(s):
    s = re.sub(r'\s', '', norm(s))
    return {s[i:i + 2] for i in range(len(s) - 1)}


def overlap(a, b):
    """Share of the shorter text's bigrams found in the other."""
    a, b = bigrams(a), bigrams(b)
    return len(a & b) / min(len(a), len(b)) if a and b else 0.0


def tokens(s):
    return {w for w in norm(s).split() if len(w) >= 3 and w not in STOP}


def words(s):
    """Words other than articles and legal forms, plural -s/-x dropped; how distinctive each is comes from its rarity."""
    return {re.sub(r'(?<=...)[sx]$', '', w) for w in norm(s).split() if len(w) >= 2 and w not in STOP}


def pseudonymised(name):
    """Published rulings replace some parties by letters ("société C et société D et fils"): no usable name."""
    return bool(re.search(r'\b(societe|ste|sarl|sas|entreprise|groupement)\s+[A-Z]\b', unicodedata.normalize(
        'NFKD', name or '').encode('ascii', 'ignore').decode().replace('Societe', 'societe'), re.I)) or not words(name)


def reading(d, rid):
    try:
        if json.loads((BASE / d / rid / 'status.json').read_text()).get('ok'):
            return json.loads((BASE / d / rid / 'result.json').read_text())
    except (OSError, json.JSONDecodeError):
        pass
    return None


def reader_of(d, rid):
    try:
        model = json.loads((BASE / d / rid / 'status.json').read_text()).get('model') or ''
    except (OSError, json.JSONDecodeError):
        return None
    return next((name for key, name in (('luna', 'luna'), ('haiku', 'haiku'), ('deepseek', 'deepseek'),
                                         ('terra', 'terra')) if key in model), model)


def settle_all(rids, rounds=200):
    """Dawid-Skene: each reader's confusion matrix (true class -> class read) and the class frequencies (separately
    for court-reported wins, first read by Luna, and rejections, first read by Haiku) estimated by EM from all
    readings; each ruling gets a probability per class. Second readings were chosen from the first reading's class,
    which EM handles (the choice depends only on observed readings). rid -> (most probable class, reading, how,
    {class: probability}); the reading is that of the most accurate reader who read that class, else of the most
    accurate reader."""
    reads = {}
    for rid in rids:
        got = []
        for d in READERS + ('extract-terra',):
            r = reading(d, rid)
            if r and r.get('outcome_class'):
                got.append((reader_of(d, rid), r))
        if got:
            reads[rid] = got
    classes = sorted({r['outcome_class'] for got in reads.values() for _, r in got})
    readers = sorted({who for got in reads.values() for who, _ in got})
    ci, ri = {c: i for i, c in enumerate(classes)}, {w: i for i, w in enumerate(readers)}
    stratum = {rid: reader_of('extract', rid) or 'other' for rid in reads}
    strata = sorted(set(stratum.values()))
    items = sorted(reads)
    obs = [[(ri[w], ci[r['outcome_class']]) for w, r in reads[rid]] for rid in items]
    K = len(classes)
    # start: share of readings per class
    T = np.array([np.bincount([c for _, c in o], minlength=K) / len(o) for o in obs])
    for _ in range(rounds):
        prior = {s_: T[[i for i, rid in enumerate(items) if stratum[rid] == s_]].mean(0) + 1e-3 for s_ in strata}
        conf = np.full((len(readers), K, K), 0.5)  # Jeffreys pseudo-counts
        for i, o in enumerate(obs):
            for w, c in o:
                conf[w, :, c] += T[i]
        conf /= conf.sum(2, keepdims=True)
        new = np.array([prior[stratum[rid]] * np.prod([conf[w, :, c] for w, c in o], axis=0) for rid, o in zip(items, obs)])
        new /= new.sum(1, keepdims=True)
        if np.abs(new - T).max() < 1e-6:
            T = new
            break
        T = new
    accuracy = {w: float(np.mean([conf[ri[w], k, k] for k in range(K)])) for w in readers}
    out = {}
    for i, rid in enumerate(items):
        cls = classes[int(T[i].argmax())]
        agree = [(accuracy[w], r) for w, r in reads[rid] if r['outcome_class'] == cls]
        best = max(agree or [(accuracy[w], r) for w, r in reads[rid]], key=lambda x: x[0])[1]
        out[rid] = (cls, best, 'dawid-skene', {c: round(float(T[i, k]), 4) for k, c in enumerate(classes)})
    for rid in rids:
        out.setdefault(rid, (None, None, 'no reading', {}))
    diag = {w: {c: round(float(conf[ri[w], k, k]), 3) for k, c in enumerate(classes)} for w in readers}
    return out, diag


def parse_date(s):
    try:
        return dt.date.fromisoformat(str(s)[:10])
    except (TypeError, ValueError):
        return None


def money(v):
    try:
        return float(str(v).replace(' ', '').replace(',', '.')) if v not in (None, '') else None
    except ValueError:
        return None


class Buyers:
    """DECP buyer names, indexed by token for candidate lookup."""

    def __init__(self, con):
        rows = con.execute("select acheteur_id, acheteur_nom, count(*) from decp where acheteur_id is not null "
                           "group by 1, 2").fetchall()
        self.names = defaultdict(set)  # normalised name -> SIRETs
        for sid, name, _ in rows:
            if name:
                self.names[norm(name)].add(sid)
        self.index = defaultdict(set)
        for name in self.names:
            for t in tokens(name):
                self.index[t].add(name)
        self.df = {t: len(v) for t, v in self.index.items()}

    def resolve(self, name):
        """SIRET -> name overlap for the buyers that could be meant (blocking: the 10 best names with overlap
        >= 0.5); how much the overlap counts is a linking field like the others."""
        toks = tokens(name)
        if not toks:
            return None, 'buyer name empty'
        # candidates share the rarest tokens of the ruling's name
        rare = sorted(toks, key=lambda t: self.df.get(t, 0))
        cands = set()
        for t in rare[:3]:
            if 0 < self.df.get(t, 0) <= 5000:
                cands |= self.index[t]
        scored = sorted(((overlap(name, c), c) for c in cands), reverse=True)
        scored = [(o, c) for o, c in scored[:10] if o >= 0.5]
        if not scored:
            return None, 'buyer not found in DECP'
        found = {}
        for o, c in scored:
            for sid in self.names[c]:
                found[sid] = max(found.get(sid, 0), o)
        return found, None


LEVELS = {  # level edges per field, fine enough that EM, not the edges, shapes the weights
    'object': (0, 0.2, 0.4, 0.6, 0.8, 0.95),   # rarity-weighted share of the named description's words found
    'winner': (0, 0.2, 0.4, 0.6, 0.8, 0.95),   # same for the winner's name; SIREN equal is one level above
    'amount': (0.0005, 0.01, 0.05, 0.2, 0.7),  # |ln ratio| of the amounts, the closest of with/without VAT
    'date': (1, 3, 7, 15, 30, 60, 120, 240, 365, 730),  # days between notification and the award or notice date
    'buyer': (0.6, 0.7, 0.8, 0.9, 0.999),      # bigram overlap of the buyer names (candidates have >= 0.5)
}
FIELDS = tuple(LEVELS)
NLEV = {f: len(e) + 1 + (f == 'winner') for f, e in LEVELS.items()}
DESCENDING = {'amount', 'date'}  # lower level = closer
VAT = (1, 1.055, 1.1, 1.2)       # French VAT rates: a ruling may quote either side of any of them


def weighted_share(named, published, idf):
    """Rarity-weighted share of the named words found in the published text (0 to 1)."""
    total = sum(idf(w) for w in named)
    return sum(idf(w) for w in named & published) / total if total else None


def level(field, x):
    if x is None:
        return None
    # object/winner: 0 = nothing shared ... 4 = (nearly) all; date: 0 = within 7 days ... 4 = over a year
    return int(sum(x > e for e in LEVELS[field]))


def features(k, contracts, buyer_overlap, df_cache):
    """Per candidate: level per field (None when a side lacks the field)."""
    n = len(contracts)
    key = tuple(sorted(buyer_overlap))
    if key not in df_cache:
        obj_df, win_df = Counter(), Counter()
        for c in contracts:
            obj_df.update(c['obj_words'])
            win_df.update(set().union(*c['win_words']) if c['win_words'] else set())
        df_cache[key] = obj_df, win_df
    obj_df, win_df = df_cache[key]
    obj_idf = lambda w: np.log2((n + 1) / (obj_df.get(w, 0) + 1))
    win_idf = lambda w: np.log2((n + 1) / (win_df.get(w, 0) + 1))
    named_obj = words(k.get('object'))
    name = None if pseudonymised(k.get('winner')) else k.get('winner')
    named_win = words(name)
    siren = re.sub(r'\D', '', str(k.get('winner_siren') or ''))[:9]
    amount = money(k.get('amount'))
    when = [d for d in (parse_date(k.get('award_date')), parse_date(k.get('notice_date'))) if d]
    out = []
    for c in contracts:
        f = {}
        f['object'] = level('object', weighted_share(named_obj, c['obj_words'], obj_idf)) if named_obj and c['obj_words'] else None
        if len(siren) == 9 and any(h and h[:9] == siren for h in c['holders']):
            f['winner'] = NLEV['winner'] - 1
        elif named_win and c['win_words']:
            f['winner'] = level('winner', max(weighted_share(named_win, w, win_idf) or 0 for w in c['win_words']))
        else:
            f['winner'] = None
        amounts = [m for m in c['amounts'] if m]
        f['amount'] = (level('amount', min(abs(np.log(m / (amount * r))) for m in amounts if m > 0
                                           for r in VAT + tuple(1 / v for v in VAT[1:])))
                       if amount and amount > 0 and any(m > 0 for m in amounts) else None)
        f['date'] = level('date', min(abs((c['date'] - d).days) for d in when)) if when and c['date'] else None
        f['buyer'] = level('buyer', buyer_overlap[c['buyer']])
        out.append(f)
    return out


def monotone(w, n):
    """Pool-adjacent-violators: the non-decreasing sequence closest to w, weighted by n (true-match counts)."""
    blocks = []
    for x, k in zip(w, n):
        blocks.append([x * k, k, 1])
        while len(blocks) > 1 and blocks[-2][0] / blocks[-2][1] > blocks[-1][0] / blocks[-1][1]:
            s1, k1, c1 = blocks.pop()
            blocks[-1][0] += s1
            blocks[-1][1] += k1
            blocks[-1][2] += c1
    return np.concatenate([np.full(c, s1 / k1) for s1, k1, c in blocks])


def em(rows, groups, rounds=200):
    """Fellegi-Sunter weights per field level, estimated under the model used for linking: each named contract is
    at most one of its N candidates (prior pi_g / N each, g = signed / not signed / unknown) or none of them.
    u (share among non-matches) is the level's share among all pairs, nearly all of which are non-matches. EM
    estimates m (share among true matches) and pi_g. Each round the weights log2(m / u) are made monotone in the
    field's direction (closer counts more; for the winner among the name levels), weighted by the estimated number
    of true matches per level. rows: per named contract, {field: array of levels, -1 = missing}."""
    cols = {f: np.concatenate([r[f] for r in rows]) for f in FIELDS}
    row_of = np.concatenate([np.full(len(r['object']), i) for i, r in enumerate(rows)])
    n_cand = np.array([len(r['object']) for r in rows], float)
    gid = {g: i for i, g in enumerate(sorted(set(groups)))}
    g_of = np.array([gid[g] for g in groups])
    pi = np.full(len(gid), 0.5)
    u = {f: np.bincount(cols[f][cols[f] >= 0], minlength=NLEV[f]) + 0.5 for f in FIELDS}
    u = {f: v / v.sum() for f, v in u.items()}
    weights = {f: np.log2((np.linspace(3, 1, NLEV[f]) if f in DESCENDING else np.linspace(1, 3, NLEV[f]))
                          / np.linspace(1, 3, NLEV[f]).sum() / u[f]) for f in FIELDS}
    for _ in range(rounds):
        sc = np.zeros(len(row_of))
        for f in FIELDS:
            ok = cols[f] >= 0
            sc[ok] += weights[f][cols[f][ok]]
        lr = np.exp2(np.minimum(sc, 60))
        prior = (pi[g_of] / n_cand)[row_of]
        total = np.bincount(row_of, weights=lr * prior, minlength=len(rows)) + (1 - pi[g_of])
        g = lr * prior / total[row_of]  # probability that the pair is the match
        in_decp = np.bincount(row_of, weights=g, minlength=len(rows))
        pi = np.clip(np.bincount(g_of, weights=in_decp) / np.bincount(g_of), 0.01, 0.99)
        new = {}
        for f in FIELDS:
            ok = cols[f] >= 0
            cnt = np.bincount(cols[f][ok], weights=g[ok], minlength=NLEV[f]) + 0.5
            w = np.log2(cnt / cnt.sum() / u[f])
            if f in DESCENDING:
                new[f] = -monotone(-w, cnt)
            elif f == 'winner':  # the SIREN level is not on the name scale
                new[f] = np.append(monotone(w[:-1], cnt[:-1]), w[-1])
            else:
                new[f] = monotone(w, cnt)
        if all(np.allclose(new[f], weights[f], atol=1e-4) for f in FIELDS):
            weights = new
            break
        weights = new
    return weights, {g: float(pi[i]) for g, i in gid.items()}


def score(f, weights):
    return sum(weights[k][v] for k, v in f.items() if v is not None)


def same_contract(c, d):
    """One contract published by several DECP sources (ids differing only by padding)."""
    a, b = {h[:9] for h in c['holders'] if h}, {h[:9] for h in d['holders'] if h}
    am, bm = {x for x in c['amounts'] if x}, {x for x in d['amounts'] if x}
    return bool(a & b and c['date'] and d['date'] and abs((c['date'] - d['date']).days) <= 7 and
                (am & bm or not am or not bm))


def link(contracts, lr, pi):
    """(best contract, its probability, duplicates, runner-up probability, probability it is in DECP at all).
    Duplicates only change the best candidates' mass, so only the 50 most likely are grouped."""
    n = len(contracts)
    clusters = []
    for i in np.argsort(-lr)[:50]:
        for cl in clusters:
            if same_contract(contracts[cl[0]], contracts[i]):
                cl.append(i)
                break
        else:
            clusters.append([i])
    total = lr.sum() * pi / n + (1 - pi)
    probs = sorted(((lr[cl].sum() * pi / n / total, cl) for cl in clusters), key=lambda x: -x[0])
    best_p, best = probs[0]
    return contracts[best[0]], float(best_p), [contracts[i]['uid'] for i in best[1:]], \
        float(probs[1][0]) if len(probs) > 1 else 0.0, float(lr.sum() * pi / n / total)


def contracts_by_buyer(con, sirets):
    """All DECP contracts of the given buyer SIRETs, one scan of the file."""
    rows = con.execute("select acheteur_id, uid, objet, montant, dateNotification, titulaire_id, titulaire_nom "
                       "from decp where acheteur_id in (select unnest(?))", [sorted(sirets)]).fetchall()
    by = {}
    for sid, uid, objet, montant, date, tid, tnom in rows:
        c = by.setdefault((sid, uid), {'uid': uid, 'buyer': sid, 'objet': objet, 'amounts': set(), 'date': date,
                                       'holders': set(), 'holder_names': set()})
        c['amounts'].add(montant)
        c['holders'].add(tid)
        c['holder_names'].add(tnom)
        if date and (not c['date'] or date < c['date']):
            c['date'] = date
    out = defaultdict(list)
    for c in by.values():
        c['obj_words'] = words(c['objet'])
        c['win_words'] = [words(h) for h in c['holder_names'] if h]
        out[c['buyer']].append(c)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--decp', type=Path, default=CACHE / 'decp-national-2026-10-30/decp.parquet')
    parser.add_argument('--out', type=Path, default=BASE / 'links')
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute(f"create view decp as select * from read_parquet('{args.decp}')")
    buyers = Buyers(con)
    rids = sorted({p.name for d in READERS + ('extract-terra',) for p in (BASE / d).iterdir() if p.is_dir()})
    stats, how_stats, out, todo = Counter(), Counter(), [], []
    settled, reader_accuracy = settle_all(rids)
    for rid in rids:
        cls, res, how, class_p = settled[rid]
        how_stats[how] += 1
        for c, x in class_p.items():
            stats['expected rulings ' + c] = round(stats['expected rulings ' + c] + x, 1)
        if cls not in LINKED:
            stats['ruling ' + (cls or how)] += 1
            continue
        stats['ruling ' + cls] += 1
        for i, k in enumerate(res.get('contracts') or []):
            row = {'ruling': rid, 'class': cls, 'class_probability': class_p.get(cls), 'class_probabilities': class_p,
                   'settled': how, 'contract': i, 'buyer': k.get('buyer'),
                   'object': k.get('object'), 'uid': None, 'probability': None, 'reason': None}
            if k.get('signed') is False:  # a DECP match could only be the relaunched procedure
                row['reason'] = 'not signed'
                out.append(row)
                continue
            found, why = buyers.resolve(k.get('buyer'))
            row['reason'] = why
            if found:
                todo.append((row, k, found))
            out.append(row)
    by_buyer = contracts_by_buyer(con, {sid for *_, found in todo for sid in found})
    df_cache, done = {}, []
    for row, k, found in todo:
        contracts = [c for sid in sorted(found) for c in by_buyer.get(sid, ())]
        if not contracts:
            row['reason'] = 'buyer has no DECP contract'
            continue
        done.append((row, k, contracts, features(k, contracts, found, df_cache)))
    group = lambda k: {True: 'signed', False: 'not signed'}.get(k.get('signed'), 'unknown')
    weights, prior = em([{f: np.array([-1 if x[f] is None else x[f] for x in feats]) for f in FIELDS}
                         for *_, feats in done], [group(k) for _, k, *_ in done])
    lrs = [np.exp2(np.minimum([score(f, weights) for f in feats], 60)) for *_, feats in done]
    for (row, k, contracts, feats), lr in zip(done, lrs):
        best, p, dups, runner, _ = link(contracts, lr, prior[group(k)])
        row.update(uid=best['uid'], probability=round(p, 4), runner_up=round(runner, 4),
                   same_contract=dups or None, levels=feats[contracts.index(best)])
    for row in out:
        if row['reason']:
            stats['reason: ' + re.sub(r' \(.*', '', row['reason'])] += 1
        p = row['probability'] or 0
        stats['expected links ' + row['class']] = round(stats['expected links ' + row['class']] + p, 1)
        stats['expected labelled links ' + row['class']] = round(stats['expected labelled links ' + row['class']] +
                                                                 p * (row['class_probability'] or 0), 1)
        stats[f"p >= 0.9 {row['class']}"] += p >= 0.9
    with open(args.out / 'links.jsonl', 'w') as fh:
        for row in out:
            fh.write(json.dumps(row, ensure_ascii=False, default=str) + '\n')
    summary = {'decp': str(args.decp), 'rulings': len(rids), 'settled': dict(how_stats), 'counts': dict(stats),
               'weights_log2': {f: [round(float(x), 2) for x in w] for f, w in weights.items()},
               'reader_accuracy_per_true_class': reader_accuracy, 'levels': LEVELS, 'prior_in_decp': {g: round(v, 3) for g, v in prior.items()}}
    (args.out / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=1))
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
