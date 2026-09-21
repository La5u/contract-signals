#!/usr/bin/env python3
"""Enrich the deterministic first 100 supplier SIRENs in the city DECP cohort.

Normal mode reads data/decp-cities.json and queries Recherche entreprises.  The
result is deliberately a small, public-only snapshot; --offline validates that
snapshot without making network requests.
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
LIMIT = 100
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
    return all_sirens, ordered[:LIMIT]


def query_url(siren):
    # Keep this URL as the exact provenance of the query (rather than a broad
    # search URL or a URL to an unfiltered API response).
    return API + "?" + urllib.parse.urlencode({"q": siren, "per_page": 25})


def fetch(url, attempts=4):
    last = None
    for attempt in range(attempts):
        if attempt:
            time.sleep(0.3 * (2 ** (attempt - 1)))
        try:
            with urllib.request.urlopen(url, timeout=45) as response:
                return json.load(response)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
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
    assert len(ids) == min(LIMIT, coverage['counts']['universe']) and len({x.get("siren") for x in ids}) == len(ids)
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
        assert sorted(all_sirens, key=lambda s: hashlib.sha256(s.encode('ascii')).hexdigest())[:LIMIT] == [x['siren'] for x in ids]


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
        validate(identities, coverage, suppliers(json.loads((data / 'decp-cities.json').read_text())))
        print(f"offline valid: {len(identities['identities'])} identities; {coverage['counts']['unavailable']} unavailable")
        return

    rows = json.loads((data / "decp-cities.json").read_text())
    all_sirens, selected = selection(rows)
    retrieved = now()
    records = []
    query_log = []
    for index, siren in enumerate(selected):
        if index:
            time.sleep(0.3)
        url = query_url(siren)
        queried_at = now()
        payload = fetch(url)
        record = clean_result(siren, url, payload, now())
        query_log.append({"siren": siren, "url": url, "queriedAt": queried_at, "status": record["status"]})
        if all_sirens[siren]:
            record["associatedSirets"] = sorted(all_sirens[siren])
        records.append(record)
        print(f"{index + 1}/{LIMIT} {siren}: {record['status']}")

    identities = {
        "retrievedAt": retrieved,
        "selection": {"method": "first 100 distinct typed French supplier SIRENs sorted by SHA256", "hash": "SHA-256 lowercase hexadecimal of SIREN", "universe": len(all_sirens), "selected": len(selected)},
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
        "queries": {"count": len(records), "minimumIntervalSeconds": 0.3, "retries": 4, "dates": {"retrievalStartedAt": retrieved, "completedAt": now()}, "log": query_log},
        "temporalScope": "retrievedAt on the snapshot denotes retrieval start; per-query log timestamps record requests. Current unit-level administrative state, not historical or establishment state.",
        "selectionDenominator": "Distinct typed supplier SIRENs in normalized non-conflicting supplierIds; ambiguous initial supplier variants are not assigned a name. All 100 selected identities use exact SIREN matching; names do not establish relationships.",
        "conservativeDiffusionChoice": "Only statut_diffusion == O permits retaining nom_complet. Missing statut_diffusion is unavailable; no field is fabricated.",
    }
    validate(identities, coverage, all_sirens)
    out.write_text(json.dumps(identities, ensure_ascii=False, indent=2) + "\n")
    cov.write_text(json.dumps(coverage, ensure_ascii=False, indent=2) + "\n")
    print(f"wrote {out} and {cov}: {LIMIT} queried, {len(unavailable)} unavailable")


if __name__ == "__main__":
    main()
