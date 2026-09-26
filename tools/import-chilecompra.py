#!/usr/bin/env python3
"""Chile Mercado Público (ChileCompra) cohort: three buyers announced before their tenders were read.

  --discover  list every tender code published 2024-09 → 2026-08 (OCDS API listaOCDSAgnoMes),
              then fetch one tender per purchasing-unit prefix (the part before the first
              dash) to learn which buyer that prefix belongs to. Only codes, buyer ids and
              buyer names are kept. Saved gzipped under data/chile-mp/raw/.
  --download  fetch the tender and award OCDS releases of every listed code of the
              announced buyers, gzipped (exact response bytes) under data/chile-mp/raw/records/
  --offline   rebuild data/chile-mp.json and its coverage file from the raw records

Licence: CC0 1.0, declared in every release package by the Dirección de Compras y
Contratación Pública. Contact points are never imported.
"""
import argparse
import gzip
import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/chile-mp/raw"
EXTRACT = ROOT / "data/chile-mp.json"
COVERAGE = ROOT / "data/chile-mp-coverage.json"
API = "https://api.mercadopublico.cl/APISOCDS/OCDS"
PORTAL = "https://www.mercadopublico.cl/Procurement/Modules/RFB/DetailsAcquisition.aspx?idlicitacion={code}"
MONTHS = [f"{y}-{m:02d}" for y, m in [(2024, m) for m in range(9, 13)] + [(2025, m) for m in range(1, 13)] + [(2026, m) for m in range(1, 9)]]
COHORT = "chile-mp-3buyers-2024-2026"
UA = {"User-Agent": "contract-signals/0.1 (public research; offline snapshot)", "Accept": "application/json"}
# Announced on 2026-09-26 after --discover and before any tender or award of these units was
# read. Rule, from the prefix map only (volume and buyer name): per level, the purchasing unit
# with the most listed tenders in the window, leaving out units above 500 tenders; for the
# municipal level, the municipality's own unit, not a department (education, health) unit.
BUYERS = [
    {"id": "CL-MP-2015", "prefix": "1019", "name": "MINISTERIO DE OBRAS PUBLICAS DIRECCION GRAL DE OO PP DCYF", "level": "national", "listedTenders": 274},
    {"id": "CL-MP-2592", "prefix": "1596", "name": "GOBIERNO REGIONAL VII REGION", "level": "regional", "listedTenders": 91},
    {"id": "CL-MP-3414", "prefix": "2422", "name": "I MUNICIPALIDAD DE PUENTE ALTO", "level": "municipal", "listedTenders": 479},
]


def get_bytes(url):
    for attempt in range(8):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404 or attempt == 7:
                raise
            time.sleep(10 * (attempt + 1))
        except Exception:
            if attempt == 7:
                raise
            time.sleep(10 * (attempt + 1))


def save_gz(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gzip.compress(data, mtime=0))


def load_gz(path):
    return json.loads(gzip.decompress(path.read_bytes()))


def discover():
    RAW.mkdir(parents=True, exist_ok=True)
    listing = RAW / "listing"
    for month in MONTHS:
        path = listing / f"{month}.json.gz"
        if path.exists():
            continue
        y, m = month.split("-")
        codes, offset, total = [], 0, None
        while total is None or offset < total:
            data = json.loads(get_bytes(f"{API}/listaOCDSAgnoMes/{y}/{m}/{offset}/1000"))
            if offset == 0 and data.get("status") == 404:
                # Observed for 2026-08 on 2026-09-26 ("No se encontraron resultados"): recorded, not skipped.
                total = 0
                break
            total = data["pagination"]["total"] if total is None else total
            if data["pagination"]["total"] != total:
                raise RuntimeError("listing total changed while paging " + month)
            codes += [d["ocid"].split("-", 2)[2] for d in data["data"]]
            offset += 1000
            time.sleep(0.5)
        if len(codes) != total:
            raise RuntimeError(f"{month}: {len(codes)} codes listed, total {total}")
        save_gz(path, (json.dumps({"month": month, "total": total, "codes": sorted(set(codes)),
                                   "note": None if total else "API answered 404 No se encontraron resultados"}) + "\n").encode("utf-8"))
        print(month, total, "tenders listed", flush=True)
    prefixes_path = RAW / "prefixes.json.gz"
    prefixes = load_gz(prefixes_path) if prefixes_path.exists() else {}
    counts = {}
    for month in MONTHS:
        for code in load_gz(listing / f"{month}.json.gz")["codes"]:
            counts.setdefault(code.split("-")[0], []).append(code)
    for n, (prefix, codes) in enumerate(sorted(counts.items())):
        if prefix in prefixes:
            continue
        buyer, sample = {}, None
        for code in codes[:5]:  # a listed code can answer 404; try a few before giving up
            try:
                release = json.loads(get_bytes(f"{API}/tender/{code}"))["releases"][0]
            except (urllib.error.HTTPError, KeyError, IndexError):
                continue
            buyer = next((p for p in release.get("parties") or [] if "buyer" in (p.get("roles") or [])), {})
            sample = code
            break
        prefixes[prefix] = {"sample": sample, "tenders": len(codes), "buyerId": buyer.get("id"), "buyerName": buyer.get("name")}
        if n % 100 == 0:
            save_gz(prefixes_path, (json.dumps(prefixes, ensure_ascii=False) + "\n").encode("utf-8"))
            print(n, "prefixes", flush=True)
        time.sleep(0.3)
    save_gz(prefixes_path, (json.dumps(dict(sorted(prefixes.items())), ensure_ascii=False) + "\n").encode("utf-8"))
    print(len(prefixes), "purchasing-unit prefixes mapped", flush=True)


def listed_codes(prefix):
    for month in MONTHS:
        for code in load_gz(RAW / "listing" / f"{month}.json.gz")["codes"]:
            if code.split("-")[0] == prefix:
                yield month, code


def download():
    manifest = {"cohortId": COHORT, "window": {"months": [MONTHS[0], MONTHS[-1]], "basis": "listaOCDSAgnoMes listing month"},
                "buyers": [], "retrievalStartedAt": datetime.now(timezone.utc).isoformat()}
    for buyer in BUYERS:
        codes = sorted({code for _, code in listed_codes(buyer["prefix"])})
        manifest["buyers"].append({**buyer, "codes": codes})
        for n, code in enumerate(codes):
            for stage in ("tender", "award"):
                path = RAW / "records" / stage / f"{code}.json.gz"
                if path.exists() or (RAW / "records" / stage / f"{code}.none").exists():
                    continue
                try:
                    save_gz(path, get_bytes(f"{API}/{stage}/{code}"))
                except urllib.error.HTTPError as e:
                    if e.code != 404:
                        raise
                    (RAW / "records" / stage).mkdir(parents=True, exist_ok=True)
                    (RAW / "records" / stage / f"{code}.none").write_text("404\n")  # no award published (yet)
                time.sleep(0.3)
            if n % 50 == 0:
                print(buyer["id"], n, "/", len(codes), flush=True)
    manifest["retrievalFinishedAt"] = datetime.now(timezone.utc).isoformat()
    (RAW / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def api_error(path):
    """The API answers some errors inside an HTTP 200 body ({"status": 500, "detail": ...})."""
    body = load_gz(path)
    return body.get("status") if isinstance(body, dict) and "releases" not in body else None


def retry_errors(rounds=3):
    for _ in range(rounds):
        failed = [p for p in sorted((RAW / "records").glob("*/*.json.gz")) if api_error(p) not in (None, 404)]
        for path in failed:
            save_gz(path, get_bytes(f"{API}/{path.parent.name}/{path.name[:-8]}"))
            time.sleep(1)
        print(len(failed), "records re-fetched after an in-body API error", flush=True)


def tender_kind(details):
    """Competitive character from the published procedure name; this source lists licitaciones only."""
    text = (details or "").lower()
    return False if text.startswith("licitación pública") or text.startswith("licitación privada") else None


def award_rows(code, tender_release, award_package):
    tender = (tender_release or {}).get("tender") or {}
    release = award_package["releases"][0]
    parties = {p.get("id"): p for p in release.get("parties") or []}
    tenderers = sum(1 for p in release.get("parties") or [] if "tenderer" in (p.get("roles") or []))
    buyer = next((p for p in release.get("parties") or [] if "buyer" in (p.get("roles") or [])), {})
    rows, excluded = [], {}
    for award in release.get("awards") or []:
        suppliers = award.get("suppliers") or []
        why = ("award not active (" + str(award.get("status")) + ")" if award.get("status") != "active" else
               "not exactly one supplier (line items split, no per-supplier amount)" if len(suppliers) != 1 else None)
        if why:
            excluded[why] = excluded.get(why, 0) + 1
            continue
        party = parties.get(suppliers[0].get("id")) or {}
        ident = party.get("identifier") or {}
        ids = [{"id": str(ident["id"]), "identifierType": "CL-RUT"}] if ident.get("scheme") == "CL-RUT" and ident.get("id") else []
        segments = [((i.get("classification") or {}).get("id") or "")[:2] for i in award.get("items") or [] if (i.get("classification") or {}).get("scheme") == "UNSPSC"]
        category = min(set(segments), key=lambda seg: (-segments.count(seg), seg)) if segments else None  # most frequent, then lowest code
        value = award.get("value") or {}
        direct = tender_kind(tender.get("procurementMethodDetails"))
        rows.append({
            "id": f"chile-{code}-{award.get('id')}", "cohortId": COHORT, "dataFamily": "chile", "country": "CHL",
            "dataStatus": "verified", "date": (award.get("date") or "")[:10] or None,
            "dateNote": "Award date (awards.date); the contract signature date is not in this source.",
            "buyer": (buyer.get("name") or "").split(" | ")[0] or None, "buyerId": buyer.get("id"),
            "supplier": (suppliers[0].get("name") or "").split(" | ")[0] or None, "supplierIds": ids,
            "description": tender.get("title") or award.get("title"),
            "amount": value.get("amount"), "currency": value.get("currency"),
            "procedure": tender.get("procurementMethodDetails") or None, "procedureCode": code.rsplit("-", 1)[-1][:2], "procedureDirect": direct,
            "offers": tenderers if direct is False and tenderers > 0 else None,
            "offersNote": "Tenderers on the whole tender, not per line item." if direct is False and tenderers > 0 else "No tenderer published: offers unknown, never zero.",
            "category": category, "cpv": None, "lotId": None, "procedureId": release.get("ocid"), "tenderCode": code, "awardId": award.get("id"),
            "source": f"{API}/award/{code}", "sourceLabel": "Mercado Público — official OCDS award release (JSON)",
            "portalUrl": PORTAL.format(code=code),
            "amountBasis": "Awarded value as published (CLP unless stated; may include several line items); not a payment, never converted.",
            "notes": "Mercado Público licitación. Contact points are not imported. Supplier identity is the RUT (Chilean tax number)."})
    return rows, excluded


def offline():
    manifest = json.loads((RAW / "manifest.json").read_text(encoding="utf-8"))
    if [b["id"] for b in manifest["buyers"]] != [b["id"] for b in BUYERS]:
        raise ValueError("Raw manifest does not describe the announced cohort")
    rows, excluded, kinds, other = [], {}, {}, 0
    for buyer in manifest["buyers"]:
        for code in buyer["codes"]:
            tpath, apath = RAW / "records" / "tender" / f"{code}.json.gz", RAW / "records" / "award" / f"{code}.json.gz"
            tender = load_gz(tpath)["releases"][0] if tpath.exists() and api_error(tpath) is None else None
            details = ((tender or {}).get("tender") or {}).get("procurementMethodDetails") or "tender record unavailable"
            kinds[details] = kinds.get(details, 0) + 1
            if not apath.exists() or api_error(apath) == 404:
                excluded["no award published"] = excluded.get("no award published", 0) + 1
                continue
            if api_error(apath) is not None:
                excluded["award record unavailable (API error)"] = excluded.get("award record unavailable (API error)", 0) + 1
                continue
            package = load_gz(apath)
            if not package.get("releases"):
                excluded["award package with no release"] = excluded.get("award package with no release", 0) + 1
                continue
            party = next((p for p in package["releases"][0].get("parties") or [] if "buyer" in (p.get("roles") or [])), {})
            if party.get("id") != buyer["id"]:
                other += 1
                continue
            got, why = award_rows(code, tender, package)
            rows += got
            for k, v in why.items():
                excluded[k] = excluded.get(k, 0) + v
    if len({r["id"] for r in rows}) != len(rows):
        raise ValueError("duplicate row ids")
    rows.sort(key=lambda r: (r["date"] or "", r["id"]))
    EXTRACT.write_text(json.dumps(rows, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    listed = {m: load_gz(RAW / "listing" / f"{m}.json.gz") for m in MONTHS}
    coverage = {"source": API, "license": "CC0 1.0 (declared in every release package)", "licenseUrl": "https://creativecommons.org/publicdomain/zero/1.0/",
                "attribution": "Dirección de Compras y Contratación Pública (ChileCompra), Mercado Público",
                "cohort": {"cohortId": COHORT, "buyers": BUYERS, "window": manifest["window"],
                           "selection": "Announced on 2026-09-26 after a map of every purchasing-unit prefix to its buyer (one tender read per prefix, buyer id and name only) and before any tender or award of the chosen units was read: per level, the unit with the most listed tenders, leaving out units above 500."},
                "retrieval": {"startedAt": manifest["retrievalStartedAt"], "finishedAt": manifest.get("retrievalFinishedAt"),
                              "listedTendersInWindow": sum(v["total"] for v in listed.values()),
                              "emptyMonths": [m for m, v in listed.items() if not v["total"]], "rawDirectory": "data/chile-mp/raw"},
                "counts": {"tendersListed": sum(len(b["codes"]) for b in manifest["buyers"]), "procedureTypes": dict(sorted(kinds.items(), key=lambda kv: -kv[1])),
                           "retainedAwards": len(rows), "excluded": excluded, "otherBuyer": other,
                           "withOffers": sum(r["offers"] is not None for r in rows), "withRut": sum(bool(r["supplierIds"]) for r in rows),
                           "currencies": sorted({r["currency"] for r in rows if r["currency"]})},
                "limitations": ["Three purchasing units, not a country sample.",
                                "This OCDS listing covers licitaciones only; direct deals (trato directo) are published as purchase orders and are not included.",
                                "Tenderers are counted on the whole tender, not per line item; awards split among several suppliers are excluded (no per-supplier amount).",
                                "The listing API answered 404 for August 2026 on 2026-09-26; that month is recorded as empty.",
                                "Amounts as published (CLP, sometimes UF or USD), never converted."],
                "reproduce": ["python tools/import-chilecompra.py --offline", "python tools/import-chilecompra.py --discover --download"]}
    COVERAGE.write_text(json.dumps(coverage, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(coverage["counts"], ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--discover", action="store_true")
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    if args.discover:
        discover()
    if args.download:
        download()
    if args.offline or args.download:
        offline()
