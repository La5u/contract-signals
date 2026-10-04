#!/usr/bin/env python3
"""Offline, country-specific single-bid proxy calibration; never edits scoring."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re

import numpy as np
import scipy
from scipy.optimize import minimize
from scipy.special import expit

VERSION = "1.0.0"
ROOT = Path(__file__).resolve().parents[1]
FILES = {
    "France": ["contracts", "decp-history", "decp-cities"],
    "Portugal": ["ted-portugal"], "Romania": ["ted-romania"],
    "Czechia": ["ted-czechia"], "UK": ["uk-fts"],
    "Chile": ["chile-mp"], "Ukraine": ["prozorro"],
    "Paraguay": ["paraguay-dncp", "paraguay-dncp-3buyers"],
}
# Intervals are [lower, upper); decimal cutpoints implement inclusive integer days.
SPECS = {
    "publication_delay_days": ([0, 31, 61, 121, 241, 731, math.inf], "high", "transparency"),
    "buyer_relative_delay_days": ([-math.inf, 0, 31, 61, 121, 241, 731, math.inf], "high", "transparency"),
    "duration_months": ([0, 12, 24, 48, 120, math.inf], "high", "execution"),
    "submission_period_days": ([0, 10, 15, 22, 31, 53, math.inf], "low", "competition"),
    "supplier_concentration_share": ([0, .4, .6, .8, math.inf], "high", "competition"),
    "decp_amount_increase_percent": ([0, 10, 20, 40, 100, math.inf], "high", "execution"),
}
ENTRY_MAX = {"competition": 18, "execution": 8, "transparency": 8}


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def day(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def clean_reason(row):
    if row.get("dataStatus") != "verified":
        return "not_verified"
    if row.get("identityAmbiguous"):
        return "ambiguous_identity"
    if row.get("initialConflicts") or row.get("modificationConflicts"):
        return "conflicting_versions"
    if row.get("assessmentMode") == "browse":
        return "browse_only"
    if (row.get("findingScope") == "aggregate" or
            row.get("consultation") and not row.get("contractId") or
            row.get("noticeEvidence") and not row.get("date")):
        return "aggregate_or_documentary"
    return None


def outcome(row):
    """DNCP uses the site's equivalent normalized method/count checks."""
    if clean_reason(row):
        return None, clean_reason(row)
    if row.get("dataFamily") == "dncp":
        if row.get("procurementMethod") not in {"open", "selective", "limited"}:
            return None, "not_explicitly_competitive"
        count = row.get("numberOfTenderers")
        if (row.get("tenderersListed") is not None and row["tenderersListed"] != count or
                number(count) and (row.get("lotCount") or 0) > 1 and count > 1):
            return None, "unusable_offer_count"
    else:
        field = "directAward" if "directAward" in row else "procedureDirect"
        if row.get(field) is not False:
            return None, "not_explicitly_competitive"
        count = row.get("offers")
    if not number(count) or count < 1 or int(count) != count:
        return None, "unusable_offer_count"
    return int(count == 1), None


def supplier(row):
    ids = row.get("supplierIds") or []
    if len(ids) != 1 or not ids[0].get("id"):
        return None
    value = ids[0]
    if value.get("identifierType") == "SIRET":
        ident = value.get("siren")
        if not ident and re.fullmatch(r"\d{14}", value["id"]):
            ident = value["id"][:9]
        return "SIREN:" + ident if ident and re.fullmatch(r"\d{9}", ident) else None
    return str(value.get("identifierType", "unknown")) + ":" + value["id"]


def amount_increase(row):
    if row.get("dataFamily") != "decp" or row.get("priceType") != "Définitif ferme":
        return None
    history = row.get("history") or []
    initial = next((e for e in history if e.get("kind") == "initial"), None)
    changes = [e for e in history if e.get("kind") == "modification"]
    if not initial or not changes or not day(initial.get("date")):
        return None
    original = initial.get("amount")
    if not number(original) or original <= 0 or original != row.get("amount") or initial["date"] != row.get("date"):
        return None
    if any(not day(e.get("date")) or e["date"] < initial["date"] for e in changes):
        return None
    latest = sorted(changes, key=lambda e: e["date"], reverse=True)[0]
    revised = latest.get("amount")
    if not number(revised) or revised < original:
        return None
    if any(e["date"] == latest["date"] and e.get("amount") != revised for e in changes):
        return None
    identities = {s.get("id") for s in row.get("supplierIds", [])}
    if any(e.get("supplierId") and e["supplierId"] not in identities for e in changes):
        return None
    cents, new_cents = math.floor(original * 100 + .5), math.floor(revised * 100 + .5)
    if cents <= 0 or max(cents, new_cents) > 2**53 - 1:
        return None
    return 100 * (new_cents - cents) / cents


def submission_period(row):
    # None of the selected French cohorts carries consultation chronology.
    # Reject incomplete chronology rather than substituting award/publication dates.
    if row.get("dataFamily") == "dncp":
        value = row.get("tenderPeriodDays")
        return value if number(value) and value >= 0 else None
    return None


def derive_context(rows):
    """Compute covariates on clean full cohorts, before filtering outcomes."""
    delay_groups, concentration_groups = defaultdict(list), defaultdict(list)
    for row in rows:
        row["buyer_key"] = str(row.get("buyerSiret") or row.get("buyerId") or row.get("buyer") or "unknown")
        cpv = row.get("cpv") or ""
        row["cpv2"] = cpv[:2] if re.fullmatch(r"\d{8}(?:-\d)?", cpv) and not cpv.startswith("000") else "unknown"
        row["cpv3"] = cpv[:3] if row["cpv2"] != "unknown" else None
        row["year"] = row["date"][:4] if day(row.get("date")) else "unknown"
        row["supplier_key"] = supplier(row)
        start, published = day(row.get("date")), day(row.get("publicationDate"))
        delay = (published - start).days if start and published else None
        row["negative_delay"] = delay is not None and delay < 0
        row["publication_delay_days"] = delay if delay is not None and delay >= 0 else None
        duration = row.get("durationMonths")
        row["duration_months"] = duration if number(duration) and duration >= 0 else None
        row["submission_period_days"] = submission_period(row)
        row["decp_amount_increase_percent"] = amount_increase(row)
        row["buyer_relative_delay_days"] = None
        row["supplier_concentration_share"] = None
        if clean_reason(row):
            continue
        if row["publication_delay_days"] is not None:
            delay_groups[(row["cohort"], row["buyer_key"])].append(row)
        if row["cpv3"]:
            concentration_groups[(row["cohort"], row["buyer_key"], row["cpv3"])].append(row)
    for group in delay_groups.values():
        if len(group) < 10:
            continue
        values = sorted(r["publication_delay_days"] for r in group)
        for row in group:
            others = values.copy()
            others.remove(row["publication_delay_days"])
            row["buyer_relative_delay_days"] = row["publication_delay_days"] - float(np.median(others))
    for group in concentration_groups.values():
        counts = Counter(r["supplier_key"] for r in group if r["supplier_key"])
        known = sum(counts.values())
        for row in group:
            ident = row["supplier_key"]
            if ident and known - 1 >= 10 and (known - 1) / (len(group) - 1) >= .8:
                row["supplier_concentration_share"] = (counts[ident] - 1) / (known - 1)
    return rows


def load_country(root, names):
    rows, hashes = [], {}
    for name in names:
        path = root / "data" / (name + ".json")
        raw = path.read_bytes()
        hashes[str(path.relative_to(root))] = hashlib.sha256(raw).hexdigest()
        data = json.loads(raw)
        cohort = data if isinstance(data, list) else data.get("contracts", data.get("rows"))
        if not isinstance(cohort, list):
            raise ValueError(f"No contracts/rows array in {path}")
        identities = Counter((r.get("buyerSiret"), r.get("contractId")) for r in cohort
                             if r.get("dataFamily") == "decp" and r.get("buyerSiret") and r.get("contractId"))
        for original in cohort:
            row = dict(original, cohort=name)
            if row.get("dataFamily") == "decp" and identities[(row.get("buyerSiret"), row.get("contractId"))] > 1:
                row["identityAmbiguous"] = True
            rows.append(row)
    derive_context(rows)
    excluded, eligible = Counter(), []
    for row in rows:
        y, reason = outcome(row)
        if reason:
            excluded[reason] += 1
        else:
            row["y"] = y
            eligible.append(row)
    return rows, eligible, dict(sorted(excluded.items())), hashes


def merge_bins(values, outcomes, edges):
    """Leftmost sparse bin joins its smaller adjacent neighbor (left on ties)."""
    assigned = np.searchsorted(edges, values, side="right") - 1
    bins = [{"lower": a, "upper": b, "members": [i],
             "indices": np.flatnonzero(assigned == i).tolist()}
            for i, (a, b) in enumerate(zip(edges[:-1], edges[1:]))]
    # Empty intervals still merge: resulting thresholds cannot skip unobserved ranges.
    merges = []
    def sparse(b):
        n = len(b["indices"])
        events = sum(outcomes[i] for i in b["indices"])
        return n < 30 or events < 5 or n - events < 5
    while len(bins) > 1:
        i = next((i for i, b in enumerate(bins) if sparse(b)), None)
        if i is None:
            break
        if i == 0:
            j = 1
        elif i == len(bins) - 1:
            j = i - 1
        else:
            j = i - 1 if len(bins[i - 1]["indices"]) <= len(bins[i + 1]["indices"]) else i + 1
        a, b = sorted((i, j))
        merges.append([bins[a]["members"].copy(), bins[b]["members"].copy()])
        bins[a] = {"lower": bins[a]["lower"], "upper": bins[b]["upper"],
                   "members": bins[a]["members"] + bins[b]["members"],
                   "indices": sorted(bins[a]["indices"] + bins[b]["indices"])}
        bins.pop(b)
    return bins, merges


def design(rows, labels, reference, buyer_fe):
    """Input terms first; deterministic orthogonal rank check removes aliases."""
    n = len(rows)
    columns, names = [np.ones(n)], ["intercept"]
    def add(name, values):
        columns.append(np.asarray(values, dtype=float))
        names.append(name)
    for value in sorted(set(labels)):
        if value != reference:
            add(f"bin:{value}", labels == value)
    currencies = [r.get("currency") or ("EUR" if r.get("dataFamily") in {"decp", "boamp"} else "unknown") for r in rows]
    for currency in sorted(set(currencies)):
        usable = [math.log(r["amount"]) for r, c in zip(rows, currencies) if c == currency and number(r.get("amount")) and r["amount"] > 0]
        median = float(np.median(usable)) if usable else 0
        scale = float(np.std(usable)) if usable else 1
        logs, missing = [], []
        for r, c in zip(rows, currencies):
            known = number(r.get("amount")) and r["amount"] > 0
            logs.append(((math.log(r["amount"]) if known else median) - median) / (scale or 1) if c == currency else 0)
            missing.append(c == currency and not known)
        add("log_amount:" + currency, logs)
        add("amount_missing:" + currency, missing)
    pooled = {}
    for field in ["currency", "cpv2", "year", "cohort"] + (["buyer_key"] if buyer_fe else []):
        values = currencies if field == "currency" else [r.get(field, "unknown") for r in rows]
        counts = Counter(values)
        events = Counter(v for v, r in zip(values, rows) if r["y"])
        if field == "buyer_key":
            rare = {v for v in counts if counts[v] < 20}
        elif field in {"cpv2", "year"}:
            rare = {v for v in counts if counts[v] < 20 or events[v] < 5 or counts[v] - events[v] < 5}
        else:
            rare = set()
        pooled[field] = sorted(rare)
        values = ["__other__" if v in rare else v for v in values]
        # Most frequent reference reduces intercept extrapolation; ties alphabetical.
        baseline = min(set(values), key=lambda v: (-values.count(v), v))
        for v in sorted(set(values)):
            if v != baseline:
                add(field + ":" + v, [x == v for x in values])
    matrix = np.column_stack(columns)
    retained, basis = [], []
    for i in range(matrix.shape[1]):
        residual = matrix[:, i].copy()
        for _ in range(2):
            for vector in basis:
                residual -= vector * (vector @ residual)
        norm = np.linalg.norm(residual)
        if norm > 1e-8 * max(1, np.linalg.norm(matrix[:, i])):
            retained.append(i)
            basis.append(residual / norm)
    return matrix[:, retained], [names[i] for i in retained], {
        "buyer_fixed_effects": buyer_fe, "controls": "log(amount) within currency + currency + CPV2 + year + cohort" + (" + buyer (>=20 rows, else other)" if buyer_fe else ""),
        "pooled_levels": pooled, "dropped_redundant_columns": [v for i, v in enumerate(names) if i not in retained],
    }


def fit_model(rows, labels, reference, buyer_fe):
    x, names, spec = design(rows, labels, reference, buyer_fe)
    y = np.asarray([r["y"] for r in rows], dtype=float)
    n, p = x.shape
    spec.update(n=n, parameters=p, coefficient_names=names)
    if len(set(y)) < 2 or n <= p + 5:
        return {"status": "insufficient", "spec": spec, "reason": "No outcome variation or insufficient residual degrees of freedom"}, None
    def optimize(penalty):
        mask = np.ones(p)
        mask[0] = 0
        def objective(beta):
            z = x @ beta
            value = np.logaddexp(0, z).sum() - y @ z + .5 * penalty * (mask * beta**2).sum()
            gradient = x.T @ (expit(z) - y) + penalty * mask * beta
            return value, gradient
        def hessian(beta):
            prob = expit(x @ beta)
            return x.T @ ((prob * (1 - prob))[:, None] * x) + np.diag(penalty * mask)
        start = np.zeros(p)
        start[0] = math.log(y.mean() / (1 - y.mean()))
        fit = minimize(objective, start, jac=True, hess=hessian, method="trust-exact",
                       options={"gtol": 1e-7, "maxiter": 150})
        converged = np.linalg.norm(objective(fit.x)[1], ord=np.inf) < 1e-5
        return fit, hessian(fit.x), converged
    fit, hessian, converged = optimize(0)
    penalty = 0
    if not converged or np.max(np.abs(fit.x)) > 20 or np.linalg.cond(hessian) > 1e10:
        penalty = .5
        fit, hessian, converged = optimize(penalty)
    if not converged or np.linalg.cond(hessian) > 1e12:
        return {"status": "failed", "spec": spec, "reason": "Optimization/Hessian unstable"}, None
    covariance = np.linalg.inv(hessian)
    buyers = [r["buyer_key"] for r in rows]
    groups = sorted(set(buyers))
    covariance_type = "Hessian (too few buyer clusters for inference)"
    if len(groups) >= 20 and not penalty:
        scores = x * (y - expit(x @ fit.x))[:, None]
        sums = np.zeros((len(groups), p))
        index = {b: i for i, b in enumerate(groups)}
        for b, score in zip(buyers, scores):
            sums[index[b]] += score
        covariance = covariance @ (sums.T @ sums) @ covariance
        covariance *= len(groups) / (len(groups) - 1) * (n - 1) / (n - p)
        covariance_type = "buyer-cluster sandwich, CR1 finite-sample correction"
    if penalty:
        covariance_type = "penalized Hessian, approximate descriptive intervals"
    se = np.sqrt(np.maximum(0, np.diag(covariance)))
    ll = float((y * (x @ fit.x) - np.logaddexp(0, x @ fit.x)).sum())
    report = {"status": "regularized" if penalty else "ok", "spec": spec,
              "regularization_l2": penalty, "covariance": covariance_type,
              "buyer_clusters": len(groups), "log_likelihood": ll,
              "aic": None if penalty else 2 * p - 2 * ll,
              "inference_usable": not penalty and len(groups) >= 20 and "unknown" not in groups,
              "bin_estimates": {}}
    for value in sorted(set(labels)):
        if value == reference:
            report["bin_estimates"][str(value)] = {"log_or": 0., "or": 1., "ci95": [1., 1.]}
            continue
        name = f"bin:{value}"
        if name not in names:
            report["bin_estimates"][str(value)] = {"log_or": None, "or": None, "ci95": None}
            report["inference_usable"] = False
            continue
        i = names.index(name)
        b, s = float(fit.x[i]), float(se[i])
        def exponential(v):
            return math.exp(v) if v < 700 else None
        report["bin_estimates"][str(value)] = {"log_or": b, "or": exponential(b),
                                                  "ci95": [exponential(b - 1.96 * s), exponential(b + 1.96 * s)]}
    return report, (x, fit.x)


def edge_json(value):
    return value if math.isfinite(value) else None


def analyze_input(rows, key):
    edges, direction, family = SPECS[key]
    usable = [r for r in rows if number(r.get(key))]
    y = [r["y"] for r in usable]
    result = {"n": len(y), "events": sum(y), "base_rate": sum(y) / len(y) if y else None,
              "missing_input_rows": len(rows) - len(y), "direction": direction, "family": family,
              "initial_edges": [edge_json(e) for e in edges], "bins": [], "models": {},
              "recommendation": {"status": "insufficient_evidence", "threshold": None,
                                 "message": "insufficient evidence: keep editorial threshold"},
              "weight_hint": None, "caveats": []}
    result["planned_model_spec"] = {
        "outcome": "offers == 1 among explicitly competitive rows with positive integer offers",
        "controls": ["log(amount) within currency", "currency", "CPV2", "year", "cohort"],
        "primary": "buyer fixed effects (>=20 usable rows; smaller buyers pooled)",
        "uncertainty": "buyer-cluster sandwich for >=20 buyers, otherwise descriptive Hessian",
    }
    if not usable:
        result["caveats"].append("Input not reliably derivable in eligible bundled rows; no model fitted.")
        return result
    bins, merges = merge_bins([r[key] for r in usable], y, edges)
    labels = np.zeros(len(y), dtype=int)
    for i, b in enumerate(bins):
        labels[b["indices"]] = i
        result["bins"].append({"lower": edge_json(b["lower"]), "upper": edge_json(b["upper"]),
                               "original_bins": b["members"], "n": len(b["indices"]),
                               "events": sum(y[j] for j in b["indices"]), "or": None, "ci95": None,
                               "base_rate": sum(y[j] for j in b["indices"]) / len(b["indices"])})
    result["sparse_bin_merges"] = merges
    reference = 0 if direction == "high" else len(bins) - 1
    result["reference_bin"] = reference
    if merges:
        result["caveats"].append("Adjacent sparse/empty bins merged; resolution is coarser than initial edges.")
    if len(bins) < 2:
        result["caveats"].append("Only one supported bin remains; no input contrast is identifiable.")
        return result
    for buyer_fe, name in [(False, "without_buyer_fe"), (True, "with_buyer_fe")]:
        report, _ = fit_model(usable, labels, reference, buyer_fe)
        result["models"][name] = report
    primary = result["models"]["with_buyer_fe"]
    for i, b in enumerate(result["bins"]):
        b["reference"] = i == reference
        b.update({k: v for k, v in primary.get("bin_estimates", {}).get(str(i), {}).items() if k in {"or", "ci95"}})
    if not primary.get("inference_usable"):
        result["caveats"].append("Primary inference unavailable: penalized/unstable fit, aliased input, or fewer than 20 buyer clusters.")
        return result
    order = list(range(len(bins))) if direction == "high" else list(reversed(range(len(bins))))
    for position in range(1, len(order)):
        region = order[position:]
        summaries = [result["bins"][i] for i in region]
        if not all(b["ci95"] and b["ci95"][0] is not None and b["ci95"][0] > 1 + 1e-8 and b["n"] >= 30 and b["events"] >= 5 for b in summaries):
            continue
        if any(b["or"] < a["or"] - 1e-8 for a, b in zip(summaries, summaries[1:])):
            continue
        first = bins[region[0]]
        threshold = first["lower"] if direction == "high" else first["upper"]
        if not math.isfinite(threshold):
            continue
        result["recommendation"] = {"status": "recommend", "threshold": threshold,
                                    "operator": ">=" if direction == "high" else "<",
                                    "region_bins": region,
                                    "message": f"candidate threshold {key} {'>=' if direction == 'high' else '<'} {threshold:g}"}
        # Binary region versus the reference only: intermediate bins are excluded.
        subset = [r for r, label in zip(usable, labels) if label == reference or label in region]
        binary = np.array([int(label in region) for label in labels if label == reference or label in region])
        hint_fit, _ = fit_model(subset, binary, 0, True)
        result["flagged_region_model"] = hint_fit
        log_or = hint_fit.get("bin_estimates", {}).get("1", {}).get("log_or")
        if hint_fit.get("inference_usable") and log_or is not None and log_or > 0:
            result["weight_hint"] = {"log_or": log_or, "scaled_entry_weight": None,
                                      "family_entry_max": ENTRY_MAX[family], "applied": False}
        return result
    result["recommendation"].update(status="no_association", message="no association: consider dropping/demoting in this jurisdiction")
    result["caveats"].append("No supported monotone positive region; this is not proof of a null effect.")
    return result


def compare_delays(rows):
    common = [r for r in rows if number(r.get("publication_delay_days")) and number(r.get("buyer_relative_delay_days"))]
    fits = {key: analyze_input(common, key) for key in ["publication_delay_days", "buyer_relative_delay_days"]}
    models = {key: fit["models"].get("with_buyer_fe", {}) for key, fit in fits.items()}
    aics = {key: model.get("aic") for key, model in models.items()}
    winner = None
    if all(number(v) for v in aics.values()):
        keys = list(aics)
        if abs(aics[keys[0]] - aics[keys[1]]) >= 2:
            winner = min(aics, key=aics.get)
    return {"n": len(common), "events": sum(r["y"] for r in common),
            "aic": aics, "better_in_sample": winner,
            "models": models, "bins": {k: v["bins"] for k, v in fits.items()},
            "conclusion": "indeterminate" if winner is None else winner + " has lower AIC on identical rows",
            "caveats": ["Exploratory in-sample comparison; different bin counts penalized by AIC, no held-out validation.",
                        "Do not switch the site solely on AIC; require a supported threshold and reliable date semantics."]}


def calibrate(root=ROOT, generated_at=None):
    output = {"tool_version": VERSION, "method": "within-country binned logistic single-bid proxy",
              "dependencies": {"numpy": np.__version__, "scipy": scipy.__version__},
              "input_sha256": {}, "jurisdictions": {},
              "out_of_scope": {"Colombia": "SECOP II contains no offer counts; single bidding cannot be defined."}}
    if generated_at is not None:
        output["generated_at"] = generated_at
    for country, files in FILES.items():
        all_rows, rows, excluded, hashes = load_country(root, files)
        output["input_sha256"].update(hashes)
        inputs = {key: analyze_input(rows, key) for key in SPECS}
        strongest = max((r["weight_hint"]["log_or"] for r in inputs.values() if r["weight_hint"]), default=0)
        for result in inputs.values():
            if result["weight_hint"]:
                hint = result["weight_hint"]
                hint["scaled_entry_weight"] = hint["family_entry_max"] * hint["log_or"] / strongest
                hint["country_strongest_log_or"] = strongest
        for key in ["publication_delay_days", "buyer_relative_delay_days"]:
            inputs[key]["negative_delay_rows_dropped"] = sum(r["negative_delay"] for r in rows)
            if country == "UK":
                inputs[key]["caveats"].append("UK contract dates are not reliably comparable with publication; descriptive only, do not apply.")
            if country == "France":
                inputs[key]["caveats"].append("BOAMP conclusion and DECP notification dates have different meanings; cohort controlled.")
        inputs["supplier_concentration_share"]["caveats"].append("Retrospective full-cohort context; leave-one-row-out, not historical-only; repeated lots may inflate support.")
        if country in {"Chile", "Paraguay"}:
            inputs["supplier_concentration_share"]["caveats"].append("No CPV: national categories are not substituted for CPV3.")
        inputs["decp_amount_increase_percent"]["caveats"].append("DECP only, post-award validation; no amendment is not assumed to mean zero increase.")
        if country != "Paraguay":
            inputs["submission_period_days"]["caveats"].append("No validated publication-to-submission-deadline chronology in selected JSON; tenderCreated/award date cannot replace a deadline.")
        output["jurisdictions"][country] = {"source_rows": len(all_rows), "n": len(rows),
                                          "events": sum(r["y"] for r in rows),
                                          "base_rate": sum(r["y"] for r in rows) / len(rows) if rows else None,
                                          "exclusions": excluded, "cohorts": files, "inputs": inputs,
                                          "delay_comparison": compare_delays(rows)}
    path = root / "data" / "colombia-secop2.json"
    output["input_sha256"][str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return output


def serialize(result):
    return json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n"


def summary(result):
    print("Jurisdiction | eligible n/events | supported thresholds | delay comparison")
    for country, data in result["jurisdictions"].items():
        recommendations = [r["recommendation"]["message"] for r in data["inputs"].values() if r["recommendation"]["status"] == "recommend"]
        print(f"{country} | {data['n']}/{data['events']} | {'; '.join(recommendations) or 'none (see evidence status per input)'} | {data['delay_comparison']['conclusion']}")
        evidence = Counter(r["recommendation"]["status"] for r in data["inputs"].values())
        print("  " + ", ".join(f"{name}: {count}" for name, count in sorted(evidence.items())))
    print("Colombia | out of scope: no offer counts. Weight hints are not applied.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=ROOT / "research/thresholds/results.json")
    parser.add_argument("--generated-at", help="Explicit provenance date; omitted by default")
    args = parser.parse_args()
    result = calibrate(args.root, args.generated_at)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(serialize(result), encoding="utf-8")
    summary(result)


if __name__ == "__main__":
    main()
