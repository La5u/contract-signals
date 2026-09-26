#!/usr/bin/env python3
"""United Kingdom Find a Tender cohort: three buyers announced before their notices were read.

  --discover  page through every award release published 2024-09-01 → 2026-09-01
              (Find a Tender OCDS API, stages=award) and keep a compact index only:
              notice id, release date, buyer party ids, names and TED buyer type.
              No bids, suppliers or values are read. Saved gzipped under data/uk-fts/raw/.
  --download  fetch the full OCDS release package of every indexed notice of the
              announced buyers, saved gzipped (exact response bytes) under data/uk-fts/raw/notices/
  --offline   rebuild data/uk-fts.json and its coverage file from the raw notices

Contact points (names, emails, telephones) are never imported. Licence: Open Government
Licence v3.0, as declared in every release package.
"""
import argparse
import gzip
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/uk-fts/raw"
EXTRACT = ROOT / "data/uk-fts.json"
COVERAGE = ROOT / "data/uk-fts-coverage.json"
API = "https://www.find-tender.service.gov.uk/api/1.0/ocdsReleasePackages"
PORTAL = "https://www.find-tender.service.gov.uk/Notice/{notice_id}"
START, END = "2024-09-01", "2026-09-01"
COHORT = "uk-fts-3buyers-2024-2026"
UA = {"User-Agent": "contract-signals/0.1 (public research; offline snapshot)", "Accept": "application/json"}
# Announced on 2026-09-26 after --discover and before any notice was downloaded or read.
# Rule, from the compact index only (volume and buyer type, no notice content): per level,
# the Find a Tender organisation id with the most award notices in the window, leaving out
# ids above 500 notices so the cohort stays reviewable (Surrey County Council 1,841; London
# Borough of Merton 1,033; the Sutton-Kingston joint account 452 is not a single council).
# One id is one buyer: other accounts of the same organisation are not merged by name.
BUYERS = [
    {"id": "GB-FTS-131", "name": "Foreign Commonwealth and Development Office", "level": "national", "indexNotices": 87},
    {"id": "GB-FTS-39", "name": "Lincolnshire County Council", "level": "regional", "indexNotices": 141},
    {"id": "GB-FTS-289", "name": "Milton Keynes Council", "level": "municipal", "indexNotices": 288},
]


def get_bytes(url):
    for attempt in range(8):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404 or attempt == 7:
                raise
            time.sleep(int(e.headers.get("Retry-After") or 0) or 10 * (attempt + 1))  # 429 under bursts
        except Exception:
            if attempt == 7:
                raise
            time.sleep(5 * (attempt + 1))


def discover():
    """Compact index of every award release in the window, one-day windows, saved per month.

    The API cursor repeats releases across pages and, over month-long windows, skips
    some; one-day windows deduplicated by notice id matched 24 one-hour windows exactly
    on a test day (2024-09-26: 149 returned, 101 unique, 101 by hour)."""
    index_dir = RAW / "index"
    index_dir.mkdir(parents=True, exist_ok=True)
    day = datetime.fromisoformat(START)
    end = datetime.fromisoformat(END)
    while day < end:
        month = day.strftime("%Y-%m")
        path = index_dir / f"{month}.json.gz"
        nxt_month = (day.replace(day=28) + timedelta(days=4)).replace(day=1)
        if path.exists():
            day = nxt_month
            continue
        entries, requests, returned = {}, 0, 0
        while day < min(nxt_month, end):
            url = API + "?" + urllib.parse.urlencode({"stages": "award", "limit": 100, "updatedFrom": day.strftime("%Y-%m-%dT00:00:00"),
                                                     "updatedTo": (day + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00")})
            while url:
                data = json.loads(get_bytes(url))
                requests += 1
                releases = data.get("releases") or []
                returned += len(releases)
                for rel in releases:
                    buyers = [{"id": p.get("id"), "name": p.get("name"),
                               "type": next((c.get("id") for c in (p.get("details") or {}).get("classifications") or [] if c.get("scheme") == "TED_CA_TYPE"), None)}
                              for p in rel.get("parties") or [] if "buyer" in (p.get("roles") or [])]
                    entries[rel["id"]] = {"id": rel["id"], "ocid": rel.get("ocid"), "date": (rel.get("date") or "")[:10], "buyers": buyers}
                url = (data.get("links") or {}).get("next") if len(releases) >= 100 else None
                time.sleep(1)
            day += timedelta(days=1)
        path.write_bytes(gzip.compress((json.dumps({"month": month, "requests": requests, "returned": returned,
                                                    "releases": sorted(entries.values(), key=lambda e: e["id"])},
                                                   ensure_ascii=False) + "\n").encode("utf-8"), mtime=0))
        print(month, len(entries), "unique award releases,", returned, "returned,", requests, "requests", flush=True)


# procurementMethod as published (OCDS codelist): open and selective are competitive
# calls; limited covers awards without prior publication and direct awards.
COMPETITIVE = {"open", "selective"}
DIRECT = {"limited"}


def offers_for(release, lot_id, single_lot):
    stats = [s for s in (release.get("bids") or {}).get("statistics") or [] if s.get("measure") == "bids"]
    match = [s for s in stats if s.get("relatedLot") == lot_id] or ([s for s in stats if not s.get("relatedLot")] if single_lot else [])
    return match[0]["value"] if len(match) == 1 and isinstance(match[0].get("value"), int) else None


def notice_rows(release):
    tender = release.get("tender") or {}
    lots = {l.get("id"): l for l in tender.get("lots") or []}
    parties = {p.get("id"): p for p in release.get("parties") or []}
    buyer = next((p for p in release.get("parties") or [] if "buyer" in (p.get("roles") or [])), {})
    contracts = {c.get("awardID"): c for c in release.get("contracts") or []}
    method = tender.get("procurementMethod")
    direct = False if method in COMPETITIVE else True if method in DIRECT else None
    rows, excluded = [], {}
    for award in release.get("awards") or []:
        suppliers = award.get("suppliers") or []
        why = ("award not active (" + str(award.get("status")) + ")" if award.get("status") != "active" else
               "not exactly one supplier" if len(suppliers) != 1 else
               "award covers several lots" if len(award.get("relatedLots") or []) > 1 else None)
        if why:
            excluded[why] = excluded.get(why, 0) + 1
            continue
        lot_id = (award.get("relatedLots") or [None])[0]
        supplier = suppliers[0]
        party = parties.get(supplier.get("id")) or {}
        ids = [{"id": supplier["id"], "identifierType": "GB-FTS"}] if supplier.get("id") else []
        coh = [x for x in [party.get("identifier") or {}] + (party.get("additionalIdentifiers") or []) if x.get("scheme") == "GB-COH" and x.get("id")]
        ids += [{"id": str(coh[0]["id"]), "identifierType": "GB-COH"}] if coh else []
        contract = contracts.get(award.get("id")) or {}
        value = contract.get("value") or award.get("value") or {}
        lot = lots.get(lot_id) or {}
        offers = offers_for(release, lot_id, len(lots) <= 1) if direct is False else None
        rows.append({
            "id": f"fts-{release['id']}-{award['id'].rsplit('-', 1)[-1]}", "cohortId": COHORT, "dataFamily": "fts", "country": "GBR",
            "dataStatus": "verified", "date": (contract.get("dateSigned") or award.get("date") or release.get("date") or "")[:10] or None,
            "dateNote": "Contract signature date (dateSigned), else the award or notice date.",
            "buyer": buyer.get("name"), "buyerId": buyer.get("id"),
            "supplier": supplier.get("name"), "supplierIds": ids,
            "description": " — ".join(dict.fromkeys(x for x in [tender.get("title"), lot.get("title")] if x)),
            "amount": value.get("amount"), "currency": value.get("currency"),
            "procedure": tender.get("procurementMethodDetails") or method, "procedureCode": method, "procedureDirect": direct,
            "offers": offers, "offersNote": None if offers is not None else "No bid count published for this lot: offers unknown, never zero.",
            "cpv": ((tender.get("classification") or {}).get("id") or "")[:8] or None, "lotId": lot_id, "lotCount": len(lots),
            "noticeId": release["id"], "procedureId": release.get("ocid"), "awardId": award.get("id"),
            "source": f"{API}/{release['id']}", "sourceLabel": "Find a Tender — official OCDS release package (JSON)",
            "portalUrl": PORTAL.format(notice_id=release["id"]),
            "amountBasis": "Contract value as published in the notice (GBP unless stated); not a payment, never converted.",
            "notes": "Find a Tender award notice. Contact points are not imported. Supplier identity is the Find a Tender party id (plus Companies House number when published)."})
    return rows, excluded


def offline():
    manifest = json.loads((RAW / "manifest.json").read_text(encoding="utf-8"))
    if [b["id"] for b in manifest["buyers"]] != [b["id"] for b in BUYERS]:
        raise ValueError("Raw manifest does not describe the announced cohort")
    wanted = {b["id"] for b in BUYERS}
    rows, excluded, methods, other = [], {}, {}, 0
    for notice in manifest["noticeIds"]:
        package = json.loads(gzip.decompress((RAW / "notices" / f"{notice}.json.gz").read_bytes()))
        for release in package["releases"]:
            buyer = next((p for p in release.get("parties") or [] if "buyer" in (p.get("roles") or [])), {})
            if buyer.get("id") not in wanted:
                other += 1
                continue
            methods[(release.get("tender") or {}).get("procurementMethod")] = methods.get((release.get("tender") or {}).get("procurementMethod"), 0) + 1
            got, why = notice_rows(release)
            rows += got
            for k, v in why.items():
                excluded[k] = excluded.get(k, 0) + v
    if len({r["id"] for r in rows}) != len(rows):
        raise ValueError("duplicate row ids")
    rows.sort(key=lambda r: (r["date"] or "", r["id"]))
    EXTRACT.write_text(json.dumps(rows, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    index_total = sum(1 for _ in index_entries())
    coverage = {"source": API, "license": "Open Government Licence v3.0 (declared in every release package)",
                "licenseUrl": "http://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/",
                "attribution": "Find a Tender service, Cabinet Office (UK)",
                "cohort": {"cohortId": COHORT, "buyers": BUYERS, "window": manifest["window"],
                           "selection": "Announced on 2026-09-26 after a compact index of every award release in the window (notice id, date, buyer id, name and type only) and before any notice was downloaded: per level, the buyer id with the most award notices, leaving out ids above 500 notices."},
                "retrieval": {"startedAt": manifest["retrievalStartedAt"], "finishedAt": manifest.get("retrievalFinishedAt"),
                              "indexedAwardReleases": index_total, "noticesDownloaded": len(manifest["noticeIds"]), "rawDirectory": "data/uk-fts/raw"},
                "counts": {"procurementMethods": dict(sorted(methods.items(), key=lambda kv: -kv[1])), "retainedAwards": len(rows),
                           "excludedAwards": excluded, "otherBuyerReleases": other, "withOffers": sum(r["offers"] is not None for r in rows),
                           "withCompaniesHouseNumber": sum(any(x["identifierType"] == "GB-COH" for x in r["supplierIds"]) for r in rows),
                           "currencies": sorted({r["currency"] for r in rows if r["currency"]})},
                "limitations": ["Three buyer accounts, not a country sample; other accounts of the same organisations are not merged by name.",
                                "Find a Tender publishes above-threshold notices (and, since 24 February 2025, Procurement Act notices); smaller contracts are not covered.",
                                "Supplier party ids are never shared by different names in this cohort, but one supplier can have several ids: repetition and concentration can only be undercounted.",
                                "Multi-supplier awards (frameworks, dynamic purchasing systems) are excluded: no single holder.",
                                "Amounts are as published, never converted or summed across currencies."],
                "reproduce": ["python tools/import-find-a-tender.py --offline", "python tools/import-find-a-tender.py --discover --download"]}
    COVERAGE.write_text(json.dumps(coverage, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(coverage["counts"], ensure_ascii=False))


def index_entries():
    for path in sorted((RAW / "index").glob("*.json.gz")):
        yield from json.loads(gzip.decompress(path.read_bytes()))["releases"]


def download():
    wanted = {b["id"] for b in BUYERS}
    notices = sorted({e["id"] for e in index_entries() if any(b["id"] in wanted for b in e["buyers"])})
    manifest = {"cohortId": COHORT, "window": {"startInclusive": START, "endExclusive": END, "basis": "award release date (API updatedFrom/updatedTo, one-day windows)"},
                "buyers": BUYERS, "noticeIds": notices, "retrievalStartedAt": datetime.now(timezone.utc).isoformat()}
    for n, notice in enumerate(notices):
        path = RAW / "notices" / f"{notice}.json.gz"
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(gzip.compress(get_bytes(f"{API}/{notice}"), mtime=0))
            time.sleep(1)
        if n % 50 == 0:
            print(n, "/", len(notices), flush=True)
    manifest["retrievalFinishedAt"] = datetime.now(timezone.utc).isoformat()
    (RAW / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


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
