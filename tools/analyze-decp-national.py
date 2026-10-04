#!/usr/bin/env python3
"""Offline national DECP threshold research. Writes aggregates only; no downloads.

Run with ~/.cache/contract-signals/venv/bin/python. Temporary SQLite staging is
removed on exit. Supported buyers with >=200 rows receive fixed effects;
unsupported control levels are pooled to prevent separated nuisance terms.
"""
import os
# Avoid oversubscribing the small dense Hessians, also stabilize repeated runs.
for _env in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_env] = "2"
import argparse
from collections import Counter, defaultdict
from datetime import date
import hashlib
import importlib.util
import itertools
import json
import math
from pathlib import Path
import re
import sqlite3
import tempfile
import time

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
CACHE = Path.home() / ".cache/contract-signals/decp-national"
VERSION = "1.1.0"
CONTROL_MIN_ROWS = 50
BUYER_MIN_ROWS = 200
MIN_OUTCOME_COUNT = 5
START, END = date(2019, 1, 1).toordinal(), date(2026, 9, 1).toordinal()
_spec = importlib.util.spec_from_file_location("calibrate_thresholds_national", ROOT / "tools/calibrate-thresholds.py")
ct = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ct)
_calibration_fit_model = ct.fit_model
_spec = importlib.util.spec_from_file_location("decp_importer_national", ROOT / "tools/import-decp-cities.py")
importer = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(importer)

# Use the actual site importer, including its deliberate MAPA exclusion.
FORMAL = {"Appel d'offres ouvert", "Appel d'offres restreint"}
ADAPTED = "Procédure adaptée"
KEYS = list(ct.SPECS)
CONCENTRATION_EDGES = [0, .4, .5, .6, .7, .8, .9, math.inf]
# Source metadata, uid, current-state flags and geographical enrichments do not
# define an initial procurement state. Names are unnecessary even internally.
STATE_FIELDS = ["nature", "objet", "montant", "codeCPV", "procedure", "techniques",
                "dureeMois", "offresRecues", "dateNotification", "datePublicationDonnees",
                "formePrix", "typesPrix", "idAccordCadre", "titulaire_id",
                "titulaire_typeIdentifiant", "type", "attributionAvance", "tauxAvance",
                "marcheInnovant", "modalitesExecution", "considerationsSociales",
                "considerationsEnvironnementales", "ccag", "sousTraitanceDeclaree",
                "typeGroupementOperateurs", "origineUE", "origineFrance",
                "lieuExecution_code", "lieuExecution_typeCode", "montant_rationalise",
                "montant_anomalie", "montant_anomalie_raisons"]


def procedure_family(label):
    if label == ADAPTED:
        return "adapted"
    if label in FORMAL:
        return "formal_calls"
    if importer.direct(label) is False:
        return "other_competitive"
    return "direct" if importer.direct(label) is True else "unknown"


def ordinal(value):
    if isinstance(value, date):
        return value.toordinal()
    try:
        return date.fromisoformat(str(value)[:10]).toordinal()
    except (TypeError, ValueError):
        return None


def positive(value):
    return ct.number(value) and value > 0


def fingerprint(values):
    # Dates are Arrow date32 objects; a canonical JSON string handles fixtures too.
    return hashlib.sha256(json.dumps(values, ensure_ascii=False, separators=(",", ":"),
                                    default=str, allow_nan=False).encode()).digest()


def supplier_key(row):
    ident, typ = row.get("titulaire_id"), row.get("titulaire_typeIdentifiant")
    if not ident or not typ or ident in {"CDL", "INX"}:
        return None
    if typ == "SIRET":
        if not re.fullmatch(r"\d{14}", ident):
            return None
        ident, typ = ident[:9], "SIREN"
    if typ == "SIREN" and not re.fullmatch(r"\d{9}", ident):
        return None
    return fingerprint([typ, ident]).hex()


def payload(row):
    cpv = row.get("codeCPV") or ""
    valid = bool(re.fullmatch(r"\d{8}(?:-\d)?", cpv)) and not cpv.startswith("000")
    # Inspection: rationalise equals raw unless anomaly=aberrant; nevertheless
    # every nonempty anomaly is excluded, including suspect unchanged amounts.
    amount = row.get("montant_rationalise")
    if amount is None:
        amount = row.get("montant")
    return [ordinal(row.get("dateNotification")), ordinal(row.get("datePublicationDonnees")),
            amount, bool(row.get("montant_anomalie")), row.get("procedure"),
            cpv[:2] if valid else "unknown", cpv[:3] if valid else None,
            supplier_key(row), row.get("dureeMois"), row.get("offresRecues"), row.get("typesPrix")]


def batches(source):
    cols = ["uid", "id", "acheteur_id", "modification_id", "donneesActuelles", "sourceDataset"] + STATE_FIELDS
    if isinstance(source, pa.Table):
        names = [c for c in cols if c in source.column_names]
        yield from source.select(names).to_batches(max_chunksize=32768)
    else:
        file = pq.ParquetFile(source)
        names = [c for c in cols if c in file.schema_arrow.names]
        yield from file.iter_batches(columns=names, batch_size=32768)


def stage(source, db):
    """Deduplicate procurement snapshots, never select a conflicting version.

    Conservative holder policy: differing holder rows are initial conflicts,
    including possible coholders. The flattened file cannot reliably distinguish
    coholders from changed supplier versions; no contract amounts are summed.
    """
    db.executescript("""
      PRAGMA journal_mode=OFF; PRAGMA synchronous=OFF; PRAGMA temp_store=FILE;
      PRAGMA cache_size=-32768;
      CREATE TABLE initial (buyer TEXT, cid TEXT, sig BLOB, uid TEXT, p TEXT,
                            PRIMARY KEY(buyer,cid,sig)) WITHOUT ROWID;
      CREATE TABLE mods (buyer TEXT, cid TEXT, mid INTEGER, sig BLOB, p TEXT,
                         PRIMARY KEY(buyer,cid,mid,sig)) WITHOUT ROWID;
      CREATE TABLE units (buyer TEXT,cid TEXT,d INTEGER,p INTEGER,a REAL,
                          proc TEXT,cpv2 TEXT,cpv3 TEXT,supplier TEXT,duration REAL,
                          offers REAL,price TEXT,PRIMARY KEY(buyer,cid)) WITHOUT ROWID;
    """)
    counts, labels, cross, amounts = Counter(), Counter(), Counter(), Counter()
    uid_counts = Counter()
    for batch in batches(source):
        init, mods = [], []
        for r in batch.to_pylist():
            # Parquet floats can carry NaN for missing values: treat them as missing.
            r = {k: None if isinstance(v, float) and math.isnan(v) else v for k, v in r.items()}
            counts["source_rows"] += 1
            labels[r.get("procedure") or "(missing)"] += 1
            mid, current = r.get("modification_id"), r.get("donneesActuelles")
            cross[f"{'initial' if mid == 0 else 'unversioned' if mid is None else 'modification'} / {current}"] += 1
            amounts[f"raw_equals_cleaned={r.get('montant') == r.get('montant_rationalise')} / {r.get('montant_anomalie') or 'none'}"] += 1
            if mid is None:
                counts["unversioned_rows_excluded"] += 1
                continue
            counts["initial_rows" if mid == 0 else "modification_rows"] += 1
            buyer, cid = r.get("acheteur_id"), r.get("id")
            if not buyer or not cid or buyer in {"CDL", "INX"} or cid in {"CDL", "INX"}:
                counts["missing_identity_rows"] += 1
                continue
            # Serialize the selected raw state before any cleaning; unknown versus
            # known, dates, raw amounts and supplier disagreements all conflict.
            sig = fingerprint([r.get(f) for f in STATE_FIELDS])
            p = json.dumps(payload(r), ensure_ascii=False, separators=(",", ":"), allow_nan=False)
            if mid == 0:
                init.append((buyer, cid, sig, r.get("uid"), p))
                if r.get("uid"):
                    uid_counts[r["uid"]] += 1
            elif mid > 0:
                mods.append((buyer, cid, mid, sig, p))
            else:
                counts["invalid_modification_index_rows"] += 1
        before = db.total_changes
        db.executemany("INSERT OR IGNORE INTO initial VALUES (?,?,?,?,?)", init)
        counts["duplicate_initial_snapshots_removed"] += len(init) - (db.total_changes - before)
        before = db.total_changes
        db.executemany("INSERT OR IGNORE INTO mods VALUES (?,?,?,?,?)", mods)
        counts["duplicate_modification_snapshots_removed"] += len(mods) - (db.total_changes - before)
        db.commit()
    # Only aggregate uid multiplicities survive; release the identity counter.
    uid_report = {"distinct_initial_uid": len(uid_counts),
                  "uids_with_multiple_initial_rows": sum(v > 1 for v in uid_counts.values()),
                  "extra_initial_uid_rows": sum(v - 1 for v in uid_counts.values())}
    del uid_counts
    # The primary key orders groups without retaining the national file in RAM.
    query = db.execute("SELECT buyer,cid,COUNT(*),MIN(p) FROM initial GROUP BY buyer,cid ORDER BY buyer,cid")
    pending = []
    families = Counter()
    for buyer, cid, variants, encoded in query:
        counts["initial_contract_groups"] += 1
        if variants != 1:
            counts["conflicting_initial_groups_excluded"] += 1
            counts["conflicting_unique_initial_snapshots_excluded"] += variants
            continue
        d, pub, amount, anomaly, proc, cpv2, cpv3, supplier, duration, offers, price = json.loads(encoded)
        if d is None:
            counts["missing_initial_date_groups_excluded"] += 1
        elif not START <= d <= END:
            counts["outside_date_window_groups_excluded"] += 1
        elif anomaly:
            counts["amount_anomaly_groups_excluded"] += 1
        elif not positive(amount):
            counts["missing_or_nonpositive_amount_groups_excluded"] += 1
        else:
            counts["clean_context_contracts"] += 1
            families[procedure_family(proc)] += 1
            pending.append((buyer,cid,d,pub,amount,proc,cpv2,cpv3,supplier,duration,offers,price))
        if len(pending) >= 10000:
            db.executemany("INSERT INTO units VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", pending)
            pending.clear()
    db.executemany("INSERT INTO units VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", pending)
    db.commit()
    counts["modification_only_contract_groups"] = db.execute("""SELECT COUNT(*) FROM
      (SELECT buyer,cid FROM mods GROUP BY buyer,cid) m WHERE NOT EXISTS
      (SELECT 1 FROM initial i WHERE i.buyer=m.buyer AND i.cid=m.cid)""").fetchone()[0]
    counts["modification_conflict_groups"] = db.execute("""SELECT COUNT(*) FROM
      (SELECT buyer,cid,mid FROM mods GROUP BY buyer,cid,mid HAVING COUNT(*)>1)""").fetchone()[0]
    return {"counts": dict(sorted(counts.items())), "procedure_labels": dict(sorted(labels.items())),
            "initial_current_cross_tab": dict(sorted(cross.items())),
            "amount_cleaning_cross_tab": dict(sorted(amounts.items())),
            "initial_uid_duplicates": uid_report, "clean_context_procedure_families": dict(sorted(families.items()))}


def loo_median(sorted_values, rank):
    """Median after removing one ranked observation, without copying the group."""
    n = len(sorted_values) - 1
    def at(i):
        return sorted_values[i + (i >= rank)]
    return float(at(n // 2)) if n % 2 else (at(n // 2 - 1) + at(n // 2)) / 2


def modification_increase(db, buyer, cid, initial):
    """Validation only: latest published index, firm price, conflict-safe history."""
    if initial[11] != "Définitif ferme":
        return None, "not_firm_price"
    mods = list(db.execute("SELECT mid,COUNT(*),MIN(p) FROM mods WHERE buyer=? AND cid=? GROUP BY mid ORDER BY mid", (buyer,cid)))
    if not mods:
        return None, "no_published_modification"
    original_supplier = initial[8]
    for mid, variants, encoded in mods:
        if variants != 1:
            return None, "conflicting_modification"
        p = json.loads(encoded)
        if p[0] is None or p[0] < initial[2] or p[3] or not positive(p[2]):
            return None, "invalid_modification_date_or_amount"
        if not original_supplier or p[7] != original_supplier:
            return None, "changed_or_unknown_supplier"
    revised = p[2]
    if revised < initial[4]:
        return None, "latest_amount_decrease"
    cents, new_cents = math.floor(initial[4] * 100 + .5), math.floor(revised * 100 + .5)
    if cents <= 0 or max(cents,new_cents) > 2**53 - 1:
        return None, "unsafe_amount_precision"
    return 100 * (new_cents - cents) / cents, "usable"


def eligible_rows(db):
    rows, excluded, diagnostics = [], Counter(), Counter()
    coverage = defaultdict(Counter)
    cursor = db.execute("SELECT * FROM units ORDER BY buyer,cid")
    for buyer, entries in itertools.groupby(cursor, key=lambda r:r[0]):
        group = list(entries)
        dated = sorted((r[3]-r[2], i) for i,r in enumerate(group) if r[3] is not None and r[3] >= r[2])
        delays = [v for v,_ in dated]
        relative = {i:v-loo_median(delays,rank) for rank,(v,i) in enumerate(dated)} if len(dated)>=10 else {}
        cpv_total, cpv_known, supplier_counts = Counter(), Counter(), Counter()
        for r in group:
            if r[7]:
                cpv_total[r[7]] += 1
                if r[8]:
                    cpv_known[r[7]] += 1
                    supplier_counts[(r[7],r[8])] += 1
        for i,r in enumerate(group):
            family = procedure_family(r[5])
            coverage[family]["clean_contracts"] += 1
            offers = r[10]
            good_offers = ct.number(offers) and offers >= 1 and int(offers)==offers
            coverage[family]["usable_offer_count"] += int(good_offers)
            if importer.direct(r[5]) is not False:
                excluded["not_explicitly_competitive"] += 1
                continue
            if not good_offers:
                excluded["unusable_offer_count"] += 1
                continue
            delay = r[3]-r[2] if r[3] is not None else None
            if delay is not None and delay < 0:
                diagnostics["negative_publication_delay_rows"] += 1
                delay = None
            concentration = None
            known, total = cpv_known[r[7]], cpv_total[r[7]]
            if r[8] and r[7] and known-1 >= 10 and (known-1)/(total-1) >= .8:
                concentration = (supplier_counts[(r[7],r[8])]-1)/(known-1)
            increase, reason = modification_increase(db,buyer,r[1],r)
            diagnostics["modification_validation_"+reason] += 1
            row = {"buyer_key":buyer,"cpv2":r[6],"year":str(date.fromordinal(r[2]).year),
                   "amount":r[4],"currency":"EUR","cohort":"decp-national","y":int(offers==1),
                   "procedure_family":family,"publication_delay_days":delay,
                   "buyer_relative_delay_days":relative.get(i),
                   "duration_months":r[9] if ct.number(r[9]) and r[9]>=0 else None,
                   "supplier_concentration_share":concentration,
                   "decp_amount_increase_percent":increase,"submission_period_days":None}
            rows.append(row)
            coverage[family]["eligible_contracts"] += 1
            coverage[family]["single_bid_contracts"] += row["y"]
    return rows, dict(sorted(excluded.items())), dict(sorted(diagnostics.items())), {k:dict(sorted(v.items())) for k,v in sorted(coverage.items())}


def national_design(rows, labels, reference, buyer_fe):
    """Pool unsupported nuisance levels and remove aliases, input terms first.

    Sequential Gram-matrix rank checks preserve input-first alias removal. All
    amounts are positive EUR, so currency, missing-amount and cohort are constant.
    """
    n = len(rows)
    columns, names = [np.ones(n)], ["intercept"]
    for value in sorted(set(labels)):
        if value != reference:
            columns.append((labels==value).astype(float)); names.append(f"bin:{value}")
    logs = np.log([r["amount"] for r in rows])
    columns.append((logs-np.median(logs))/(np.std(logs) or 1)); names.append("log_amount:EUR")
    pooled_counts = {}
    fe_kept = set()
    for field in ["cpv2","year"] + (["buyer_key"] if buyer_fe else []):
        vals = [r[field] for r in rows]
        counts = Counter(vals)
        events = Counter(v for v,r in zip(vals,rows) if r["y"])
        min_rows = BUYER_MIN_ROWS if field == "buyer_key" else CONTROL_MIN_ROWS
        def supported(total, event_count):
            return total >= min_rows and min(event_count, total-event_count) >= MIN_OUTCOME_COUNT
        rare = {v for v in counts if not supported(counts[v], events[v])}
        # Renaming a pure-outcome category "other" does not remove separation.
        # Merge it with the largest supported level; retain every observation.
        if rare and not supported(sum(counts[v] for v in rare), sum(events[v] for v in rare)):
            kept = set(counts)-rare
            if kept:
                rare.add(min(kept, key=lambda v: (-counts[v], v)))
        if field == "buyer_key":
            fe_kept = set(counts)-rare
        pooled_counts[field] = len(rare)
        vals = ["__other__" if v in rare else v for v in vals]
        counts = Counter(vals)
        baseline = min(counts,key=lambda v:(-counts[v],v))
        for v in sorted(counts):
            if v!=baseline:
                columns.append(np.asarray([x==v for x in vals],dtype=float)); names.append(field+":"+v)
    x = np.column_stack(columns)
    del columns
    gram = x.T @ x
    retained = []
    # Incremental Cholesky avoids repeatedly solving a growing dense system.
    # Each accepted column extends the factor of the retained Gram matrix.
    factor = np.zeros_like(gram)
    for i in range(len(names)):
        residual = gram[i,i]
        k = len(retained)
        if retained:
            v = gram[retained,i]
            projection = ct.scipy.linalg.solve_triangular(factor[:k,:k], v, lower=True, check_finite=False)
            residual -= projection @ projection
        if residual > 1e-10*max(1,gram[i,i]):
            if retained:
                factor[k,:k] = projection
            factor[k,k] = math.sqrt(residual)
            retained.append(i)
    if len(retained) != len(names):
        x = x[:,retained]
    # Global centering is an equivalent intercept reparameterization, not
    # within-buyer demeaning. It prevents large-sample intercept-gradient stalls.
    x[:,1:] -= x[:,1:].mean(axis=0)
    return x, [names[i] for i in retained], {
        "buyer_fixed_effects":buyer_fe,"buyer_fe_cap":None if buyer_fe else 0,
        "buyer_fe_min_rows":BUYER_MIN_ROWS,"control_min_rows":CONTROL_MIN_ROWS,
        "control_min_events_and_nonevents":MIN_OUTCOME_COUNT,
        "non_intercept_columns_globally_centered":True,
        "buyer_fe_levels":len(fe_kept),"buyer_fe_rows":sum(r['buyer_key'] in fe_kept for r in rows),
        "pooled_level_counts":{("buyers" if k=="buyer_key" else k):v for k,v in pooled_counts.items()},"dropped_redundant_columns_count":len(names)-len(retained),
        "controls":"scaled log(amount EUR) + CPV2 + year" + (" + all supported buyers (>=200 rows); remaining pooled" if buyer_fe else "")}


def diagnose_input(rows, key="supplier_concentration_share"):
    """Inspect the unchanged fitter's actual unpenalized fallback conditions."""
    usable = [r for r in rows if ct.number(r.get(key))]
    edges, direction, _ = ct.SPECS[key]
    if key == "supplier_concentration_share":
        edges = CONCENTRATION_EDGES
    bins, _ = ct.merge_bins([r[key] for r in usable], [r["y"] for r in usable], edges)
    labels = np.zeros(len(usable), dtype=int)
    for i, b in enumerate(bins):
        labels[b["indices"]] = i
    reference = 0 if direction == "high" else len(bins)-1
    x, names, _ = national_design(usable, labels, reference, True)
    old_design, old_minimize = ct.design, ct.minimize
    diagnostics = []
    def inspect(objective, start, **kwargs):
        fit = old_minimize(objective, start, **kwargs)
        gradient = objective(fit.x)[1]
        largest = int(np.argmax(np.abs(fit.x)))
        gradient_largest = int(np.argmax(np.abs(gradient)))
        name = names[largest]
        # Keep buyer identifiers private even in console diagnostics.
        safe = lambda v: "buyer fixed effect" if v.startswith("buyer_key:") else v
        diagnostic = {
            "fit": "unpenalized" if not diagnostics else "L2 fallback",
            "n": len(usable), "parameters": len(names),
            "optimizer_success": bool(fit.success), "message": str(fit.message),
            "iterations": int(fit.nit), "gradient_inf": float(np.max(np.abs(gradient))),
            "converged": bool(np.max(np.abs(gradient)) < 1e-5),
            "max_abs_beta": float(np.abs(fit.x[largest])), "largest_coefficient": safe(name),
            "largest_gradient_column": safe(names[gradient_largest]),
            "hessian_condition": float(np.linalg.cond(kwargs["hess"](fit.x))),
        }
        indicator = x[:,largest] - x[:,largest].min()
        if largest and np.all(np.isclose(indicator, 0) | np.isclose(indicator, 1)):
            selected = np.isclose(indicator, 1)
            diagnostic["level_n"] = int(selected.sum())
            diagnostic["level_events"] = sum(r["y"] for r,s in zip(usable,selected) if s)
        diagnostics.append(diagnostic)
        print(json.dumps(diagnostic), flush=True)
        return fit
    ct.design, ct.minimize = national_design, inspect
    try:
        report, _ = national_fit_model(usable, labels, reference, True)
        print(json.dumps({"status": report["status"]}), flush=True)
    finally:
        ct.design, ct.minimize = old_design, old_minimize
    return diagnostics


def national_fit_model(rows, labels, reference, buyer_fe):
    """Use the imported fitter with accurate loss reduction for large samples.

    Its float64 sum minus y@z loses tiny Newton improvements. Sum per-row
    logistic losses in extended precision instead; preserve its gradient,
    Hessian, fallback criteria, penalty and cluster covariance verbatim.
    """
    x, names, spec = national_design(rows, labels, reference, buyer_fe)
    y = np.asarray([r["y"] for r in rows], dtype=float)
    old_design, old_minimize = ct.design, ct.minimize
    def minimize(objective, start, **kwargs):
        def accurate_objective(beta):
            _, gradient = objective(beta)
            z = x @ beta
            # The gradient's extra term is the unchanged quadratic L2 penalty.
            # For a quadratic penalty R, R(beta)=beta @ grad(R)/2.
            penalty_gradient = gradient - x.T @ (ct.expit(z)-y)
            penalty = np.longdouble(beta @ penalty_gradient) / 2
            precise_z = x @ beta.astype(np.longdouble)
            loss = np.logaddexp(0, np.where(y, -precise_z, precise_z)).sum(dtype=np.longdouble)
            return loss + penalty, gradient
        return old_minimize(accurate_objective, start, **kwargs)
    ct.design = lambda *_: (x, names, spec)
    ct.minimize = minimize
    try:
        return _calibration_fit_model(rows, labels, reference, buyer_fe)
    finally:
        ct.design, ct.minimize = old_design, old_minimize


def flag_counts(rows,key,threshold):
    values = [r[key] for r in rows if ct.number(r.get(key))]
    n = sum(v>=threshold for v in values)
    share = n/len(values) if values else None
    return {"threshold":threshold,"operator":">=","flagged":n,"assessable":len(values),
            "share_assessable":share,"share_eligible":n/len(rows) if rows else None,
            "norm_warning":share is not None and share>.3,
            "majority_flagged":share is not None and share>.5}


def sanitize_models(value):
    """Imported fit reports coefficient names containing buyer IDs; strip them."""
    if isinstance(value,dict):
        return {k:sanitize_models(v) for k,v in value.items() if k not in {"coefficient_names","pooled_levels","dropped_redundant_columns"}}
    if isinstance(value,list):
        return [sanitize_models(v) for v in value]
    return value


def analyze(rows):
    results = {}
    # Reuse actual bin merging, logistic fitting, cluster covariance and the
    # predeclared monotone-significant-tail recommendation rule without edits.
    old_design, old_spec, old_fit = ct.design, ct.SPECS["supplier_concentration_share"], ct.fit_model
    ct.design, ct.fit_model = national_design, national_fit_model
    ct.SPECS["supplier_concentration_share"] = (CONCENTRATION_EDGES,"high","competition")
    try:
        for key in KEYS:
            print(f"  {key}: {len(rows):,} eligible",flush=True)
            result = ct.analyze_input(rows,key)
            result["planned_model_spec"].update(
                controls=["centered/scaled log(amount EUR)", "CPV2", "year"],
                primary="all buyers with >=200 usable rows and >=5 events/non-events; others pooled",
                control_pooling="CPV2/year: >=50 rows and >=5 events/non-events; unsupported other merges with largest supported level")
            edges = ct.SPECS[key][0]
            candidates = [v for v in edges[1:-1] if math.isfinite(v)]
            result["candidate_flag_counts"] = [flag_counts(rows,key,v) for v in candidates]
            rec = dict(result["recommendation"])
            result["statistical_recommendation"] = rec
            if rec.get("threshold") is not None:
                flagged = flag_counts(rows,key,rec["threshold"])
                result["recommended_flag_counts"] = flagged
                if flagged["majority_flagged"]:
                    result["recommendation"] = {"status":"reject_majority_flag","threshold":None,
                        "message":"Statistical candidate flags the majority; unsuitable as an outlier red flag."}
                elif flagged["norm_warning"]:
                    result["recommendation"]["status"] = "review_common_pattern"
                    result["recommendation"]["message"] += "; flags >30% of assessable contracts; require policy review"
            if key=="submission_period_days":
                result["caveats"].append("DECP has no submission deadline or validated submission-period input.")
            if key=="decp_amount_increase_percent":
                result["validation_only"] = True
                result["caveats"].append("Post-award validation only: no modification is not zero increase; latest published positive modification index used, not inferred chronology.")
            results[key] = sanitize_models(result)
    finally:
        ct.design, ct.SPECS["supplier_concentration_share"], ct.fit_model = old_design,old_spec,old_fit
    return {"n":len(rows),"events":sum(r["y"] for r in rows),"buyers":len({r["buyer_key"] for r in rows}),
            "base_rate":sum(r["y"] for r in rows)/len(rows) if rows else None,"inputs":results}


def assert_aggregate_only(output):
    forbidden = {"uid","id","acheteur_id","titulaire_id","buyer_key","supplier_key",
                 "buyerId","supplierId","contractId","rows","contracts","coefficient_names",
                 "acheteur_nom","titulaire_nom","objet","initialAlternatives","indices"}
    def walk(v, path="$"):
        if isinstance(v,dict):
            if forbidden.intersection(v):
                raise ValueError(f"row-level field {sorted(forbidden.intersection(v))} in aggregate output at {path}")
            for k,x in v.items(): walk(x, f"{path}.{k}")
        elif isinstance(v,list):
            for i,x in enumerate(v): walk(x, f"{path}[{i}]")
    walk(output)


def interval(bin):
    a,b = bin["lower"],bin["upper"]
    return f"[{a if a is not None else '-inf'}, {b if b is not None else '+inf'})"


def estimate(bin):
    if bin.get("or") is None or not bin.get("ci95") or None in bin["ci95"]:
        return "unavailable"
    return f"{bin['or']:.2f} [{bin['ci95'][0]:.2f}, {bin['ci95'][1]:.2f}]"


def markdown(output):
    counts = output["inspection"]["counts"]
    all = output["overall"]
    lines = ["# France national DECP: threshold research", "",
        f"Tool {VERSION}; offline snapshot SHA-256 `{output['input_sha256']}`. Dataset `{output['source']['dataset_id']}`, licence `{output['source']['licence']}`.", "",
        f"Source: {counts['source_rows']:,} contract-version-holder rows. Clean initial-state context: {counts['clean_context_contracts']:,} contracts. Outcome cohort: {all['n']:,} contracts, {all['buyers']:,} buyers, {all['events']:,} single bids ({all['base_rate']:.1%}).",
        "", "## Method and deviations", "",
        "One contract is buyer identifier + contract identifier. modification_id=0 is the initial state; positive indices are modifications. Null indices lack usable notification dates in this snapshot and are excluded. donneesActuelles marks the current/latest state, not initial eligibility: false initial states remain eligible. Exact procurement snapshots are deduplicated across sources, ignoring source metadata, uid, current-state and geographical enrichments. All differing procurement snapshots in an initial identity group are excluded; no arbitrary version is selected. Raw amounts, dates, description and holder identity participate in conflict checks. Differing holders are conservatively excluded too: flattened coholder rows cannot reliably be distinguished from changed-supplier versions. No amounts are summed.",
        "", "Dates: initial notification 2019-01-01 through 2026-09-01 inclusive. Positive montant_rationalise (raw fallback only when missing) controls amount; all suspect/aberrant amounts are dropped, even when unchanged by rationalisation. Inspection found cleaned and raw amounts equal on all non-anomalous rows. Missing CPV2 is an explicit unknown category.",
        "", "Outcome: offresRecues=1 versus integer offresRecues>=2 among procedures for which tools/import-decp-cities.py direct() is exactly false; tools/import-decp-paris-ardeche.py imports the same map. Exact supported labels: open/restricted calls for tender, Procédure avec négociation, Dialogue compétitif. MAPA/Procédure adaptée maps to unknown and is excluded, as are alternative spellings and other negotiated labels absent from the importer. This is a mapping limitation, not a claim those procedures lack competition. Formal calls are analysed separately; other explicitly competitive procedures are also reported. MAPA has coverage counts only, because it has no eligible outcome under the requested importer rule.",
        "", "All context uses clean initial contracts before outcome/procedure filtering. Publication delay is publication minus notification; negative delays are missing for this input. Buyer-relative delay subtracts the exact leave-one-out buyer median, with at least 10 nonnegative dated contracts in the buyer group. Duration is nonnegative months. Concentration is the focal supplier's share in buyer × CPV3, leaving the focal contract out: at least 10 known-supplier peers and 80% known-supplier coverage, matching the calibration helper's conservative guard. Valid SIRETs collapse to SIREN; other identifiers retain type. The fine bins are [0,40), [40,50), [50,60), [60,70), [70,80), [80,90), [90,100]% (100% belongs to the last bin). This is a full-window retrospective context, not information available at award time.",
        "", "tools/calibrate-thresholds.py is imported unchanged for binning, adjacent sparse-bin merges (n>=30, >=5 events and >=5 non-events), logistic fitting, buyer-cluster sandwich covariance with CR1 correction, and its predeclared monotone significant-tail recommendation rule. Odds ratios (ORs) compare each bin with the first supported bin; confidence intervals (CIs) are 95%. Controls: centered/scaled log(amount EUR), CPV2 and notification year. Constant currency/cohort controls drop out. CPV2/year levels need >=50 rows, >=5 events and >=5 non-events; every buyer meeting >=200 rows and the same outcome-support requirement receives a separate level, with no cap. Unsupported levels are pooled. If the pooled category itself lacks support, it absorbs the largest supported level; renaming a zero-event level alone would retain separation. All observations and buyer clusters remain. The legacy design retained zero-event buyer levels, producing separated coefficients and triggering L2 despite optimizer convergence. These are pooled buyer effects rather than full buyer adjustment; residual buyer differences may confound associations. Where no buyer meets these requirements, the primary specification has no separate buyer levels; inspect the reported FE coverage. An input-first Gram-matrix rank check using incremental Cholesky removes aliased controls while retaining input terms; fitted likelihood and covariance still use the imported functions. Non-intercept columns are globally centered to avoid a large-sample intercept-gradient stall. This is an equivalent intercept reparameterization: likelihood, bin odds ratios and their cluster intervals are preserved; it is not within-buyer demeaning. Per-row logistic losses and their reduction are calculated in extended precision to avoid cancellation of tiny Newton improvements in large samples. The imported gradient, Hessian, convergence/fallback checks, L2 penalty, recommendation rule and cluster covariance are unchanged. The model without buyer fixed effects is reported as sensitivity. Penalized or unstable fits cannot support recommendations. No supplier/buyer coefficient names or identifiers are exported.",
        "", "Each input is fitted separately on rows with that input; denominators differ. Candidate flag counts show both assessable and full eligible shares. The original statistical rule is preserved separately; a majority-flagging candidate is rejected as an outlier red flag, and >30% coverage requires policy review. Multiple inputs/bins are exploratory and are not corrected for multiple testing; no scoring thresholds or weights are changed.",
        "", "Amount increases are validation only: firm-price initial contracts, published modifications, no conflicts, nondecreasing latest amount, valid dates and stable known supplier. Latest means highest published modification index, because the national table exposes states rather than a separate validated amendment date field. Revised amounts are new totals, never added. Absence of modification does not mean zero increase. Submission period is absent from DECP; award/publication dates cannot substitute for submission chronology.",
        "", "## Exclusions and inspection", "", "| Stage/count | Number |", "|---|---:|"]
    for k,v in counts.items(): lines.append(f"| {k} | {v:,} |")
    for k,v in output["outcome_exclusions"].items(): lines.append(f"| outcome: {k} | {v:,} |")
    lines += ["", "Counts are sequential within initial-group exclusions; raw duplicate/modification/uid diagnostics are separate, overlapping units and must not be added to contract exclusions.", "", "### Initial/current state cross-tab", "", "| State / donneesActuelles | Rows |", "|---|---:|"]
    for k,v in output["inspection"]["initial_current_cross_tab"].items(): lines.append(f"| {k} | {v:,} |")
    lines += ["", "### Procedure labels (all source rows)", "", "| Label | Rows |", "|---|---:|"]
    for k,v in output["inspection"]["procedure_labels"].items(): lines.append(f"| {k} | {v:,} |")
    lines += ["", "### Procedure coverage", "", "| Family | Clean contracts | Usable offers | Outcome eligible | Single bid |", "|---|---:|---:|---:|---:|"]
    for k,v in output["procedure_coverage"].items():
        lines.append(f"| {k} | {v.get('clean_contracts',0):,} | {v.get('usable_offer_count',0):,} | {v.get('eligible_contracts',0):,} | {v.get('single_bid_contracts',0):,} |")
    for scope,report in [("overall",output["overall"]),*output["procedure_splits"].items()]:
        lines += ["",f"## Results: {scope}","",f"Eligible n={report['n']:,}; buyers={report['buyers']:,}; events={report['events']:,}."]
        for key,result in report["inputs"].items():
            rec = result["recommendation"]
            lines += ["",f"### {key}","",f"Recommendation: **{rec['status']}**. {rec['message']}", "", "| Bin | n | Single bids | Rate | Adjusted OR [95% CI] |", "|---|---:|---:|---:|---|"]
            for b in result["bins"]:
                lines.append(f"| {interval(b)} | {b['n']:,} | {b['events']:,} | {b['base_rate']:.1%} | {estimate(b)} |")
            for name,model in result["models"].items():
                spec=model["spec"]
                lines.append(f"\n{name}: {model['status']}; {model.get('covariance','no covariance')}; n={spec['n']:,}, parameters={spec['parameters']}; FE levels={spec.get('buyer_fe_levels',0)}, FE rows={spec.get('buyer_fe_rows',0):,}.")
            if result["candidate_flag_counts"]:
                lines += ["", "| Candidate >= | Flagged | Assessable share | Eligible share | Common pattern (>30%) |", "|---|---:|---:|---:|---|"]
                for f in result["candidate_flag_counts"]:
                    share = f"{f['share_assessable']:.1%}" if f["share_assessable"] is not None else "unavailable"
                    lines.append(f"| {f['threshold']:g} | {f['flagged']:,} | {share} | {'n/a' if f['share_eligible'] is None else format(f['share_eligible'], '.1%')} | {'yes' if f['norm_warning'] else 'no'} |")
            lines += ["",*['- '+c for c in result["caveats"]]]
    lines += ["", f"Analysis runtime: {output['runtime_seconds']:.1f} seconds (including staging).", "", "## Conclusions and limits", "",
        "Single bid is a proxy for restricted competition, not corruption. National publication coverage is not a census of purchasing; offer-count reporting is selective and excludes many otherwise competitive records. Lots, framework contracts and reused contract IDs can affect units; conservative conflict exclusions reduce coverage. Full-window supplier shares and buyer medians use later contracts and should not be interpreted as prospective predictions. Publication delays can reflect batching, backfills or data correction. Long duration can be normal for the purchased service. No causal claim, legal-compliance finding or automatic site threshold change follows from these estimates.",
        "", "A fine concentration curve should be assessed across all bins and procedure families, rather than selecting an isolated significant interval. The monotone-tail rule can yield a high threshold even when middle-bin risk starts increasing earlier, or no recommendation when the curve is nonmonotone. A >30% flag share describes a common pattern requiring review; a majority threshold is unsuitable for an outlier red flag. MAPA-specific thresholds cannot be learned without an explicit, validated change to the site's procedure/outcome mapping.", ""]
    return "\n".join(lines)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--input",type=Path,default=CACHE/"decp.parquet")
    parser.add_argument("--manifest",type=Path,default=CACHE/"manifest.json")
    parser.add_argument("--output",type=Path,default=ROOT/"research/thresholds/france-national.json")
    parser.add_argument("--markdown",type=Path,default=ROOT/"research/thresholds/france-national.md")
    parser.add_argument("--diagnose", choices=KEYS, help="inspect one primary model and exit without writing reports")
    args=parser.parse_args(argv)
    started=time.monotonic()
    manifest=json.loads(args.manifest.read_text())
    sha=hashlib.sha256()
    with args.input.open("rb") as fh:
        while block:=fh.read(4<<20): sha.update(block)
    if sha.hexdigest()!=manifest["sha256"]:
        raise ValueError("Input SHA-256 differs from manifest")
    print("Staging national initial states and modifications",flush=True)
    with tempfile.TemporaryDirectory(prefix="decp-national-") as tmp:
        with sqlite3.connect(str(Path(tmp)/"states.sqlite")) as db:
            inspection=stage(args.input,db)
            print(json.dumps(inspection["counts"],sort_keys=True),flush=True)
            rows,excluded,diagnostics,coverage=eligible_rows(db)
    print(f"Outcome eligible: {len(rows):,}; analysing overall",flush=True)
    if args.diagnose:
        diagnose_input(rows, args.diagnose)
        return 0
    overall=analyze(rows)
    splits={}
    for family in ("formal_calls","other_competitive","adapted"):
        subset=[r for r in rows if r["procedure_family"]==family]
        print("Procedure split: "+family,flush=True)
        splits[family]=analyze(subset)
    out={"tool_version":VERSION,"calibration_tool_version":ct.VERSION,
         "calibration_tool_sha256":hashlib.sha256((ROOT/"tools/calibrate-thresholds.py").read_bytes()).hexdigest(),
         "dependencies":{"pyarrow":pa.__version__,"numpy":np.__version__,"scipy":ct.scipy.__version__},
         "source":{k:manifest.get(k) for k in ("dataset_id","dataset_title","licence","resource_last_modified","retrieved_at")},
         "input_sha256":manifest["sha256"],"date_window":["2019-01-01","2026-09-01"],
         "method":{"buyer_fe_cap":None,"buyer_fe_min_rows":BUYER_MIN_ROWS,"cluster":"buyer",
                   "control_min_rows":CONTROL_MIN_ROWS,"control_min_events_and_nonevents":MIN_OUTCOME_COUNT,
                   "non_intercept_columns_globally_centered":True,
                   "loss_reduction":"extended precision per-row logistic loss; unchanged gradient, Hessian and fallback checks",
                   "unsupported_other":"merge with largest supported level",
                   "concentration_edges":[ct.edge_json(v) for v in CONCENTRATION_EDGES],
                   "concentration_min_known_peers":10,"concentration_min_known_coverage":.8,
                   "buyer_relative_min_dated_contracts":10,"common_pattern_share":.3,"majority_rejection_share":.5},
         "inspection":inspection,"outcome_exclusions":excluded,"input_diagnostics":diagnostics,
         "procedure_coverage":coverage,"overall":overall,"procedure_splits":splits}
    out["runtime_seconds"] = round(time.monotonic()-started, 1)
    assert_aggregate_only(out)
    args.output.write_text(json.dumps(out,indent=2,ensure_ascii=False,sort_keys=True,allow_nan=False)+"\n")
    args.markdown.write_text(markdown(out))
    print(f"Completed in {time.monotonic()-started:.1f}s; aggregate outputs written",flush=True)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
