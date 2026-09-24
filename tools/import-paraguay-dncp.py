#!/usr/bin/env python3
"""Bounded DNCP/OCDS pilot: Fernando de la Mora, calls published 2024-09-01..2025-08-31.

--download saves search pages and every full OCID record; resume is safe for records
already saved (a new search snapshot requires clearing the raw directory first).
--offline reproduces the static contract extract exclusively from saved responses.
No score, payment check, or completeness claim for actual procurement is inferred.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import time
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/paraguay-dncp/raw"
BASE = "https://www.contrataciones.gov.py/datos/api/v3/doc"
BUYER = "DNCP-SICP-CODE-66"  # Municipalidad de Fernando de la Mora; fixed before download
START, END = "2024-09-01", "2025-09-01"  # end exclusive; source end date inclusive
PAGE_SIZE = 50
LICENSE = "https://creativecommons.org/licenses/by/4.0/"


def search_url(page):
    return BASE + "/search/processes?" + urlencode({
        "page": page, "items_per_page": PAGE_SIZE, "parties.identifier.id": "66",
        "fecha_desde": START, "fecha_hasta": "2025-08-31", "tipo_fecha": "publicacion_llamado",
    })


def record_url(ocid):
    return BASE + "/ocds/record/" + quote(ocid, safe="")


def get_json(url):
    for attempt in range(4):
        try:
            with urlopen(Request(url, headers={"User-Agent": "contract-signals/0.1 (public research; offline snapshot)"}), timeout=40) as response:
                return json.load(response)
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def check_package(package):
    if package.get("version") != "1.1" or package.get("license") != LICENSE or not package.get("records"):
        raise ValueError("Unexpected OCDS version, license or empty package")


def download():
    manifest_path = RAW / "manifest.json"
    if manifest_path.exists():
        manifest = load(manifest_path)
        if manifest["queryUrl"] != search_url(1):
            raise ValueError("Existing raw snapshot has a different query; do not merge cohorts")
    else:
        first = get_json(search_url(1))
        check_package(first)
        total = first["pagination"]["total_items"]
        count = first["pagination"]["total_pages"]
        manifest = {"buyerId": BUYER, "window": {"startInclusive": START, "endExclusive": END,
                    "basis": "tipo_fecha=publicacion_llamado (call publication, NOT contract signature)"},
                    "queryUrl": search_url(1), "searchTotal": total, "totalPages": count,
                    "retrievalStartedAt": datetime.now(timezone.utc).isoformat(),
                    "searchPages": [{"file": f"search-{page:03}.json", "url": search_url(page)} for page in range(1, count + 1)],
                    "recordUrlTemplate": BASE + "/ocds/record/{ocid}"}
        save(RAW / "search-001.json", first)
        save(manifest_path, manifest)
    ocids = []
    for page in manifest["searchPages"]:
        path = RAW / page["file"]
        if not path.exists():
            save(path, get_json(page["url"]))
        response = load(path)
        check_package(response)
        pagination = response["pagination"]
        if pagination["total_items"] != manifest["searchTotal"] or pagination["total_pages"] != manifest["totalPages"] or pagination["total_in_page"] != len(response["records"]):
            raise ValueError("Search pagination changed mid-download; discard snapshot")
        ocids.extend(record["ocid"] for record in response["records"])
    if len(ocids) != manifest["searchTotal"] or len(set(ocids)) != len(ocids):
        raise ValueError("Search pagination incomplete or overlapping; discard snapshot")
    for i, ocid in enumerate(ocids, 1):
        path = RAW / "records" / (ocid + ".json")
        if not path.exists():
            package = get_json(record_url(ocid))
            check_package(package)
            if len(package["records"]) != 1 or package["records"][0]["ocid"] != ocid:
                raise ValueError("Full record OCID mismatch: " + ocid)
            save(path, package)
        if i % 20 == 0:
            print(f"saved {i}/{len(ocids)} records", flush=True)
    manifest["retrievalFinishedAt"] = datetime.now(timezone.utc).isoformat()
    save(manifest_path, manifest)
    offline()


def contract_rows(record):
    """Only explicit contract->award links; never interpret search hits as contracts."""
    release = record.get("compiledRelease") or {}
    ocid = record["ocid"]
    buyer = release.get("buyer") or {}
    if buyer.get("id") != BUYER:
        raise ValueError("Buyer mismatch: " + ocid)
    tender = release.get("tender") or {}
    awards = {a["id"]: a for a in release.get("awards", []) if a.get("id")}
    rows = []
    for contract in release.get("contracts", []):
        award = awards.get(contract.get("awardID"))
        if not contract.get("id") or not award:
            continue  # unresolved association: report as excluded, never infer by name
        suppliers = award.get("suppliers") or []
        if len(suppliers) != 1 or not suppliers[0].get("id"):
            continue  # no single-holder identity; do not manufacture one
        value = contract.get("value") or {}
        if value.get("currency") != "PYG" or not isinstance(value.get("amount"), (int, float)):
            continue
        documents = [d.get("url") for d in contract.get("documents", []) if d.get("documentType") == "contractSigned" and str(d.get("url", "")).startswith("https://")]
        supplier = suppliers[0]
        rows.append({
            "id": f"dncp-{ocid}-{contract['id']}", "cohortId": "dncp-fernando-2024-2025", "dataFamily": "dncp",
            "dataStatus": "verified", "buyer": buyer.get("name") or "Municipalidad de Fernando de la Mora", "buyerId": BUYER,
            "supplier": supplier.get("name"), "supplierIds": [{"identifierType": "OCDS party ID", "id": supplier["id"]}],
            "description": tender.get("title") or contract["id"], "procedure": tender.get("procurementMethodDetails"),
            "contractId": contract["id"], "awardId": award["id"], "ocid": ocid,
            "date": ((contract.get("period") or {}).get("startDate") or "")[:10] or None,
            "dateNote": "OCDS contract.period.startDate; dateSigned not supplied. Not proof of signature.",
            "signatureDate": (contract.get("dateSigned") or "")[:10] or None,
            "callPublishedDate": (tender.get("datePublished") or "")[:10] or None,
            "contractStatus": contract.get("status"), "amount": value["amount"], "currency": "PYG",
            "amendmentCount": len(contract.get("amendments") or []), "releaseCount": len(record.get("releases") or []),
            "signedDocumentUrls": documents,
            "source": record_url(ocid), "sourceLabel": "DNCP OCDS 1.1 — full record",
            "notes": "Published OCDS contract linked by awardID; amount is declared, not an audited payment. No Paraguayan scoring rules approved.",
        })
    return rows


def offline():
    manifest = load(RAW / "manifest.json")
    if manifest["buyerId"] != BUYER or manifest["queryUrl"] != search_url(1):
        raise ValueError("Raw manifest does not describe the announced cohort")
    ocids = []
    for page in manifest["searchPages"]:
        response = load(RAW / page["file"])
        check_package(response)
        if response["pagination"]["total_items"] != manifest["searchTotal"]:
            raise ValueError("Search total drift")
        ocids.extend(record["ocid"] for record in response["records"])
    if len(ocids) != manifest["searchTotal"] or len(set(ocids)) != len(ocids):
        raise ValueError("Search results incomplete or duplicated")
    rows, records_with_contracts, total_contracts, releases, amendment_events = [], 0, 0, 0, 0
    for ocid in ocids:
        package = load(RAW / "records" / (ocid + ".json"))
        check_package(package)
        if len(package["records"]) != 1 or package["records"][0]["ocid"] != ocid:
            raise ValueError("Missing or mismatched full record: " + ocid)
        record = package["records"][0]
        compiled = record.get("compiledRelease") or {}
        contracts = compiled.get("contracts") or []
        total_contracts += len(contracts)
        releases += len(record.get("releases") or [])
        amendment_events += sum(len(c.get("amendments") or []) for c in contracts)
        matched = contract_rows(record)
        if any(not row["callPublishedDate"] or not START <= row["callPublishedDate"] < END for row in matched):
            raise ValueError("Compiled call publication outside fixed search window: " + ocid)
        records_with_contracts += bool(matched)
        rows.extend(matched)
    ids = [row["id"] for row in rows]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate contract IDs; refusing to write")
    rows.sort(key=lambda r: (r["callPublishedDate"] or "", r["id"]))
    save(ROOT / "data/paraguay-dncp.json", rows)
    coverage = {"source": BASE, "license": "CC BY 4.0", "licenseUrl": LICENSE,
                "attribution": "Dirección Nacional de Contrataciones Públicas (DNCP), Paraguay",
                "cohort": {"buyer": "Municipalidad de Fernando de la Mora", "buyerId": BUYER,
                           "selection": "One municipality, selected before downloading contract records; date filter on call publication, not on award/signature or score.",
                           "window": manifest["window"]},
                "retrieval": {"startedAt": manifest["retrievalStartedAt"], "finishedAt": manifest["retrievalFinishedAt"], "queryUrl": manifest["queryUrl"],
                              "pages": manifest["searchPages"], "totalItemsAtDownload": manifest["searchTotal"],
                              "recordUrlTemplate": manifest["recordUrlTemplate"], "rawDirectory": "data/paraguay-dncp/raw"},
                "counts": {"searchProcesses": len(ocids), "recordsWithEligibleContracts": records_with_contracts,
                           "publishedContractsInFullRecords": total_contracts, "retainedContracts": len(rows),
                           "excludedContractEntries": total_contracts - len(rows), "releasesInFullRecords": releases,
                           "publishedContractAmendmentEntries": amendment_events,
                           "retainedWithSignedDocumentUrl": sum(bool(r["signedDocumentUrls"]) for r in rows),
                           "retainedWithoutSignatureDate": sum(not r["signatureDate"] for r in rows)},
                "limitations": ["Calls published during the fixed window, not contracts signed during that window; later awards/contracts may appear in full records.",
                                "Search pagination is checked against one observed total but the API does not promise an immutable snapshot; national completeness is unverified.",
                                "Only contracts with explicit awardID, one identified award supplier, and PYG contract value are retained; excluded counts are reported.",
                                "The source's contractSigned document links are not a manual review of document contents; signatures, legal status and payments are not independently audited.",
                                "Amendment and release counts are context, not a reconstructed value history; source versions can be incomplete.",
                                "No Paraguayan vigilance rules approved: every retained row is Not assessed, never scored with French or Colombian rules.",
                                "A single municipality is not a country sample; no cross-country score or currency comparison."],
                "reproduce": ["python tools/import-paraguay-dncp.py --download", "python tools/import-paraguay-dncp.py --offline", "node tests/paraguay.cjs"]}
    save(ROOT / "data/paraguay-dncp-coverage.json", coverage)
    print(json.dumps(coverage["counts"], indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    if args.download:
        download()
    elif args.offline:
        offline()
    else:
        parser.error("choose --download or --offline")
