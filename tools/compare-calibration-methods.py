#!/usr/bin/env python3
"""Offline synthetic comparison only; no production inputs or scoring changes."""
import argparse
import importlib.util
import json
import time
from pathlib import Path

_spec = importlib.util.spec_from_file_location('calibration_generator', Path(__file__).with_name('calibrate-indicators.py'))
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)
np, minimize, expit = base.np, base.minimize, base.expit
KINDS = base.KINDS
METRICS = ('AP', 'precision_top5', 'recall_top5')
TOLERANCES = {'AP': .02, 'precision_top5': .05}


def fit_pipelines(train_x, train_known, train_labels, validation_x, validation_known, validation_labels):
    """Only train and validation inputs: never accept test data or a method filter."""
    means = np.divide((train_x * train_known).sum(axis=0), train_known.sum(axis=0),
                      out=np.zeros(len(KINDS)), where=train_known.sum(axis=0) > 0)
    x = np.where(train_known, train_x, means)
    vx = np.where(validation_known, validation_x, means)
    def objective(weights, intercept=0):
        value = base.ap(validation_labels, vx @ weights + intercept)
        return -1 if value is None else value
    betas = (1, 5, 10)
    weights = [base.lr_weights(train_x, train_known, train_labels, beta) for beta in betas]
    li = max(range(len(betas)), key=lambda i: objective(weights[i]))
    def loss(theta, reg):
        z = x @ theta[1:] + theta[0]
        residual = expit(z) - train_labels
        return (float(np.mean(np.logaddexp(0, z) - train_labels * z) + reg * np.sum(theta[1:] ** 2)),
                np.r_[residual.mean(), x.T @ residual / len(x) + 2 * reg * theta[1:]])
    regs = (.005, .025, .1)
    fits = [minimize(loss, np.zeros(len(KINDS) + 1), args=(reg,), jac=True,
                     method='L-BFGS-B', bounds=[(None, None)] + [(0, 8)] * len(KINDS),
                     options={'maxiter': 200}) for reg in regs]
    eligible = [i for i, fit in enumerate(fits) if fit.success and np.isfinite(fit.fun)
                and np.all(np.isfinite(fit.x))]
    if not eligible:
        raise RuntimeError('No logistic candidate converged')
    gi = max(eligible, key=lambda i: objective(fits[i].x[1:], fits[i].x[0]))
    return {'means': means.tolist(),
            'lr': {'weights': weights[li].tolist(), 'intercept': 0., 'beta': betas[li]},
            'logistic': {'weights': fits[gi].x[1:].tolist(), 'intercept': float(fits[gi].x[0]),
                         'l2': regs[gi], 'candidate_converged': [i in eligible for i in range(len(regs))]}}


def select_methods(method):
    if method not in ('lr', 'logistic', 'both'):
        raise ValueError('Unknown method')
    return ('lr', 'logistic') if method == 'both' else (method,)


def run_one(scenario, seed, method='both'):
    x, known, truth, discovery, (train, val, test) = base.generate(scenario, seed)
    fitted = fit_pipelines(x[train], known[train], discovery[train], x[val], known[val], discovery[val])
    tx = np.where(known[test], x[test], fitted['means'])
    # Fit both irrespective of output filter; paired comparison always uses both.
    metrics = {m: base.metrics(truth[test], tx @ fitted[m]['weights'] + fitted[m]['intercept'], known[test])
               for m in ('lr', 'logistic')}
    return {'seed': seed, 'means': fitted['means'],
            'methods': {m: fitted[m] | {'metrics': metrics[m]} for m in select_methods(method)},
            'paired_difference': {k: metrics['logistic'][k] - metrics['lr'][k]
                                  if metrics['logistic'][k] is not None and metrics['lr'][k] is not None else None for k in METRICS},
            'split_diagnostics': {name: {'n': len(idx), 'latent_prevalence': float(truth[idx].mean()),
                                         'selected_label_prevalence': float(discovery[idx].mean())}
                                  for name, idx in zip(('train', 'validation', 'test'), (train, val, test))}}


def paired_summary(values, metric):
    values = np.array([v for v in values if v is not None])
    if not len(values):
        return {'mean': None, 'interval_95': None, 'n': 0, 'classification': 'inconclusive'}
    draws = np.random.default_rng(712).choice(values, (2000, len(values))).mean(axis=1)
    low, high = np.quantile(draws, [.025, .975])
    tolerance = TOLERANCES.get(metric)
    crossing = low <= 0 <= high
    larger = tolerance is not None and (low > tolerance or high < -tolerance)
    return {'mean': float(values.mean()), 'interval_95': [float(low), float(high)], 'n': len(values),
            'winner_by_mean': 'logistic' if values.mean() > 0 else 'lr' if values.mean() < 0 else 'tie',
            'crosses_zero': bool(crossing), 'arbitrary_practical_tolerance': tolerance,
            'classification': 'consistently larger difference' if larger else 'inconclusive',
            'directional_interval_excludes_zero': bool(not crossing)}


def experiment(method='both'):
    select_methods(method)
    start = time.perf_counter()
    scenarios = {}
    for scenario in base.SCENARIOS:
        runs = [run_one(scenario, seed, method) for seed in range(10)]
        scenarios[scenario] = {'runs': runs, 'paired_logistic_minus_lr': {
            k: paired_summary([r['paired_difference'][k] for r in runs], k) for k in METRICS}}
    return {'synthetic_only': True, 'method_output_filter': method,
            'design': {'rows_per_seed': 4000, 'seeds': list(range(10)), 'buyer_groups': 100,
                       'group_split': [60, 20, 20], 'indicators': KINDS,
                       'missing': 'Training assessed means (zero fallback if never assessed), same mean imputation for both rankers; no missingness coefficients.',
                       'lr': 'Training assessed LR with beta [1,5,10]; validation AP selects.',
                       'logistic': 'Training L2 [.005,.025,.1], weights bounded [0,8], free intercept; converged finite candidates only, validation AP selects.',
                       'test': 'Untouched latent synthetic labels; no test tuning. Training/validation use selected discovery labels, treating undiscovered positives as negative in biased-discovery.',
                       'ties': 'Raw-score AP; fractional equal inclusion at top-5% boundary ties.',
                       'bootstrap': '2000 paired resamples across ten seeds only, never rows; descriptive small synthetic sample, no real-world inference.',
                       'predeclared_arbitrary_tolerances': TOLERANCES,
                       'interpretation': 'Tolerances are arbitrary, not empirical claims. Crossing zero is inconclusive, not equivalence. Consistently larger means the entire interval exceeds the tolerance in one direction; all other cases inconclusive. Recall has no declared tolerance. Winners can differ by metric.',
                       'caveats': ['Imputed latent rank scores are not factual signals or deployable weights.',
                                   'No verified real-world labels, probabilities, calibration validity or model-family superiority claims.',
                                   'Invented distributions; buyer effects in all scenarios; nonlinear family-max uses the generator fixed proxy.',
                                   'Missing-not-at-random, population drift and selected discovery bias remain uncorrected.',
                                   'Output filtering never changes fitting, hyperparameter selection or paired comparisons.']},
            'scenarios': scenarios, 'elapsed_seconds': time.perf_counter() - start}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--method', choices=('lr', 'logistic', 'both'), default='both')
    parser.add_argument('--output', default='/tmp/contract-head-to-head.json')
    args = parser.parse_args()
    result = experiment(args.method)
    Path(args.output).write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'output': args.output, 'elapsed_seconds': result['elapsed_seconds'],
                      'paired': {s: v['paired_logistic_minus_lr'] for s, v in result['scenarios'].items()}}, indent=2))
