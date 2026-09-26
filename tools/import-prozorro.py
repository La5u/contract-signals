#!/usr/bin/env python3
"""Ukraine Prozorro cohort: three buyers announced before download.

  --download  list each buyer's tenders (prozorro.gov.ua search, discovery only), resolve
              each tenderID to its internal id, and save the official record from the
              public API (public-api.prozorro.gov.ua/api/2.5) gzipped under data/prozorro/raw/
  --offline   rebuild data/prozorro.json and its coverage file from the raw records

Only official public-API records are used as data; the website search and details
endpoints only locate them. Window: tender dateCreated 2024-09-01 (inclusive) to
2026-09-01 (exclusive). No score, payment check or completeness claim is inferred here.
"""
import argparse
import gzip
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/prozorro/raw"
EXTRACT = ROOT / "data/prozorro.json"
COVERAGE = ROOT / "data/prozorro-coverage.json"
SEARCH = "https://prozorro.gov.ua/api/search/tenders"
DETAILS = "https://prozorro.gov.ua/api/tenders/{tender_id}/details"
API = "https://public-api.prozorro.gov.ua/api/2.5"
PORTAL = "https://prozorro.gov.ua/tender/{tender_id}"
START, END = "2024-09-01", "2026-09-01"
COHORT = "prozorro-3buyers-2024-2026"
# Announced on 2026-09-25 before any tender record was downloaded: one buyer per level,
# chosen by level and a reviewable volume, outside occupied or front-line oblasts.
BUYERS = [
    {"code": "00012925", "name": "Міністерство охорони здоров'я України", "level": "national"},
    {"code": "20089290", "name": "Вінницька обласна державна адміністрація (апарат)", "level": "regional"},
    {"code": "26510514", "name": "Дніпровська міська рада", "level": "municipal"},
]
UA = {"User-Agent": "contract-signals/0.1 (public research; offline snapshot)"}


def get_json(url, method="GET"):
    for attempt in range(6):
        try:
            data = b"" if method == "POST" else None  # the search expects an (empty) POST body
            with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=UA, method=method), timeout=90) as r:
                data = json.load(r)
            if isinstance(data, dict) and ("data" in data or "id" in data or "total" in data):
                return data
            raise ValueError("unexpected payload")
        except Exception:
            if attempt == 5:
                raise
            time.sleep(5 * (attempt + 1))  # 503/429 under load: back off politely


def save_gz(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gzip.compress((json.dumps(value, ensure_ascii=False, indent=1) + "\n").encode("utf-8"), mtime=0))


def load_gz(path):
    return json.loads(gzip.decompress(path.read_bytes()))


def download():
    manifest_path = RAW / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else None
    if manifest is None:
        manifest = {"cohortId": COHORT, "window": {"startInclusive": START, "endExclusive": END, "basis": "official record dateCreated"},
                    "retrievalStartedAt": datetime.now(timezone.utc).isoformat(), "buyers": []}
        for buyer in BUYERS:
            query = SEARCH + "?" + urllib.parse.urlencode({"buyer[]": buyer["code"]})
            first = get_json(query + "&page=1", "POST")  # pages start at 1
            ids, page = [], 1
            while True:
                data = first if page == 1 else get_json(query + f"&page={page}", "POST")
                if data["total"] != first["total"]:
                    raise RuntimeError("search total changed during paging")
                ids += [t["tenderID"] for t in data["data"]]
                page += 1
                if len(ids) >= first["total"] or not data["data"]:
                    break
                time.sleep(1)
            if len(ids) != first["total"] or len(set(ids)) != len(ids):
                raise RuntimeError(f"incomplete or duplicated search listing for {buyer['code']}")
            # A tenderID carries its creation date (UA-YYYY-MM-DD-…): keep the window before fetching.
            in_window = [t for t in ids if START <= t[3:13] < END]
            manifest["buyers"].append({"code": buyer["code"], "searchUrl": query, "searchTotal": first["total"],
                                       "listedTenderIDs": len(ids), "tenderIDs": in_window})
            print(buyer["code"], first["total"], "tenders listed,", len(in_window), "in window", flush=True)
        RAW.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    done = 0
    for buyer in manifest["buyers"]:
        for tender_id in buyer["tenderIDs"]:
            path = RAW / "records" / f"{tender_id}.json.gz"
            if not path.exists():
                internal = get_json(DETAILS.format(tender_id=tender_id))["id"]
                record = get_json(f"{API}/tenders/{internal}")
                if record["data"].get("tenderID") != tender_id:
                    raise RuntimeError("tenderID mismatch for " + tender_id)
                save_gz(path, record)
                time.sleep(0.5)
            done += 1
            if done % 100 == 0:
                print(done, "records", flush=True)
    manifest["retrievalFinishedAt"] = datetime.now(timezone.utc).isoformat()
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


# Procedure types by their meaning in the Prozorro standard (not by any result).
COMPETITIVE = {"aboveThreshold", "aboveThresholdEU", "aboveThresholdUA", "aboveThresholdUA.defense", "belowThreshold",
               "competitiveDialogueEU", "competitiveDialogueUA", "competitiveDialogueEU.stage2", "competitiveDialogueUA.stage2",
               "competitiveOrdering", "esco", "simple.defense", "requestForProposal", "priceQuotation",
               "closeFrameworkAgreementUA", "closeFrameworkAgreementSelectionUA"}
DIRECT = {"negotiation", "negotiation.quick"}
SIGNED = {"active", "terminated"}
IGNORED_BIDS = {"deleted", "draft"}


def supplier_identifier(identifier):
    code = str((identifier or {}).get("id") or "").strip()
    if (identifier or {}).get("scheme") == "UA-EDR" and code.isdigit():
        return {"id": code, "identifierType": "EDRPOU" if len(code) == 8 else "RNOKPP" if len(code) == 10 else "UA-EDR"}
    return {"id": code, "identifierType": "published identifier"} if code else None


def offers_for(tender, lot_id):
    """Offers on this lot: bids whose lot values point to it (or all bids without lots)."""
    bids = [b for b in tender.get("bids") or [] if b.get("status") not in IGNORED_BIDS]
    if not tender.get("bids"):
        return None
    if lot_id:
        return sum(1 for b in bids if any(v.get("relatedLot") == lot_id for v in b.get("lotValues") or []))
    return len(bids)


def disqualified_before(tender, award):
    """Bidders on this lot whose award was declared unsuccessful before the winning
    award: Prozorro creates awards in ranking order, so each one is a better-ranked
    bid set aside. None when the award history lacks dates."""
    if not award.get("date"):
        return None
    same_lot = [a for a in tender.get("awards") or [] if a.get("lotID") == award.get("lotID")]
    if any(not a.get("date") for a in same_lot):
        return None
    return len({a.get("bid_id") for a in same_lot if a.get("status") == "unsuccessful"
                and a.get("bid_id") != award.get("bid_id") and a["date"] <= award["date"]})


def contract_rows(tender):
    kind = tender["procurementMethodType"]
    buyer = tender["procuringEntity"]["identifier"]
    awards = {a["id"]: a for a in tender.get("awards") or []}
    lots = {l["id"]: l for l in tender.get("lots") or []}
    rows, excluded = [], {}
    for contract in tender.get("contracts") or []:
        award = awards.get(contract.get("awardID"))
        why = ("contract not signed (" + str(contract.get("status")) + ")" if contract.get("status") not in SIGNED else
               "no active award" if not award or award.get("status") != "active" else
               "not exactly one supplier" if len(award.get("suppliers") or []) != 1 else None)
        if why:
            excluded[why] = excluded.get(why, 0) + 1
            continue
        supplier = award["suppliers"][0]
        lot_id = award.get("lotID")
        items = [i for i in tender.get("items") or [] if not lot_id or i.get("relatedLot") == lot_id]
        cpv = next((i["classification"]["id"].split("-")[0] for i in items if (i.get("classification") or {}).get("scheme") in ("ДК021", "CPV")), None)
        value = contract.get("value") or award.get("value") or {}
        direct = False if kind in COMPETITIVE else True if kind in DIRECT else None
        offers = offers_for(tender, lot_id) if direct is False else None
        rows.append({
            "id": f"prozorro-{tender['tenderID']}-{contract['id'][:8]}", "cohortId": COHORT, "dataFamily": "prozorro", "country": "UKR",
            "dataStatus": "verified", "date": (contract.get("dateSigned") or contract.get("date") or "")[:10] or None,
            "dateNote": "Contract signature date (dateSigned), or the contract record date when dateSigned is absent.",
            "buyer": buyer.get("legalName") or tender["procuringEntity"].get("name"), "buyerId": buyer.get("id"),
            "supplier": (supplier.get("identifier") or {}).get("legalName") or supplier.get("name"),
            "supplierIds": [x for x in [supplier_identifier(supplier.get("identifier"))] if x],
            "description": " — ".join(dict.fromkeys(x for x in [tender.get("title"), (lots.get(lot_id) or {}).get("title")] if x)),
            "amount": value.get("amount"), "currency": value.get("currency"),
            "procedure": kind, "procedureDirect": direct, "category": tender.get("mainProcurementCategory"), "cpv": cpv,
            "offers": offers, "disqualifiedBefore": disqualified_before(tender, award) if direct is False else None, "offersNote": None if offers is not None else "No bids are published in this record: offers unknown, never zero.",
            "lotId": lot_id, "lotCount": len(lots), "contractId": contract.get("contractID"), "awardId": award["id"],
            "procedureId": tender["id"], "tenderID": tender["tenderID"], "tenderCreated": (tender.get("dateCreated") or "")[:10] or None,
            "complaintCount": len(tender.get("complaints") or []) + sum(len(a.get("complaints") or []) for a in awards.values()),
            "source": f"{API}/tenders/{tender['id']}", "sourceLabel": "Prozorro public API — official tender record (JSON)",
            "portalUrl": PORTAL.format(tender_id=tender["tenderID"]),
            "amountBasis": "Contract value as published (VAT per the record); not a payment. Never converted.",
            "notes": "Prozorro official record. Offers counted from published bids on this lot; the record may hide bids of unfinished stages.",
        })
    return rows, excluded


def offline():
    manifest = json.loads((RAW / "manifest.json").read_text(encoding="utf-8"))
    if [b["code"] for b in manifest["buyers"]] != [b["code"] for b in BUYERS]:
        raise ValueError("Raw manifest does not describe the announced cohort")
    rows, excluded, kinds, outside, other_buyer = [], {}, {}, 0, 0
    for buyer in manifest["buyers"]:
        for tender_id in buyer["tenderIDs"]:
            tender = load_gz(RAW / "records" / f"{tender_id}.json.gz")["data"]
            if not START <= (tender.get("dateCreated") or "")[:10] < END:
                outside += 1
                continue
            if tender["procuringEntity"]["identifier"].get("id") != buyer["code"]:
                other_buyer += 1
                continue
            kinds[tender["procurementMethodType"]] = kinds.get(tender["procurementMethodType"], 0) + 1
            got, why = contract_rows(tender)
            rows += got
            for k, v in why.items():
                excluded[k] = excluded.get(k, 0) + v
    if len({r["id"] for r in rows}) != len(rows):
        raise ValueError("duplicate row ids")
    rows.sort(key=lambda r: (r["tenderCreated"] or "", r["id"]))
    EXTRACT.write_text(json.dumps(rows, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    coverage = {"source": API, "discovery": SEARCH + " (prozorro.gov.ua site search, used only to list tender IDs)",
                "license": "Not declared by the publisher (the Open Contracting data registry lists none); Prozorro data are published as open data under Ukrainian procurement law. To confirm before redistribution.",
                "attribution": "Prozorro, Ministry of Economy of Ukraine / State enterprise Prozorro",
                "cohort": {"cohortId": COHORT, "buyers": BUYERS, "window": manifest["window"],
                           "selection": "One buyer per level, announced on 2026-09-25 before any tender record was downloaded; chosen by level and a reviewable tender count, outside occupied or front-line oblasts; never by indicator results."},
                "retrieval": {"startedAt": manifest["retrievalStartedAt"], "finishedAt": manifest.get("retrievalFinishedAt"),
                              "buyers": [{k: b[k] for k in ("code", "searchUrl", "searchTotal", "listedTenderIDs")} | {"inWindowByTenderID": len(b["tenderIDs"])} for b in manifest["buyers"]],
                              "rawDirectory": "data/prozorro/raw"},
                "counts": {"tendersInWindow": sum(kinds.values()), "tendersOutsideWindowByDateCreated": outside, "tendersWithAnotherBuyer": other_buyer,
                           "procedureTypes": dict(sorted(kinds.items(), key=lambda kv: -kv[1])), "retainedContracts": len(rows),
                           "excludedContracts": excluded, "withOffers": sum(r["offers"] is not None for r in rows),
                           "currencies": sorted({r["currency"] for r in rows if r["currency"]})},
                "limitations": ["Three buyers, not a country sample; wartime rules allow exceptions and withheld publications.",
                                "Direct-contract reports (reporting) are recorded without a procedure; they are not scored.",
                                "Contract changes live in the separate contracting API and were not imported.",
                                "Amounts are in the published currency, never converted or summed across currencies."],
                "reproduce": ["python tools/import-prozorro.py --offline", "python tools/import-prozorro.py --download"]}
    COVERAGE.write_text(json.dumps(coverage, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(coverage["counts"], ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    if args.download:
        download()
    if args.offline or args.download:
        offline()
