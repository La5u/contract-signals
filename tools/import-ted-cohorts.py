#!/usr/bin/env python3
"""Portugal, Romania and Czechia from TED: award notices (eForms) of three announced buyers each.

  --cohort portugal|romania|czechia --download   search TED (API v3, anonymous) for the buyers'
                                         can-standard notices, save each official XML gzipped
  --cohort portugal|romania|czechia --offline    rebuild data/ted-<cohort>.json and its coverage file

TED covers procedures above the EU thresholds only: these cohorts are not a picture of
the countries' procurement. Buyers are matched by their published identifier and its
spelling variants, never by name. Reuse: TED notices "can be freely reused, for
commercial or non-commercial purposes" (Commission Decision 2011/833/EU).
"""
import argparse
import gzip
import hashlib
import importlib.util
import json
import re
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("boamp", ROOT / "tools/import-boamp-sample.py")
boamp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(boamp)
as_list, text, path, ids = boamp.as_list, boamp.text, boamp.path, boamp.ids

SEARCH = "https://api.ted.europa.eu/v3/notices/search"
XML = "https://ted.europa.eu/en/notice/{pub}/xml"
PAGE = "https://ted.europa.eu/en/notice/-/detail/{pub}"
START, END = "20240901", "20260901"
LICENSE = "TED notices may be freely reused, for commercial or non-commercial purposes (Commission Decision 2011/833/EU; https://ted.europa.eu/en/legal-notice)."
# Announced on 2026-09-25 before any notice XML was downloaded: one buyer per level,
# chosen by level and a reviewable notice count (TED search totals in brackets).
COHORTS = {
    "portugal": {"country": "PRT", "prefix": "PT", "idType": "NIF", "cohortId": "ted-portugal-2024-2026", "buyers": [
        {"id": "503933813", "name": "Infraestruturas de Portugal, S. A.", "level": "national"},        # 371
        {"id": "508779472", "name": "Comunidade Intermunicipal do Cávado", "level": "regional"},     # 36
        {"id": "500051070", "name": "Município de Lisboa", "level": "municipal"},                    # 35
    ]},
    "romania": {"country": "ROU", "prefix": "RO", "idType": "CUI", "cohortId": "ted-romania-2024-2026", "buyers": [
        {"id": "4221306", "name": "Ministerul Finanțelor", "level": "national"},                     # 119; CNAIR (1,450) set aside for volume
        {"id": "4288110", "name": "Județul Cluj (Consiliul Județean)", "level": "regional"},          # 91
        {"id": "4305857", "name": "Municipiul Cluj-Napoca", "level": "municipal"},                   # 89
    ]},
    # Announced on 2026-09-26 before any notice XML was downloaded, from TED search totals of a
    # candidate list (5 ministries, 5 regions, 5 cities): per level the largest at most 500.
    # Set aside for volume: Ministry of the Interior (2,048), Ministry of Defence (1,843);
    # Prague (493) is both a region and a municipality and was left out.
    "czechia": {"country": "CZE", "prefix": "CZ", "idType": "ICO", "cohortId": "ted-czechia-2024-2026",
                "selection": "One buyer per level, announced on 2026-09-26 before any notice XML was downloaded: from TED search totals of a candidate list (Ministries of the Interior, Defence, Health, Justice and Finance; the South Moravian, Moravian-Silesian, Vysočina, Olomouc and Plzeň regions; Brno, Ostrava, Plzeň, Olomouc and Prague), the largest at most 500 notices per level; Prague left out as both region and city. Never by indicator results.",
                "buyers": [
        {"id": "00006947", "name": "Ministerstvo financí", "level": "national"},                     # 257
        {"id": "70890692", "name": "Moravskoslezský kraj", "level": "regional"},                     # 195
        {"id": "00845451", "name": "Statutární město Ostrava", "level": "municipal"},                # 214
    ]},
}
# eForms procedure codes (EU directives). neg-wo-call = negotiated without prior publication.
PROCEDURES = {"open": ("Open procedure", False), "restricted": ("Restricted procedure", False),
              "comp-dial": ("Competitive dialogue", False), "neg-w-call": ("Negotiated with prior publication", False),
              "innovation": ("Innovation partnership", False), "comp-tend": ("Competitive tendering", False),
              "neg-wo-call": ("Negotiated without prior publication", True), "oth-single": ("Other single-stage procedure", None),
              "oth-mult": ("Other multiple-stage procedure", None)}


def variants(cohort, base):
    """Spellings of one identifier seen in TED: bare, country-prefixed, spaced."""
    p = cohort["prefix"]
    out = {base, p + base, f"{p} {base}", f"{p}-{base}"}
    if len(base) == 9:
        spaced = f"{base[:3]} {base[3:6]} {base[6:]}"
        out |= {spaced, f"{p} {spaced}"}
    return sorted(out)


def query_for(cohort, buyer):
    ids_ = " ".join(repr(v) for v in variants(cohort, buyer["id"]))
    return (f"buyer-country={cohort['country']} AND notice-type=can-standard AND publication-date>={START} "
            f"AND publication-date<{END} AND organisation-identifier-buyer IN ({ids_})")


def post(query, page):
    body = json.dumps({"query": query, "fields": ["publication-number", "publication-date", "organisation-identifier-buyer"],
                       "limit": 250, "page": page}).encode()
    for attempt in range(7):
        try:
            with urllib.request.urlopen(urllib.request.Request(SEARCH, data=body, headers={"Content-Type": "application/json"}), timeout=90) as r:
                return json.load(r)
        except Exception:
            if attempt == 6:
                raise
            time.sleep(2 ** attempt)


def fetch(url):
    for attempt in range(7):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "contract-signals/0.1"}), timeout=90) as r:
                data = r.read()
            if data:
                return data
            raise ValueError("empty body (HTTP 202 while TED prepares the XML)")
        except Exception:
            if attempt == 6:
                raise
            time.sleep(2 ** attempt)


def raw_dir(key):
    return ROOT / f"data/ted-{key}/raw"


def download(key):
    cohort, raw = COHORTS[key], raw_dir(key)
    manifest_path = raw / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        manifest = {"cohortId": cohort["cohortId"], "window": {"startInclusive": START, "endExclusive": END, "basis": "TED publication date"},
                    "retrievalStartedAt": datetime.now(timezone.utc).isoformat(), "buyers": []}
        for buyer in cohort["buyers"]:
            q = query_for(cohort, buyer)
            first = post(q, 1)
            notices, page = list(first["notices"]), 1
            while len(notices) < first["totalNoticeCount"]:
                page += 1
                notices += post(q, page)["notices"]
                time.sleep(0.5)
            pubs = [n["publication-number"] for n in notices]
            if len(pubs) != first["totalNoticeCount"] or len(set(pubs)) != len(pubs):
                raise RuntimeError("incomplete TED listing for " + buyer["id"])
            manifest["buyers"].append({"id": buyer["id"], "query": q, "searchTotal": first["totalNoticeCount"], "publicationNumbers": pubs})
            print(key, buyer["id"], len(pubs), "notices", flush=True)
            time.sleep(1)
        raw.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for buyer in manifest["buyers"]:
        for pub in buyer["publicationNumbers"]:
            out = raw / "notices" / f"{pub}.xml.gz"
            if not out.exists():
                data = fetch(XML.format(pub=pub))
                if b"ContractAwardNotice" not in data[:4000]:
                    raise RuntimeError("not an eForms award notice: " + pub)
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(gzip.compress(data, mtime=0))
                time.sleep(2)  # TED answers empty 202s (bot protection) to faster clients
    manifest["retrievalFinishedAt"] = datetime.now(timezone.utc).isoformat()
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


# ---- eForms XML to the XML-as-JSON shape used by the BOAMP parser ----
PREFIXES = {
    "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2": "cbc",
    "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2": "cac",
    "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2": "ext",
    "http://data.europa.eu/p27/eforms-ubl-extension-aggregate-components/1": "efac",
    "http://data.europa.eu/p27/eforms-ubl-extension-basic-components/1": "efbc",
    "http://data.europa.eu/p27/eforms-ubl-extensions/1": "efext",
}


def to_dict(element):
    def name(tag):
        if tag.startswith("{"):
            ns, local = tag[1:].split("}")
            return f"{PREFIXES[ns]}:{local}" if ns in PREFIXES else local
        return tag
    node = {f"@{name(k)}": v for k, v in element.attrib.items()}
    for child in element:
        key, value = name(child.tag), to_dict(child)
        if key in node:
            node[key] = node[key] if isinstance(node[key], list) else [node[key]]
            node[key].append(value)
        else:
            node[key] = value
    body = (element.text or "").strip()
    if not node:
        return body
    if body:
        node["#text"] = body
    return node


def notice_rows(cohort, pub, xml_bytes):
    notice = to_dict(ET.fromstring(xml_bytes))
    ext = notice["ext:UBLExtensions"]["ext:UBLExtension"]["ext:ExtensionContent"]["efext:EformsExtension"]
    ext = ext[0] if isinstance(ext, list) else ext
    result = ext.get("efac:NoticeResult") or {}
    orgs = {}
    for o in as_list((ext.get("efac:Organizations") or {}).get("efac:Organization")):
        company = o.get("efac:Company") or {}
        orgs[text(path(company, "cac:PartyIdentification", "cbc:ID"))] = {
            "name": text(path(company, "cac:PartyName", "cbc:Name")),
            "companyId": text(path(company, "cac:PartyLegalEntity", "cbc:CompanyID")),
            "country": text(path(company, "cac:PostalAddress", "cac:Country", "cbc:IdentificationCode"))}
    tenders = {text(path(t, "cbc:ID")): t for t in as_list(result.get("efac:LotTender"))}
    contracts = {text(path(c, "cbc:ID")): c for c in as_list(result.get("efac:SettledContract"))}
    parties = {text(path(p, "cbc:ID")): p for p in as_list(result.get("efac:TenderingParty"))}
    lots = {text(path(l, "cbc:ID")): l for l in as_list(notice.get("cac:ProcurementProjectLot"))}
    buyer_org = orgs.get(text(path(notice, "cac:ContractingParty", "cac:Party", "cac:PartyIdentification", "cbc:ID"))) or {}
    procedure_code = text(path(notice, "cac:TenderingProcess", "cbc:ProcedureCode"))
    label, direct = PROCEDURES.get(procedure_code, (procedure_code, None))
    title = text(path(notice, "cac:ProcurementProject", "cbc:Name"))
    issue = text(notice.get("cbc:IssueDate"))
    rows, excluded = [], []
    for res in as_list(result.get("efac:LotResult")):
        if text(path(res, "cbc:TenderResultCode")) != "selec-w":
            continue
        tender_ids, contract_ids = ids(res.get("efac:LotTender")), ids(res.get("efac:SettledContract"))
        lot_id, res_id = text(path(res, "efac:TenderLot", "cbc:ID")), text(path(res, "cbc:ID"))
        if len(tender_ids) != 1 or len(contract_ids) > 1 or not lot_id:
            excluded.append("several or no winning tender/contract references")
            continue
        tender = tenders.get(tender_ids[0]) or {}
        party = parties.get(text(path(tender, "efac:TenderingParty", "cbc:ID"))) or {}
        members = [orgs[t] | {"org": t} for t in ids(party.get("efac:Tenderer")) if t in orgs]
        if not members or not any(m["name"] for m in members):
            excluded.append("no identified holder")
            continue
        node = path(tender, "cac:LegalMonetaryTotal", "cbc:PayableAmount")
        amount, currency = None, None
        if isinstance(node, dict):
            try:
                value = float(node["#text"])
                if value >= 0:
                    amount, currency = (int(value) if value.is_integer() else value), node.get("@currencyID")
            except (KeyError, TypeError, ValueError):
                pass
        offers = None
        for stat in as_list(res.get("efac:ReceivedSubmissionsStatistics")):
            if text(path(stat, "efbc:StatisticsCode")) == "tenders" and str(stat.get("efbc:StatisticsNumeric", "")).isdigit():
                offers = int(stat["efbc:StatisticsNumeric"])
        contract = contracts.get(contract_ids[0]) if contract_ids else None
        lot = lots.get(lot_id) or {}
        project = path(lot, "cac:ProcurementProject") or {}
        duration_node = path(project, "cac:PlannedPeriod", "cbc:DurationMeasure")
        duration = None
        if isinstance(duration_node, dict) and duration_node.get("@unitCode") == "MONTH":
            try:
                duration = float(duration_node["#text"])
            except (KeyError, TypeError, ValueError):
                pass
        supplier_ids = []
        for m in members:
            cid = (m["companyId"] or "").strip()
            if not cid:
                continue
            digits = re.sub(r"^" + cohort["prefix"] + r"[\s-]?", "", re.sub(r"\s", "", cid), flags=re.I)
            national = m["country"] == cohort["country"] and digits.isdigit()
            supplier_ids.append({"id": digits if national else cid, "identifierType": cohort["idType"] if national else "published identifier"})
        buyer_id = re.sub(r"^" + cohort["prefix"] + r"[\s-]?", "", re.sub(r"\s", "", buyer_org.get("companyId") or ""), flags=re.I)
        rows.append({
            "id": f"ted-{pub}-{lot_id.lower()}", "cohortId": cohort["cohortId"], "dataFamily": "ted", "country": cohort["country"],
            "dataStatus": "verified", "date": (text(path(contract, "cbc:IssueDate")) or "")[:10] or None,
            "dateNote": "Contract conclusion date declared in the notice (SettledContract/IssueDate); not the publication date.",
            "buyer": buyer_org.get("name"), "buyerId": buyer_id or None,
            "supplier": " / ".join(m["name"] for m in members if m["name"]), "supplierIds": supplier_ids,
            "description": " — ".join(dict.fromkeys(x for x in [title, text(path(project, "cbc:Name"))] if x)) or pub,
            "amount": amount, "currency": currency, "procedure": label, "procedureCode": procedure_code, "procedureDirect": direct,
            "offers": offers, "durationMonths": duration,
            "cpv": text(path(project, "cac:MainCommodityClassification", "cbc:ItemClassificationCode")),
            "lotId": lot_id, "contractId": contract_ids[0] if contract_ids else None, "resultId": res_id,
            "noticeId": pub, "publicationDate": (issue or "")[:10] or None,
            "source": PAGE.format(pub=pub), "sourceLabel": f"TED notice {pub} (official page)", "xmlUrl": XML.format(pub=pub),
            "amountBasis": "Value of the winning tender (PayableAmount) in the currency published; not a notice total, a framework ceiling or a payment.",
            "notes": "TED eForms award notice. Offers = the 'tenders' statistic only. Above-EU-threshold procedures only.",
        })
    return rows, excluded


def offline(key):
    cohort, raw = COHORTS[key], raw_dir(key)
    manifest = json.loads((raw / "manifest.json").read_text(encoding="utf-8"))
    if [b["id"] for b in manifest["buyers"]] != [b["id"] for b in cohort["buyers"]] or \
            [b["query"] for b in manifest["buyers"]] != [query_for(cohort, b) for b in cohort["buyers"]]:
        raise ValueError("Raw manifest does not describe the announced cohort")
    seen, rows, excluded, other_buyer = set(), [], {}, []
    known = {b["id"] for b in cohort["buyers"]}
    for buyer in manifest["buyers"]:
        for pub in buyer["publicationNumbers"]:
            if pub in seen:
                continue
            seen.add(pub)
            got, why = notice_rows(cohort, pub, gzip.decompress((raw / "notices" / f"{pub}.xml.gz").read_bytes()))
            for r in why:
                excluded[r] = excluded.get(r, 0) + 1
            for r in got:
                if r["buyerId"] not in known:
                    other_buyer.append(r["id"])  # the lead buyer differs (joint procurement): not attributed to the cohort
                    continue
                rows.append(r)
    by_id = {}
    for r in rows:
        by_id.setdefault(r["id"], []).append(r)
    conflicting = sorted(k for k, v in by_id.items() if len({json.dumps(x, sort_keys=True) for x in v}) > 1)
    rows = [v[0] for k, v in by_id.items() if k not in conflicting]
    rows.sort(key=lambda r: (r["publicationDate"] or "", r["id"]))
    (ROOT / f"data/ted-{key}.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    coverage = {"source": SEARCH, "notices": "https://ted.europa.eu/en/notice/{publication-number}/xml", "license": LICENSE,
                "attribution": "Publications Office of the European Union, TED (Tenders Electronic Daily)",
                "cohort": {"cohortId": cohort["cohortId"], "country": cohort["country"],
                           "buyers": cohort["buyers"], "window": manifest["window"],
                           "selection": cohort.get("selection", "One buyer per level, announced on 2026-09-25 before any notice XML was downloaded; chosen by level and a reviewable TED notice count, never by indicator results."),
                           "identity": "Buyers matched by published identifier and its spelling variants (bare, country-prefixed, spaced), never by name."},
                "retrieval": {"startedAt": manifest["retrievalStartedAt"], "finishedAt": manifest.get("retrievalFinishedAt"),
                              "queries": [{"buyerId": b["id"], "query": b["query"], "searchTotal": b["searchTotal"]} for b in manifest["buyers"]],
                              "rawDirectory": f"data/ted-{key}/raw"},
                "counts": {"notices": len(seen), "retainedLots": len(rows), "excludedResults": excluded,
                           "lotsWithAnotherLeadBuyer": len(other_buyer), "conflictingLotIdsExcluded": len(conflicting),
                           "withOffers": sum(r["offers"] is not None for r in rows), "withAmount": sum(r["amount"] is not None for r in rows),
                           "currencies": sorted({r["currency"] for r in rows if r["currency"]})},
                "limitations": ["TED publishes procedures above the EU thresholds only; most national procurement is not here.",
                                "Contract modification notices are separate TED notices and were not imported: no amount-increase check.",
                                "Offers are the 'tenders' statistic published per lot; admissibility is not assessed.",
                                "Amounts are in the published currency, never converted or summed across currencies."],
                "reproduce": [f"python tools/import-ted-cohorts.py --cohort {key} --offline", f"python tools/import-ted-cohorts.py --cohort {key} --download"]}
    (ROOT / f"data/ted-{key}-coverage.json").write_text(json.dumps(coverage, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(key, json.dumps(coverage["counts"], ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cohort", choices=sorted(COHORTS), required=True)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    if args.download:
        download(args.cohort)
    if args.download or args.offline:
        offline(args.cohort)
