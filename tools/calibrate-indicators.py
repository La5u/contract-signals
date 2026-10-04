#!/usr/bin/env python3
"""Bounded OFFLINE SYNTHETIC-ONLY ranking experiment; never reads production data."""
import argparse
import json
import time
from pathlib import Path
try:
    import numpy as np
    from scipy.optimize import minimize
    from scipy.special import expit
    from sklearn.metrics import average_precision_score, roc_auc_score
except ImportError as exc:
    raise SystemExit(f"Missing existing dependency: {exc}. Requires numpy, scipy, sklearn; no automatic installation.")

KINDS = ['single-offer', 'direct-award', 'repeated-single-offer', 'repeated-direct',
         'low-competition-rate', 'concentration', 'disqualified-better-bid',
         'short-bidding-period', 'late-notice-change', 'long-duration', 'amount-increase',
         'term-extension', 'late-publication', 'cap', 'execution', 'legalGround', 'unitPrice', 'exclusivity']
FAMILIES = ['competition'] * 9 + ['execution'] * 3 + ['transparency'] + ['execution'] * 2 + ['competition', 'execution', 'competition']
# Representative site constants / graduated maxima; proxy, not actual data scores.
POINTS = np.array([12, 18, 40, 60, 40, 40, 12, 40, 5, 40, 40, 40, 16, 20, 10, 5, 3, 1.])
CAPS = np.array([60., 40., 16.])
FAMILY_NAMES = ['competition', 'execution', 'transparency']
SCENARIOS = ['independent', 'correlated', 'nonlinear-family-max', 'nonlinear-pair-interaction', 'missingness', 'population-sector-drift', 'biased-discovery']
METHODS = ['signal-count', 'fixed-family-max-proxy', 'nonnegative-LR', 'nonnegative-logistic-ranking', 'learned-family-max']


def split_groups(groups, seed):
    order = np.random.default_rng(seed).permutation(np.unique(groups))
    return tuple(np.flatnonzero(np.isin(groups, part)) for part in (order[:60], order[60:80], order[80:]))


def lr_weights(x, known, labels, beta=1):
    rates = []
    for label in (0, 1):
        mask = known & (labels[:, None] == label)
        rates.append(((x * mask).sum(axis=0) + beta) / (mask.sum(axis=0) + 2 * beta))
    return np.maximum(0, np.log(rates[1] / rates[0]))


def family_score(x, weights):
    return np.minimum(100, sum(np.minimum(cap, (x[:, np.array(FAMILIES) == family] * weights[np.array(FAMILIES) == family]).max(axis=1))
                               for family, cap in zip(FAMILY_NAMES, CAPS)))


def ap(y, score):
    return float(average_precision_score(y, score)) if y.sum() else None


def metrics(y, score, known):
    if not len(y):
        return dict.fromkeys(['AP', 'precision_top5', 'recall_top5', 'coverage', 'ROC_AUC', 'prevalence'], None) | {'n': 0}
    k = max(1, int(np.ceil(len(y) * .05)))
    boundary = np.sort(score)[-k]
    above, tied = score > boundary, score == boundary
    inclusion = above.astype(float) + tied * ((k - above.sum()) / tied.sum())
    positives = float(y @ inclusion)
    return {'AP': ap(y, score), 'precision_top5': positives / k,
            'recall_top5': positives / y.sum() if y.sum() else None, 'coverage': float(known.mean()),
            'ROC_AUC': float(roc_auc_score(y, score)) if len(np.unique(y)) == 2 else None,
            'prevalence': float(y.mean()), 'n': len(y)}


def generate(scenario, seed):
    rng = np.random.default_rng(seed)
    groups = np.repeat(np.arange(100), 40)
    train, val, test = split_groups(groups, seed + 1000)
    n = len(groups)
    p0 = np.linspace(.04, .22, 18)
    p1 = np.clip(p0 + rng.uniform(.02, .3, 18), 0, .85)
    buyer_effect = rng.normal(0, .65, 100)[groups]
    latent = rng.binomial(1, expit(np.log(.16 / .84) + buyer_effect))
    prob = np.where(latent[:, None], p1, p0)
    if scenario == 'correlated':
        # Shared family-level shocks create redundant evidence.
        for family in FAMILY_NAMES:
            cols = np.array(FAMILIES) == family
            prob[:, cols] = np.clip(prob[:, cols] + rng.normal(0, .15, (n, 1)), .01, .95)
    if scenario == 'population-sector-drift':
        sector = (groups % 3)[:, None]
        prob = np.clip(prob + .05 * sector, .01, .95)
        prob[test] = np.clip(.1 + .65 * prob[test, ::-1], .01, .95)
    x = (rng.random((n, 18)) < prob).astype(float)
    if scenario == 'nonlinear-family-max':
        x = (rng.random((n, 18)) < p0).astype(float)
        latent = rng.binomial(1, expit(-3 + family_score(x, POINTS) / 25 + buyer_effect))
    if scenario == 'nonlinear-pair-interaction':
        x = (rng.random((n, 18)) < np.clip(p0 * 2, 0, .8)).astype(float)
        interaction = (x[:, :9] * x[:, 9:]).sum(axis=1)
        latent = rng.binomial(1, expit(-2.5 + 2.5 * interaction + buyer_effect))
    known = rng.random((n, 18)) > .08
    if scenario == 'missingness':
        known = rng.random((n, 18)) > (.15 + .45 * latent[:, None])
    observed = x * known
    discovery = latent.copy()
    if scenario == 'biased-discovery':
        discovery = latent * (rng.random(n) < expit(-1.5 + 2.8 * x[:, 0] + 1.5 * x[:, 1]))
    return observed, known, latent, discovery, (train, val, test)


def fit_models(x, known, labels, validation_x, validation_labels, validation_known):
    objective = lambda y, s: ap(y, s) if y.sum() else -1.
    lr_candidates = [lr_weights(x, known, labels, beta) for beta in (1, 5)]
    lr_index = max(range(2), key=lambda i: objective(validation_labels, validation_x @ lr_candidates[i]))
    lr = lr_candidates[lr_index]
    means = (x.sum(axis=0) + 1) / (known.sum(axis=0) + 2)
    imputed = np.where(known, x, means)
    def loss(theta, regularization):
        z = imputed @ theta[1:] + theta[0]
        residual = expit(z) - labels
        return (np.logaddexp(0, z).mean() - (labels * z).mean() + regularization * (theta[1:] ** 2).sum(),
                np.r_[residual.mean(), imputed.T @ residual / len(labels) + 2 * regularization * theta[1:]])
    regularizations = (.005, .025, .1)
    results = [minimize(loss, np.zeros(19), args=(reg,), jac=True, method='L-BFGS-B',
                        bounds=[(None, None)] + [(0, 8)] * 18, options={'maxiter': 100})
               for reg in regularizations]
    # Caller supplies assessed masks separately for validation imputation.
    vx = np.where(validation_known, validation_x, means)
    eligible = [i for i, result in enumerate(results) if result.success]
    if not eligible:
        raise RuntimeError('No logistic candidate converged')
    li = max(eligible, key=lambda i: objective(validation_labels, vx @ results[i].x[1:] + results[i].x[0]))
    upper = np.array([CAPS[FAMILY_NAMES.index(f)] for f in FAMILIES])
    candidates = []
    for start in (np.minimum(POINTS, upper), upper / 2):
        weights = start.copy()
        # Two passes, four values; TRAIN AP tunes, validation only selects start.
        for _ in range(2):
            for j in range(18):
                best = objective(labels, family_score(x, weights))
                chosen = weights[j]
                for value in (0, upper[j] / 4, upper[j] / 2, upper[j]):
                    trial = weights.copy(); trial[j] = value
                    score = objective(labels, family_score(x, trial))
                    if score > best + 1e-12:
                        best, chosen = score, value
                weights[j] = chosen
        candidates.append(weights)
    fi = max(range(2), key=lambda i: objective(validation_labels, family_score(validation_x, candidates[i])))
    return {'lr': lr, 'means': means, 'logistic': results[li].x, 'family': candidates[fi],
            'selection': {'lr_beta': (1, 5)[lr_index], 'logistic_regularization': regularizations[li],
                          'logistic_converged': [bool(r.success) for r in results], 'family_start': fi}}


def run_one(scenario, seed):
    x, known, truth, discovery, (train, val, test) = generate(scenario, seed)
    fitted = fit_models(x[train], known[train], discovery[train], x[val], discovery[val], known[val])
    tx, tk = x[test], known[test]
    scores = [tx.sum(axis=1), family_score(tx, POINTS), tx @ fitted['lr'],
              np.where(tk, tx, fitted['means']) @ fitted['logistic'][1:] + fitted['logistic'][0],
              family_score(tx, fitted['family'])]
    high = tk.mean(axis=1) >= .8
    return {'seed': seed, 'train_discovery_prevalence': float(discovery[train].mean()),
            'test_true_prevalence': float(truth[test].mean()),
            'metrics': {m: metrics(truth[test], s, tk) for m, s in zip(METHODS, scores)},
            'coverage_ge_80pct': {m: metrics(truth[test][high], s[high], tk[high]) for m, s in zip(METHODS, scores)},
            'split_diagnostics': {name: {'true_prevalence': float(truth[idx].mean()),
                'discovery_prevalence': float(discovery[idx].mean()),
                'discovery_recall': float(discovery[idx].sum() / truth[idx].sum()) if truth[idx].sum() else None}
                for name, idx in zip(('train', 'validation', 'test'), (train, val, test))},
            'selection': fitted['selection'],
            'weights': {k: v.tolist() for k, v in fitted.items() if k != 'selection'}}


def summarize(values):
    values = [v for v in values if v is not None]
    return {'mean': float(np.mean(values)) if values else None,
            'std': float(np.std(values)) if values else None, 'n': len(values)}


def paired_interval(runs, method):
    differences = [r['metrics'][method]['AP'] - r['metrics']['signal-count']['AP']
                   for r in runs if r['metrics'][method]['AP'] is not None
                   and r['metrics']['signal-count']['AP'] is not None]
    if not differences:
        return {'mean': None, 'interval_95': None, 'n': 0}
    draws = np.random.default_rng(712).choice(differences, (1000, len(differences))).mean(axis=1)
    return {'mean': float(np.mean(differences)), 'interval_95': np.quantile(draws, [.025, .975]).tolist(),
            'n': len(differences)}


def experiment():
    start = time.perf_counter()
    scenarios = {}
    for scenario in SCENARIOS:
        runs = [run_one(scenario, seed) for seed in range(5)]
        aggregate = {m: {key: summarize([r['metrics'][m][key] for r in runs])
                         for key in ('AP', 'precision_top5', 'recall_top5', 'coverage', 'ROC_AUC', 'prevalence')} for m in METHODS}
        scenarios[scenario] = {'runs': runs, 'aggregate': aggregate,
                               'paired_seed_bootstrap_AP_difference_vs_count': {m: paired_interval(runs, m) for m in METHODS},
                               'ranking_by_mean_AP': sorted(METHODS, key=lambda m: -(aggregate[m]['AP']['mean'] if aggregate[m]['AP']['mean'] is not None else -1))}
    return {'schema_version': 1, 'synthetic_only': True,
            'disclaimer': 'Verified real-world corruption labels = 0. Cannot calibrate real-world corruption, estimate corruption probabilities, or validate site scores.',
            'design': {'rows_per_seed': 4000, 'buyer_groups': 100, 'split_groups': [60, 20, 20], 'seeds': list(range(5)),
                       'test_target': 'synthetic latent outcome, distinct from selected discovery labels',
                       'baseline': 'representative site constants / graduated maxima proxy, NOT actual data scores',
                       'caps': dict(zip(FAMILY_NAMES, CAPS.tolist())), 'total_cap': 100,
                       'tie_handling': 'raw-score tie-aware AP/AUC; top5 boundary ties receive equal fractional inclusion weights',
                       'missing': 'LR denominators assessed only; logistic imputes training assessed conditional means, no missingness coefficients; count/family-max absent checks contribute no signal',
                       'logistic': 'train fits L2 candidates [.005,.025,.1], validation raw AP selects converged fit; uncalibrated ranking scale',
                       'family_optimization': 'two starts (nominal, uniform per-family half-cap), two coordinate passes, four bounded values; train AP tune, validation AP select',
                       'lr': 'train beta smoothing [1,5], validation raw AP selection; assessed denominators preserved',
                       'scenario_notes': 'Every scenario has correlated buyer-level outcome random effects. Family-max generator uses the exact fixed proxy and gives it a built-in advantage. Pair-interaction is a separate nonlinear generator. Biased-discovery is a narrow positive-unlabeled setting: training unlabeled rows are wrongly treated as negative; no general bias-correction claim.',
                       'bootstrap': '1000 deterministic paired resamples across five synthetic seeds only; NOT real-world statistical evidence',
                       'comparison': 'Fitted pipelines, NOT general model-family superiority. Missing preprocessing intentionally differs; logistic has an imputation advantage. coverage_ge_80pct is a selected-subset diagnostic.',
                       'limitations': ['Invented distributions, not empirical calibration', 'Selection bias and missing-not-at-random remain uncorrected', 'Five seeds and finite validation search do not establish general superiority', 'High-coverage subset may be selected and differ in prevalence; AP and recall null when it has no positives'],
                       'indicators': [{'kind': k, 'family': f, 'nominal_points': p} for k, f, p in zip(KINDS, FAMILIES, POINTS.tolist())]},
            'scenarios': scenarios, 'elapsed_seconds': time.perf_counter() - start}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='/tmp/contract-calibration-results.json')
    args = parser.parse_args()
    result = experiment()
    Path(args.output).write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'output': args.output, 'elapsed_seconds': result['elapsed_seconds'],
                      'rankings': {s: v['ranking_by_mean_AP'] for s, v in result['scenarios'].items()}}, indent=2))
