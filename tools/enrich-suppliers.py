#!/usr/bin/env python3
"""Attach current public company names to every typed French supplier SIREN.

Normal mode reads the DECP cohorts (six cities, Paris & Ardèche) and queries
Recherche entreprises once per distinct SIREN, then writes supplierProfiles into
both datasets.  --offline validates the existing snapshot and re-applies it to
the datasets without making network requests.
"""
import argparse
import hashlib
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API = "https://recherche-entreprises.api.gouv.fr/search"
DATASETS = (("decp-cities.json", "decp-cities-coverage.json"), ("decp-history.json", "decp-coverage.json"))
SIREN_RE = re.compile(r"^\d{9}$")
SIRET_RE = re.compile(r"^\d{14}$")


def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def suppliers(rows):
    found = {}
    for row in rows:
        for item in row.get("supplierIds") or []:
            typ, ident = item.get("identifierType"), str(item.get("id", ""))
            siren = item.get("siren")
            if typ == "SIRET" and SIRET_RE.fullmatch(ident):
                siren = ident[:9]
            elif typ == "SIREN" and SIREN_RE.fullmatch(ident):
                siren = ident
            else:
                continue
            found.setdefault(siren, set())
            if SIRET_RE.fullmatch(ident):
                found[siren].add(ident)
    return found


def selection(rows):
    all_sirens = suppliers(rows)
    ordered = sorted(all_sirens, key=lambda s: hashlib.sha256(s.encode("ascii")).hexdigest())
    return all_sirens, ordered


def query_url(siren):
    # Keep this URL as the exact provenance of the query (rather than a broad
    # search URL or a URL to an unfiltered API response).
    return API + "?" + urllib.parse.urlencode({"q": siren, "per_page": 25})


def fetch(url, attempts=7):
    last = None
    for attempt in range(attempts):
        if attempt:
            time.sleep(min(30, 0.5 * (2 ** attempt)))  # ~1 min total: rides out DNS or network blips
        try:
            with urllib.request.urlopen(url, timeout=45) as response:
                return json.load(response)
        # OSError covers dropped connections (RemoteDisconnected, ConnectionResetError).
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
            last = exc
    raise RuntimeError(f"lookup failed after {attempts} attempts: {last}")


def clean_result(siren, url, payload, retrieved):
    matches = [x for x in payload.get("results", []) if str(x.get("siren", "")) == siren]
    base = {"siren": siren, "name": None, "administrativeState": None,
            "diffusionStatus": None, "source": url, "retrievedAt": retrieved,
            "status": "unavailable", "reason": None}
    if len(matches) != 1:
        base["reason"] = "no exact result siren" if not matches else "ambiguous exact results"
        return base
    result = matches[0]
    diffusion = result.get("statut_diffusion")
    base["diffusionStatus"] = diffusion if isinstance(diffusion, str) else None
    # O is the API's public/full-diffusion value. Missing or other values are
    # intentionally not guessed: names may not be retained in that case.
    if diffusion != "O":
        base["reason"] = ("statut_diffusion absent" if diffusion is None
                           else "not full public diffusion")
        return base
    name = result.get("nom_complet")
    if not isinstance(name, str) or not name.strip():
        base["reason"] = "exact public result has no legal entity name"
        return base
    base["name"] = name.strip()
    state = result.get("etat_administratif")
    base["administrativeState"] = state if state in ('A', 'C') else None
    base["status"] = "available"
    return base


def validate(identities, coverage, all_sirens=None):
    assert isinstance(identities.get("identities"), list)
    ids = identities["identities"]
    assert len(ids) == coverage['counts']['universe'] and len({x.get("siren") for x in ids}) == len(ids)
    assert all(SIREN_RE.fullmatch(x["siren"]) for x in ids)
    allowed = {"siren", "name", "administrativeState", "diffusionStatus", "source", "retrievedAt", "status", "reason", "associatedSirets"}
    for item in ids:
        assert set(item) <= allowed
        assert item["status"] in ("available", "unavailable")
        assert item["status"] == "available" or item["name"] is None
        assert item['status'] != 'available' or (item['diffusionStatus'] == 'O' and isinstance(item['name'], str) and item['name'].strip())
        assert item['source'] == query_url(item['siren'])
        assert item["source"].startswith(API + "?")
        assert item["status"] == "available" or item["reason"]
    assert coverage['counts']['selected'] == len(ids)
    assert coverage['selection']['selectedSirens'] == [x['siren'] for x in ids]
    if all_sirens is not None:
        assert len(all_sirens) == coverage['counts']['universe']
        assert sorted(all_sirens, key=lambda s: hashlib.sha256(s.encode('ascii')).hexdigest()) == [x['siren'] for x in ids]


def profiles_from(identities):
    return {p["siren"]: {k: p.get(k) for k in ["siren", "name", "administrativeState", "diffusionStatus", "source", "retrievedAt", "status"]}
            for p in identities["identities"]
            if p.get("status") == "available" and p.get("diffusionStatus") == "O" and p.get("source") == query_url(p["siren"])}


def apply_profiles(data, identities):
    """Write supplierProfiles into each DECP dataset; names never replace published identifiers."""
    profiles = profiles_from(identities)
    for name, coverage_name in DATASETS:
        rows = json.loads((data / name).read_text())
        for row in rows:
            sirens = {s.get("siren") for s in row.get("supplierIds") or []}
            row["supplierProfiles"] = [profiles[s] for s in sorted(sirens - {None}) if s in profiles]
        coverage = json.loads((data / coverage_name).read_text())
        coverage["identityEnrichment"] = {"snapshot": "supplier-identities.json", "coverage": "supplier-identities-coverage.json",
            "contractsWithCurrentNames": sum(bool(r["supplierProfiles"]) for r in rows), "availableSirens": len(profiles),
            "historicalNamesVerified": False,
            "matching": "SIREN derived only from typed French SIRET/SIREN; names do not replace published contract identifiers."}
        (data / name).write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n")
        (data / coverage_name).write_text(json.dumps(coverage, ensure_ascii=False, indent=2) + "\n")
        print(f"{name}: {coverage['identityEnrichment']['contractsWithCurrentNames']}/{len(rows)} rows with a current public name")


def cohort_rows(data):
    return [row for name, _ in DATASETS for row in json.loads((data / name).read_text())]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline", action="store_true", help="validate existing sanitized outputs; never network")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    data = root / "data"
    out = data / "supplier-identities.json"
    cov = data / "supplier-identities-coverage.json"
    if args.offline:
        identities, coverage = json.loads(out.read_text()), json.loads(cov.read_text())
        validate(identities, coverage, suppliers(cohort_rows(data)))
        print(f"offline valid: {len(identities['identities'])} identities; {coverage['counts']['unavailable']} unavailable")
        apply_profiles(data, identities)
        return

    rows = cohort_rows(data)
    all_sirens, selected = selection(rows)
    # Checkpoint: an interrupted run resumes from the lookups already made.
    checkpoint = data / ".supplier-identities.partial.json"
    done = json.loads(checkpoint.read_text()) if checkpoint.exists() else {"retrievedAt": now(), "lookups": {}}
    retrieved = done["retrievedAt"]
    records = []
    query_log = []
    for index, siren in enumerate(selected):
        url = query_url(siren)
        if siren not in done["lookups"]:
            time.sleep(0.3)
            queried_at = now()
            done["lookups"][siren] = {"queriedAt": queried_at, "record": clean_result(siren, url, fetch(url), now())}
            checkpoint.write_text(json.dumps(done, ensure_ascii=False))
        record = dict(done["lookups"][siren]["record"])
        query_log.append({"siren": siren, "url": url, "queriedAt": done["lookups"][siren]["queriedAt"], "status": record["status"]})
        if all_sirens[siren]:
            record["associatedSirets"] = sorted(all_sirens[siren])
        records.append(record)
        print(f"{index + 1}/{len(selected)} {siren}: {record['status']}")

    identities = {
        "retrievedAt": retrieved,
        "selection": {"method": "every distinct typed French supplier SIREN in the six-city and Paris & Ardèche DECP cohorts, sorted by SHA256", "hash": "SHA-256 lowercase hexadecimal of SIREN", "universe": len(all_sirens), "selected": len(selected)},
        "identities": records,
    }
    unavailable = [x for x in records if x["status"] == "unavailable"]
    coverage = {
        "retrievedAt": retrieved,
        "source": "API publique Recherche d’entreprises / Annuaire des entreprises — current public identity by SIREN; not independently verified historical Sirene/RNE names",
        "api": API,
        "scope": "Current administrative information only; no RNE or Sirene historical claim. No addresses, officers, personal contacts, or raw API responses retained.",
        "selection": {"method": identities["selection"]["method"], "selectedSirens": selected},
        "counts": {"universe": len(all_sirens), "selected": len(selected), "queried": len(records), "available": len(records) - len(unavailable), "unavailable": len(unavailable), "excludedFromSelection": len(all_sirens) - len(selected)},
        "unavailableReasons": {reason: sum(x["reason"] == reason for x in unavailable) for reason in sorted({x["reason"] for x in unavailable})},
        "queries": {"count": len(records), "minimumIntervalSeconds": 0.3, "retries": 7, "dates": {"retrievalStartedAt": retrieved, "completedAt": now()}, "log": query_log},
        "temporalScope": "retrievedAt on the snapshot denotes retrieval start; per-query log timestamps record requests. Current unit-level administrative state, not historical or establishment state.",
        "selectionDenominator": "Distinct typed supplier SIRENs in normalized non-conflicting supplierIds; ambiguous initial supplier variants are not assigned a name. Every identity uses exact SIREN matching; names do not establish relationships.",
        "conservativeDiffusionChoice": "Only statut_diffusion == O permits retaining nom_complet. Missing statut_diffusion is unavailable; no field is fabricated.",
    }
    validate(identities, coverage, all_sirens)
    out.write_text(json.dumps(identities, ensure_ascii=False, indent=2) + "\n")
    cov.write_text(json.dumps(coverage, ensure_ascii=False, indent=2) + "\n")
    checkpoint.unlink()
    print(f"wrote {out} and {cov}: {len(records)} queried, {len(unavailable)} unavailable")
    apply_profiles(data, identities)


if __name__ == "__main__":
    main()
