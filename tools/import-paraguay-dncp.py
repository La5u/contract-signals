#!/usr/bin/env python3
"""Bounded DNCP/OCDS cohorts for Paraguay, each announced before download.

Cohorts (never merged; each has its own raw directory, extract and coverage file):
  fernando  Municipalidad de Fernando de la Mora, calls published 2024-09-01..2025-08-31 (first pilot)
  3buyers   MOPC (national), Gobierno Departamental de Central (departmental),
            Municipalidad de Asunción (municipal); calls published 2024-09-01..2026-08-31

--download saves search pages and every full OCID record; resume is safe for records
already saved (a new search snapshot requires clearing the raw directory first).
--offline reproduces the static contract extract exclusively from saved responses.
No score, payment check, or completeness claim for actual procurement is inferred.
"""
import argparse
from datetime import date, datetime, timedelta, timezone
import gzip
import json
from pathlib import Path
import time
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://www.contrataciones.gov.py/datos/api/v3/doc"
PAGE_SIZE = 50
LICENSE = "https://creativecommons.org/licenses/by/4.0/"
PORTAL = "https://www.contrataciones.gov.py/licitaciones/"

# Buyers and windows are fixed here before any contract record is downloaded.
# Selection uses government level and a manually reviewable process count only,
# never indicator results.
COHORTS = {
    "fernando": {
        "cohortId": "dncp-fernando-2024-2025",
        "raw": ROOT / "data/paraguay-dncp/raw",
        "extract": ROOT / "data/paraguay-dncp.json",
        "coverage": ROOT / "data/paraguay-dncp-coverage.json",
        "buyers": [{"code": "66", "name": "Municipalidad de Fernando de la Mora", "level": "municipal"}],
        "start": "2024-09-01", "end": "2025-09-01",
        "selection": "One municipality, selected before downloading contract records; date filter on call publication, not on award/signature or score.",
    },
    "3buyers": {
        "cohortId": "dncp-3buyers-2024-2026",
        "raw": ROOT / "data/paraguay-dncp-3buyers/raw",
        "extract": ROOT / "data/paraguay-dncp-3buyers.json",
        "coverage": ROOT / "data/paraguay-dncp-3buyers-coverage.json",
        "buyers": [
            {"code": "20", "name": "Ministerio de Obras Públicas y Comunicaciones (MOPC)", "level": "national"},
            {"code": "81", "name": "Gobierno Departamental de Central", "level": "departmental"},
            {"code": "108", "name": "Municipalidad de Asunción", "level": "municipal"},
        ],
        "start": "2024-09-01", "end": "2026-09-01",
        "gzipRecords": True,  # MOPC works records list thousands of items; gzip keeps the exact response bytes
        "selection": "One buyer per government level (national, departmental, municipal), announced on 2026-09-25 before downloading contract records. Chosen by level and a manually reviewable process count (search totals 149, 95 and 97 at announcement); the Ministerio de Educación y Ciencias (3,517 processes) was set aside for volume. Indicator results were not consulted.",
    },
}
BUYER = "DNCP-SICP-CODE-66"  # first pilot; kept for the pilot's tests and manifest


def buyer_id(code):
    return "DNCP-SICP-CODE-" + code


def search_url(page, code="66", start="2024-09-01", end="2025-09-01"):
    last = (date.fromisoformat(end) - timedelta(days=1)).isoformat()  # source end date is inclusive
    return BASE + "/search/processes?" + urlencode({
        "page": page, "items_per_page": PAGE_SIZE, "parties.identifier.id": code,
        "fecha_desde": start, "fecha_hasta": last, "tipo_fecha": "publicacion_llamado",
    })


def record_url(ocid):
    return BASE + "/ocds/record/" + quote(ocid, safe="")


def get_json(url):
    for attempt in range(5):
        try:
            with urlopen(Request(url, headers={"User-Agent": "contract-signals/0.1 (public research; offline snapshot)"}), timeout=60) as response:
                return json.load(response)
        except Exception:
            if attempt == 4:
                raise
            time.sleep(2 ** attempt)


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def record_path(cohort, ocid):
    return cohort["raw"] / "records" / (ocid + (".json.gz" if cohort.get("gzipRecords") else ".json"))


def save_record(cohort, ocid, package):
    path = record_path(cohort, ocid)
    if not cohort.get("gzipRecords"):
        return save(path, package)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(package, ensure_ascii=False, indent=1) + "\n").encode("utf-8")
    path.write_bytes(gzip.compress(data, mtime=0))  # mtime=0: identical input gives identical bytes


def load_record(cohort, ocid):
    path = record_path(cohort, ocid)
    return json.loads(gzip.decompress(path.read_bytes()) if cohort.get("gzipRecords") else path.read_text(encoding="utf-8"))


def check_package(package):
    if package.get("version") != "1.1" or package.get("license") != LICENSE or not package.get("records"):
        raise ValueError("Unexpected OCDS version, license or empty package")


def manifest_queries(manifest):
    """The first pilot's manifest describes one query at top level; later ones list queries."""
    if "queries" in manifest:
        return manifest["queries"]
    return [{"buyerId": manifest["buyerId"], "queryUrl": manifest["queryUrl"], "searchTotal": manifest["searchTotal"],
             "totalPages": manifest["totalPages"], "searchPages": manifest["searchPages"]}]


def page_file(cohort, code, page):
    return f"search-{page:03}.json" if cohort["cohortId"] == COHORTS["fernando"]["cohortId"] else f"search-{code}-{page:03}.json"


def download(cohort):
    raw = cohort["raw"]
    manifest_path = raw / "manifest.json"
    if manifest_path.exists():
        manifest = load(manifest_path)
        expected = [search_url(1, b["code"], cohort["start"], cohort["end"]) for b in cohort["buyers"]]
        if [q["queryUrl"] for q in manifest_queries(manifest)] != expected:
            raise ValueError("Existing raw snapshot has a different query; do not merge cohorts")
    else:
        queries = []
        for b in cohort["buyers"]:
            first = get_json(search_url(1, b["code"], cohort["start"], cohort["end"]))
            check_package(first)
            total, count = first["pagination"]["total_items"], first["pagination"]["total_pages"]
            if total >= 10000:
                raise ValueError("Search total at the API cap; completeness cannot be checked")
            pages = [{"file": page_file(cohort, b["code"], p), "url": search_url(p, b["code"], cohort["start"], cohort["end"])} for p in range(1, count + 1)]
            save(raw / pages[0]["file"], first)
            queries.append({"buyerId": buyer_id(b["code"]), "queryUrl": pages[0]["url"], "searchTotal": total, "totalPages": count, "searchPages": pages})
        manifest = {"cohortId": cohort["cohortId"],
                    "window": {"startInclusive": cohort["start"], "endExclusive": cohort["end"],
                               "basis": "tipo_fecha=publicacion_llamado (call publication, NOT contract signature)"},
                    "queries": queries, "retrievalStartedAt": datetime.now(timezone.utc).isoformat(),
                    "recordUrlTemplate": BASE + "/ocds/record/{ocid}"}
        save(manifest_path, manifest)
    ocids = []
    for query in manifest_queries(manifest):
        found = []
        for page in query["searchPages"]:
            path = raw / page["file"]
            if not path.exists():
                save(path, get_json(page["url"]))
            response = load(path)
            check_package(response)
            pagination = response["pagination"]
            if pagination["total_items"] != query["searchTotal"] or pagination["total_pages"] != query["totalPages"] or pagination["total_in_page"] != len(response["records"]):
                raise ValueError("Search pagination changed mid-download; discard snapshot")
            found.extend(record["ocid"] for record in response["records"])
        if len(found) != query["searchTotal"] or len(set(found)) != len(found):
            raise ValueError("Search pagination incomplete or overlapping; discard snapshot")
        ocids.extend(o for o in found if o not in ocids)
    for i, ocid in enumerate(ocids, 1):
        if not record_path(cohort, ocid).exists():
            package = get_json(record_url(ocid))
            check_package(package)
            if len(package["records"]) != 1 or package["records"][0]["ocid"] != ocid:
                raise ValueError("Full record OCID mismatch: " + ocid)
            save_record(cohort, ocid, package)
        if i % 20 == 0:
            print(f"saved {i}/{len(ocids)} records", flush=True)
    manifest["retrievalFinishedAt"] = datetime.now(timezone.utc).isoformat()
    save(manifest_path, manifest)
    offline(cohort)


def portal_urls(documents, title):
    """Human-readable portal pages exactly as the source lists them; never constructed."""
    return [d["url"] for d in documents or [] if d.get("title") == title and str(d.get("url", "")).startswith(PORTAL)]


# Award attachments a reviewer needs to check competition per lot; URLs as published.
AWARD_DOCUMENTS = {"Cuadro Comparativo de Ofertas": "bidComparison", "Informe de Evaluación": "evaluationReport",
                   "Resolución de Adjudicación": "awardResolution"}


def award_documents(award):
    docs, seen = [], set()
    for d in award.get("documents") or []:
        kind = AWARD_DOCUMENTS.get(d.get("documentTypeDetails"))
        url = str(d.get("url", ""))
        if kind and url.startswith("https://www.contrataciones.gov.py/") and url not in seen:
            seen.add(url)
            docs.append({"kind": kind, "title": d.get("title"), "date": (d.get("datePublished") or "")[:10] or None, "url": url})
    return docs


def complaint_summaries(release):
    """Process-level complaints before the DNCP, as procedural context only.

    Participants' names (judges, clerks, complainants) are deliberately not kept.
    The outcome is in the linked resolutions; it is never inferred here."""
    out = []
    for complaint in release.get("complaints") or []:
        events = complaint.get("events") or []
        types = {e.get("type") for e in events}
        text = " ".join(str(e.get("description") or "") for e in events).lower()
        denunciation = any(str(i.get("name", "")).startswith("Denunciante") for i in complaint.get("intervenients") or [])
        kind = "protest" if types & {"Escrito de Protesta", "Presentación de protestante"} else \
            "investigation" if denunciation or "investigaci" in text else "other"
        dates = sorted(d for e in events for d in [((e.get("period") or {}).get("startDate") or "")[:10]] if d)
        out.append({"id": complaint.get("id"), "kind": kind, "eventCount": len(events),
                    "firstEventDate": dates[0] if dates else None, "lastEventDate": dates[-1] if dates else None,
                    "closureRecorded": "Resolución de Cierre" in types,
                    "documents": [{"title": d.get("title"), "date": (d.get("datePublished") or "")[:10] or None, "url": d["url"]}
                                  for d in complaint.get("documents") or [] if str(d.get("url", "")).startswith("https://www.contrataciones.gov.py/")]})
    return out


# Only a debarment bars a supplier from contracting; warnings and fines do not.
BARRING_SANCTIONS = {"INHABILITACION"}
SANCTIONS = ROOT / "data/dncp-sanctions.json"  # minimised snapshot, tools/fetch-dncp-sanctions.py


def sanctions_in_force(row, snapshot):
    """Debarments whose period covers the award date; context only, never points."""
    supplier = {s["id"]: s for s in snapshot["suppliers"]}.get(row["supplierIds"][0]["id"]) if snapshot and row["supplierIds"] else None
    day = row.get("awardDate")
    return [s | {"retrievedAt": snapshot["retrievedAt"][:10]} for s in (supplier or {}).get("sanctions", [])
            if s["type"] in BARRING_SANCTIONS and day and s["start"] and s["start"] <= day and (s["end"] is None or day <= s["end"])]


def supplier_identifier(supplier_id):
    return {"identifierType": "RUC" if supplier_id.startswith("PY-RUC-") else "OCDS party ID", "id": supplier_id}


def contract_rows(record, buyers=(BUYER,), cohort_id="dncp-fernando-2024-2025"):
    """Only explicit contract->award links; never interpret search hits as contracts."""
    release = record.get("compiledRelease") or {}
    ocid = record["ocid"]
    buyer = release.get("buyer") or {}
    if buyer.get("id") not in buyers:
        raise ValueError("Buyer mismatch: " + ocid)
    tender = release.get("tender") or {}
    awards = {a["id"]: a for a in release.get("awards", []) if a.get("id")}
    tenderers = tender.get("tenderers")
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
        amendments = [{"id": a.get("id"), "date": (a.get("date") or "")[:10] or None, "description": a.get("description"),
                       "amount": (a.get("amendsAmount") or {}).get("amount"), "currency": (a.get("amendsAmount") or {}).get("currency"),
                       "entryId": a.get("financialCode")} for a in contract.get("amendments") or []]
        supplier = suppliers[0]
        rows.append({
            "id": f"dncp-{ocid}-{contract['id']}", "cohortId": cohort_id, "dataFamily": "dncp",
            "dataStatus": "verified", "buyer": buyer.get("name") or buyer["id"], "buyerId": buyer["id"],
            "supplier": supplier.get("name"), "supplierIds": [supplier_identifier(supplier["id"])],
            "description": tender.get("title") or contract["id"], "procedure": tender.get("procurementMethodDetails"),
            "procurementMethod": tender.get("procurementMethod"),
            "procurementMethodRationale": tender.get("procurementMethodRationale"),
            "category": tender.get("mainProcurementCategory"),
            "numberOfTenderers": tender.get("numberOfTenderers") if isinstance(tender.get("numberOfTenderers"), int) else None,
            "tenderersListed": len(tenderers) if isinstance(tenderers, list) else None,
            "lotCount": len(tender.get("lots") or []),
            "tenderPeriodDays": (tender.get("tenderPeriod") or {}).get("durationInDays"),
            "contractId": contract["id"], "awardId": award["id"], "ocid": ocid,
            "date": ((contract.get("period") or {}).get("startDate") or "")[:10] or None,
            "dateNote": "OCDS contract.period.startDate; dateSigned not supplied. Not proof of signature.",
            "signatureDate": (contract.get("dateSigned") or "")[:10] or None,
            "callPublishedDate": (tender.get("datePublished") or "")[:10] or None,
            "awardDate": (award.get("date") or "")[:10] or None,
            "contractStatus": contract.get("status"), "amount": value["amount"], "currency": "PYG",
            "amendmentCount": len(amendments), "amendments": amendments, "releaseCount": len(record.get("releases") or []),
            "signedDocumentUrls": documents, "awardDocuments": award_documents(award), "complaints": complaint_summaries(release),
            "callUrl": (portal_urls(tender.get("documents"), "URL de la Convocatoria") or [None])[0],
            "awardUrl": (portal_urls(award.get("documents"), "URL de la Adjudicación") or [None])[0],
            "source": record_url(ocid), "sourceLabel": "DNCP OCDS 1.1 — full record (JSON)",
            "notes": "Published OCDS contract linked by awardID; amount is declared, not an audited payment.",
        })
    return rows


def offline(cohort):
    raw = cohort["raw"]
    manifest = load(raw / "manifest.json")
    queries = manifest_queries(manifest)
    buyers = tuple(buyer_id(b["code"]) for b in cohort["buyers"])
    if [q["buyerId"] for q in queries] != list(buyers) or [q["queryUrl"] for q in queries] != [search_url(1, b["code"], cohort["start"], cohort["end"]) for b in cohort["buyers"]]:
        raise ValueError("Raw manifest does not describe the announced cohort")
    ocids, per_query = [], []
    for query in queries:
        found = []
        for page in query["searchPages"]:
            response = load(raw / page["file"])
            check_package(response)
            if response["pagination"]["total_items"] != query["searchTotal"]:
                raise ValueError("Search total drift")
            found.extend(record["ocid"] for record in response["records"])
        if len(found) != query["searchTotal"] or len(set(found)) != len(found):
            raise ValueError("Search results incomplete or duplicated")
        per_query.append({"buyerId": query["buyerId"], "searchProcesses": len(found)})
        ocids.extend(o for o in found if o not in ocids)
    rows, records_with_contracts, total_contracts, releases, amendment_events, other_buyer = [], 0, 0, 0, 0, []
    amendment_entry_ids, budget_only = set(), 0
    for ocid in ocids:
        package = load_record(cohort, ocid)
        check_package(package)
        if len(package["records"]) != 1 or package["records"][0]["ocid"] != ocid:
            raise ValueError("Missing or mismatched full record: " + ocid)
        record = package["records"][0]
        compiled = record.get("compiledRelease") or {}
        if (compiled.get("buyer") or {}).get("id") not in buyers:
            other_buyer.append(ocid)  # no single cohort buyer (e.g. a multi-buyer second-stage purchase)
            continue
        contracts = compiled.get("contracts") or []
        total_contracts += len(contracts)
        releases += len(record.get("releases") or [])
        amendment_events += sum(len(c.get("amendments") or []) for c in contracts)
        budget_only += sum(1 for c in contracts if not c.get("id") and set(c) <= {"implementation"})
        amendment_entry_ids.update(a.get("financialCode") for c in contracts for a in c.get("amendments") or [] if a.get("financialCode"))
        matched = contract_rows(record, buyers, cohort["cohortId"])
        if any(not row["callPublishedDate"] or not cohort["start"] <= row["callPublishedDate"] < cohort["end"] for row in matched):
            raise ValueError("Compiled call publication outside fixed search window: " + ocid)
        records_with_contracts += bool(matched)
        rows.extend(matched)
    ids = [row["id"] for row in rows]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate contract IDs; refusing to write")
    rows.sort(key=lambda r: (r["callPublishedDate"] or "", r["id"]))
    snapshot = load(SANCTIONS) if SANCTIONS.exists() else None
    for row in rows:
        row["sanctionsInForceAtAward"] = sanctions_in_force(row, snapshot)
    save(cohort["extract"], rows)
    names = {buyer_id(b["code"]): b for b in cohort["buyers"]}
    single = len(cohort["buyers"]) == 1
    coverage = {"source": BASE, "portal": PORTAL, "license": "CC BY 4.0", "licenseUrl": LICENSE,
                "attribution": "Dirección Nacional de Contrataciones Públicas (DNCP), Paraguay",
                "cohort": ({"buyer": cohort["buyers"][0]["name"], "buyerId": buyers[0]} if single else
                           {"buyers": [{"buyerId": k, "name": v["name"], "level": v["level"]} for k, v in names.items()]}) |
                          {"cohortId": cohort["cohortId"], "selection": cohort["selection"], "window": manifest["window"]},
                "retrieval": {"startedAt": manifest["retrievalStartedAt"], "finishedAt": manifest["retrievalFinishedAt"],
                              **({"queryUrl": queries[0]["queryUrl"], "pages": queries[0]["searchPages"], "totalItemsAtDownload": queries[0]["searchTotal"]} if single else
                                 {"queries": [{"buyerId": q["buyerId"], "queryUrl": q["queryUrl"], "totalItemsAtDownload": q["searchTotal"], "pages": q["searchPages"]} for q in queries]}),
                              "recordUrlTemplate": manifest["recordUrlTemplate"], "rawDirectory": str(raw.relative_to(ROOT))},
                "counts": {"searchProcesses": len(ocids), **({} if single else {"searchProcessesByBuyer": per_query, "processesWithoutSingleCohortBuyer": len(other_buyer), "processesWithoutSingleCohortBuyerOcids": other_buyer}),
                           "recordsWithEligibleContracts": records_with_contracts,
                           "publishedContractsInFullRecords": total_contracts, "retainedContracts": len(rows),
                           "excludedContractEntries": total_contracts - len(rows),
                           "excludedBudgetOnlyEntries": budget_only,
                           "excludedEntriesThatAreAmendmentRecords": sum(1 for c in amendment_entry_ids if c not in {r["contractId"] for r in rows}),
                           "releasesInFullRecords": releases,
                           "publishedContractAmendmentEntries": amendment_events,
                           "retainedWithSignedDocumentUrl": sum(bool(r["signedDocumentUrls"]) for r in rows),
                           "retainedWithoutSignatureDate": sum(not r["signatureDate"] for r in rows),
                           "retainedWithPortalAwardPage": sum(bool(r["awardUrl"]) for r in rows),
                           "retainedWithTendererCount": sum(r["numberOfTenderers"] is not None for r in rows),
                           "retainedWithComplaintRecorded": sum(bool(r["complaints"]) for r in rows)},
                "limitations": ["Calls published during the fixed window, not contracts signed during that window; later awards/contracts may appear in full records.",
                                "Search pagination is checked against one observed total but the API does not promise an immutable snapshot; national completeness is unverified. The search API caps totals at 10,000, so only bounded per-buyer queries are used.",
                                "Only contracts with explicit awardID, one identified award supplier, and PYG contract value are retained; excluded counts are reported. Budget-only entries (no contract ID, only implementation.financialProgress) are not contracts. Excluded entries also include the separate contract entries the source publishes for amount amendments; the amendment itself stays attached to its parent contract.",
                                "The source's contractSigned document links are not a manual review of document contents; signatures, legal status and payments are not independently audited.",
                                "Amendment and release counts are context, not a reconstructed value history; source versions can be incomplete.",
                                "Paraguayan checks are editorial (docs/score-paraguay.md); French and Colombian rules are never applied.",
                                "A few buyers are not a country sample; no cross-country score or currency comparison."],
                "reproduce": [f"python tools/import-paraguay-dncp.py --cohort {key} --download" for key, c in COHORTS.items() if c is cohort] +
                             [f"python tools/import-paraguay-dncp.py --cohort {key} --offline" for key, c in COHORTS.items() if c is cohort] +
                             ["node tests/paraguay.cjs"]}
    save(cohort["coverage"], coverage)
    print(json.dumps(coverage["counts"], indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cohort", choices=sorted(COHORTS), default="fernando")
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    if args.download:
        download(COHORTS[args.cohort])
    elif args.offline:
        offline(COHORTS[args.cohort])
    else:
        parser.error("choose --download or --offline")
