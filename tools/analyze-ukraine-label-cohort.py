#!/usr/bin/env python3
"""Descriptive analyses of the Ukraine audit label cohort (research/labels/ukraine-cohort.json.gz).

  a) single-bid threshold analysis (tools/calibrate-thresholds.py functions, same predeclared rule), Ukraine-audit
  b) among DASU-monitored tenders: rate of every explorer indicator for audit_violation true vs false, tender-level,
     with Wilson 95% intervals and an add-half smoothed likelihood ratio (site engine run in Node on all rows as one cohort)

Selection caveat: DASU picks tenders with its own risk rules that overlap the explorer indicators; reviewed
negatives are conditional on that selection, comparison tenders are unlabelled. Nothing here is a finding of
corruption and no scoring file is changed. The existing calibrate-thresholds.py is imported, never modified.
"""
import argparse
import gzip
import importlib.util
import json
import math
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('calibrate_thresholds', ROOT / 'tools/calibrate-thresholds.py')
ct = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ct)

JURISDICTION = 'Ukraine-audit'
COHORT = 'ukraine-audit-label-cohort'


def load_cohort(path):
    return json.loads(gzip.decompress(Path(path).read_bytes()))


def submission_period(row):
    """Tender-period length published in the official record (start to end of the submission period)."""
    value = row.get('tenderPeriodDays')
    return value if ct.number(value) and value >= 0 else None


def threshold_rows(rows):
    """Rows as calibrate-thresholds.py expects them (importer fields + cohort)."""
    return [dict(r, cohort=COHORT) for r in rows]


def analyze_single_bid(rows):
    rows = threshold_rows(rows)
    ct.submission_period = submission_period      # this cohort carries tenderPeriod chronology (not the DNCP-only default)
    ct.derive_context(rows)
    excluded, eligible = Counter(), []
    for row in rows:
        y, reason = ct.outcome(row)
        if reason:
            excluded[reason] += 1
        else:
            row['y'] = y
            eligible.append(row)
    inputs = {key: ct.analyze_input(eligible, key) for key in ct.SPECS}
    buyers = {r['buyer_key'] for r in eligible}
    return {'source_rows': len(rows), 'n': len(eligible), 'events': sum(r['y'] for r in eligible),
            'base_rate': sum(r['y'] for r in eligible) / len(eligible) if eligible else None,
            'buyers': len(buyers), 'exclusions': dict(sorted(excluded.items())), 'inputs': inputs,
            'delay_comparison': ct.compare_delays(eligible)}


def wilson(k, n, z=1.959964):
    if n == 0:
        return [None, None]
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(max(0, centre - half), 4), round(min(1, centre + half), 4)]


def engine_rows(rows):
    """Add the display fields the site validator requires; no names are stored, ids stand in."""
    out = []
    for r in rows:
        e = {k: v for k, v in r.items() if k not in ('role', 'labels', 'matchedTo', 'violationTypes', 'reporting', 'tenderStatus',
                                                      'tenderPeriodStart', 'tenderPeriodEnd', 'tenderPeriodDays', 'awardDate')}
        e.update(buyer=r['buyerId'] or 'unknown buyer', description='(not stored)', supplier='(not stored)', sourceLabel='Prozorro public API',
                 amountBasis='Contract value as published; never converted.', dateNote='Contract signature date.', notes='Research cohort row.')
        out.append(e)
    return out


def run_engine(rows):
    with tempfile.TemporaryDirectory() as d:
        src, dst = Path(d) / 'rows.json', Path(d) / 'status.json'
        src.write_text(json.dumps(engine_rows(rows)))
        subprocess.run(['node', str(ROOT / 'tools/ukraine-cohort-indicators.cjs'), str(src), str(dst)], check=True, cwd=ROOT,
                       stdout=subprocess.DEVNULL)
        return json.loads(dst.read_text())


def tender_status(statuses):
    """Tender-level: signal if any row signals; clear if none signals and some row is assessed."""
    if 'signal' in statuses:
        return 'signal'
    return 'clear' if 'clear' in statuses else None


def indicator_table(rows, status):
    by_tender = defaultdict(list)
    for r in rows:
        by_tender[r['tenderID']].append(r)
    groups = {'true': [], 'false': [], 'comparison': []}
    for tid, rs in by_tender.items():
        if rs[0]['role'] == 'comparison':
            groups['comparison'].append(rs)
        elif rs[0]['labels']['audit_violation'] is True:
            groups['true'].append(rs)
        elif rs[0]['labels']['audit_violation'] is False:
            groups['false'].append(rs)
    ids = sorted({i for s in status.values() for i in s})
    table = {}
    for ind in ids:
        entry = {}
        for name, tenders in groups.items():
            assessed = [tender_status([status[r['id']][ind] for r in rs if r['id'] in status]) for rs in tenders]
            assessed = [a for a in assessed if a]
            sig = sum(a == 'signal' for a in assessed)
            entry[name] = {'signal': sig, 'assessed': len(assessed), 'rate': round(sig / len(assessed), 4) if assessed else None,
                           'wilson95': wilson(sig, len(assessed))}
        t, f = entry['true'], entry['false']
        if t['assessed'] and f['assessed']:
            lr = ((t['signal'] + .5) / (t['assessed'] + 1)) / ((f['signal'] + .5) / (f['assessed'] + 1))
            entry['smoothed_lr_true_vs_false'] = round(lr, 3)
        else:
            entry['smoothed_lr_true_vs_false'] = None
        table[ind] = entry
    return {'tenders': {k: len(v) for k, v in groups.items()}, 'indicators': table}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--cohort', default=str(ROOT / 'research/labels/ukraine-cohort.json.gz'))
    p.add_argument('--output', default=str(ROOT / 'research/labels/ukraine-cohort-analysis.json'))
    args = p.parse_args(argv)
    cohort = load_cohort(args.cohort)
    rows = cohort['rows']
    status = run_engine(rows)
    out = {'cohort': Path(args.cohort).name, 'built_at': cohort['built_at'], 'jurisdiction': JURISDICTION,
           'caveat': cohort['selection_diagnostics']['caveat'],
           'single_bid_all_rows': analyze_single_bid(rows),
           'single_bid_monitored_rows': analyze_single_bid([r for r in rows if r['role'] == 'monitored']),
           'indicator_rates_by_audit_outcome': indicator_table([r for r in rows], status),
           'notes': ['Descriptive only: no claim of corruption; indicators are editorial, audit outcome is partial and selected.',
                     'Likelihood ratio = ((s_true+0.5)/(n_true+1)) / ((s_false+0.5)/(n_false+1)), tender level (any row signals).',
                     'Strata (true/false) are sampled separately, so within-label rates are unaffected by the stratification.',
                     'The nationalConcentration/repeated checks use the cohort as one pooled set of buyers, with sparse buyers (<10 procedures) not assessed.']}
    Path(args.output).write_text(json.dumps(out, indent=1, ensure_ascii=False, allow_nan=False) + '\n')
    sb = out['single_bid_all_rows']
    print(f"single-bid all rows: n={sb['n']} events={sb['events']} buyers={sb['buyers']}")
    for k, v in sb['inputs'].items():
        print(f"  {k}: {v['recommendation']['status']} n={v['n']} {v['recommendation']['message']}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
