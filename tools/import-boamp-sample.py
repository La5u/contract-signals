#!/usr/bin/env python3
"""BOAMP award-lot sample (publications February–April 2025): rebuilt importer.

The original importer predates the repository and was lost. This tool re-implements
the mapping recorded in data/coverage.json ("mapping", "processing", "sampling") and
was checked against the file published on 2026-09-13 (see coverage "rebuild").

  --download  fetch every award notice of the window into data/boamp-raw.json.gz
  --offline   rebuild the 3,000 sampled lots from that snapshot and merge them into
              data/contracts.json, leaving the two Mauges lots and the eight CRC
              audit dossiers (hand-documented rows) untouched.
"""
import argparse
import gzip
import hashlib
import json
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "boamp-raw.json.gz"
API = "https://www.boamp.fr/api/explore/v2.1/catalog/datasets/boamp/records"
WHERE = "nature='ATTRIBUTION' AND dateparution >= '2025-02-01' AND dateparution < '2025-05-01'"
SAMPLE_SIZE = 3000
DIRECT = {"neg-wo-call": True, "open": False, "restricted": False, "comp-dial": False, "neg-w-call": False, "innovation": False}
TEXT = {
    "amountBasis": "Valeur de l’offre retenue déclarée en EUR (PayableAmount), pas le total de l’avis ni le plafond de l’accord-cadre. Vérifier le régime de taxes et le périmètre dans l’avis original.",
    "dateNote": "Date de conclusion déclarée (SettledContract/IssueDate), sinon inconnue. La date de publication n’est pas substituée à la date du contrat.",
    "notes": "Import BOAMP eForms. La durée est la période initiale déclarée en mois, sans reconductions ; les autres unités restent inconnues. Offres : total déclaré sous le code tenders uniquement, sans présumer leur recevabilité. Aucun examen systématique des audits n’a été effectué : constat officiel inconnu, pas absence de constat.",
    "identifierNote": "Identifiants transcrits depuis eForms. CON/LOT sont locaux à l’avis ; aucune égalité avec un identifiant DECP n’est présumée. SIREN dérivé seulement d’un SIRET français à 14 chiffres.",
}


# ---- helpers for the XML-as-JSON shape of eForms (text nodes, single-or-list) ----
def as_list(v):
    return [] if v is None else v if isinstance(v, list) else [v]


def text(v):
    if isinstance(v, dict):
        return v.get("#text")
    return v


def first_text(v):
    items = as_list(v)
    return text(items[0]) if items else None


def ids(v):
    return [text(x.get("cbc:ID")) for x in as_list(v) if isinstance(x, dict)]


def path(node, *keys):
    """Descend through keys, taking the first element wherever eForms has a list."""
    for key in keys:
        if isinstance(node, list):
            node = node[0] if node else None
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node[0] if isinstance(node, list) and node else node


def download():
    def get(url):
        for attempt in range(6):
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "contract-signals/0.1"}), timeout=120) as r:
                    return json.load(r)
            except Exception:
                if attempt == 5:
                    raise
                time.sleep(2 ** attempt)
    started = datetime.now(timezone.utc).isoformat()
    records, pages, total, offset = [], [], None, 0
    while True:
        url = API + "?" + urllib.parse.urlencode({"where": WHERE, "limit": 100, "offset": offset, "order_by": "idweb"})
        page = get(url)
        total = total if total is not None else page["total_count"]
        if page["total_count"] != total:
            raise RuntimeError("total_count changed during pagination; start again")
        records += page["results"]
        pages.append({"url": url, "offset": offset, "count": len(page["results"])})
        offset += len(page["results"])
        if offset >= total or not page["results"]:
            break
    if len(records) != total:
        raise RuntimeError("incomplete pagination")
    raw = {"source": API, "where": WHERE, "retrievedAt": started, "total": total, "queries": pages, "records": records}
    RAW.write_bytes(gzip.compress(json.dumps(raw, ensure_ascii=False).encode("utf-8"), mtime=0))
    print(f"saved {total} notices")


def lot_rows(record):
    """One candidate row per winning LotResult; None when the notice is not eForms."""
    try:
        notice = json.loads(record["donnees"])["EFORMS"]["ContractAwardNotice"]
    except (KeyError, TypeError, ValueError):
        return None
    ext = notice["ext:UBLExtensions"]["ext:UBLExtension"]["ext:ExtensionContent"]["efext:EformsExtension"]
    result = ext.get("efac:NoticeResult") or {}
    orgs = {}
    for o in as_list((ext.get("efac:Organizations") or {}).get("efac:Organization")):
        company = o.get("efac:Company") or {}
        orgs[text(path(company, "cac:PartyIdentification", "cbc:ID"))] = {
            "name": text(path(company, "cac:PartyName", "cbc:Name")),
            "companyId": text(path(company, "cac:PartyLegalEntity", "cbc:CompanyID")),
            "country": text(path(company, "cac:PostalAddress", "cac:Country", "cbc:IdentificationCode"))}
    tenders = {first_text(t.get("cbc:ID")): t for t in as_list(result.get("efac:LotTender"))}
    contracts = {first_text(c.get("cbc:ID")): c for c in as_list(result.get("efac:SettledContract"))}
    parties = {first_text(p.get("cbc:ID")): p for p in as_list(result.get("efac:TenderingParty"))}
    lots = {first_text(l.get("cbc:ID")): l for l in as_list(notice.get("cac:ProcurementProjectLot"))}
    buyer_org = text(path(notice, "cac:ContractingParty", "cac:Party", "cac:PartyIdentification", "cbc:ID"))
    procedure_code = text(path(notice, "cac:TenderingProcess", "cbc:ProcedureCode"))
    rows = []
    for res in as_list(result.get("efac:LotResult")):
        if first_text(res.get("cbc:TenderResultCode")) != "selec-w":
            continue
        tender_ids, contract_ids = ids(res.get("efac:LotTender")), ids(res.get("efac:SettledContract"))
        lot_id = text(path(res, "efac:TenderLot", "cbc:ID"))
        res_id = first_text(res.get("cbc:ID"))
        if len(tender_ids) != 1 or len(contract_ids) > 1 or not lot_id:
            rows.append({"excluded": "several or no winning tender/contract references"})
            continue
        tender = tenders.get(tender_ids[0]) or {}
        party = parties.get(text(path(tender, "efac:TenderingParty", "cbc:ID"))) or {}
        members = [orgs.get(t) for t in ids(party.get("efac:Tenderer")) if orgs.get(t)]
        members = [m | {"org": t} for t, m in zip(ids(party.get("efac:Tenderer")), members)]
        if not members or not any(m["name"] for m in members):
            rows.append({"excluded": "no identified holder"})
            continue
        amount_node = path(tender, "cac:LegalMonetaryTotal", "cbc:PayableAmount")
        amount = None
        if isinstance(amount_node, dict) and amount_node.get("@currencyID") == "EUR":
            try:
                value = float(amount_node["#text"])
                amount = (int(value) if value.is_integer() else value) if value >= 0 else None
            except (TypeError, ValueError):
                amount = None
        offers = None
        for stat in as_list(res.get("efac:ReceivedSubmissionsStatistics")):
            if first_text(stat.get("efbc:StatisticsCode")) == "tenders" and str(stat.get("efbc:StatisticsNumeric", "")).isdigit():
                offers = int(stat["efbc:StatisticsNumeric"])
        contract = contracts.get(contract_ids[0]) if contract_ids else {}
        issue = text(path(contract, "cbc:IssueDate"))
        lot = lots.get(lot_id) or {}
        project = path(lot, "cac:ProcurementProject") or {}
        duration_node = path(project, "cac:PlannedPeriod", "cbc:DurationMeasure")
        duration = None
        if isinstance(duration_node, dict) and duration_node.get("@unitCode") == "MONTH":
            try:
                duration = float(duration_node["#text"])  # months, kept as a float like the original
            except (TypeError, ValueError):
                duration = None
        cpv = text(path(project, "cac:MainCommodityClassification", "cbc:ItemClassificationCode"))
        supplier_ids = []
        for m in members:
            cid = (m["companyId"] or "").strip()
            if not cid:
                continue
            compact = re.sub(r"\s", "", cid)
            # A French SIRET/SIREN only for a French address: foreign registration
            # numbers can have the same length.
            if m["country"] != "FRA":
                supplier_ids.append({"id": cid, "identifierType": "identifiant publié", "siren": None})
            elif re.fullmatch(r"\d{14}", compact):
                supplier_ids.append({"id": compact, "identifierType": "SIRET", "siren": compact[:9]})
            elif re.fullmatch(r"\d{9}", compact):
                supplier_ids.append({"id": compact, "identifierType": "SIREN", "siren": compact})
            else:
                supplier_ids.append({"id": cid, "identifierType": "identifiant publié", "siren": None})
        buyer_id = re.sub(r"\s", "", (orgs.get(buyer_org) or {}).get("companyId") or "")
        lot_title = text(path(project, "cbc:Name"))
        rows.append({
            "id": f"boamp-{record['idweb']}-{lot_id.lower()}",
            "date": issue[:10] if issue else None, "buyer": record.get("nomacheteur"),
            "supplier": " / ".join(m["name"] for m in members if m["name"]),
            "description": " — ".join(x for x in [record.get("objet"), lot_title] if x) or None,
            "amount": amount, "procedure": record.get("procedure_libelle"), "offers": offers, "durationMonths": duration,
            "directAward": DIRECT.get(procedure_code), "officialFinding": None, "dataStatus": "verified",
            "source": record.get("url_avis") or f"https://www.boamp.fr/pages/avis/?q=idweb:{record['idweb']}",
            "sourceLabel": f"BOAMP — avis d’attribution {record['idweb']} ({record.get('dateparution')})",
            "sourceReference": f"{lot_id}, {res_id}, {tender_ids[0]}, {contract_ids[0] if contract_ids else '—'}; supplier organization {', '.join(m['org'] for m in members)}; source dateparution {record.get('dateparution')}.",
            "amountBasis": TEXT["amountBasis"], "dateNote": TEXT["dateNote"], "notes": TEXT["notes"],
            "dataFamily": "boamp", "cohortId": None,
            "buyerSiret": buyer_id if re.fullmatch(r"\d{14}", buyer_id) else None,
            "supplierIds": supplier_ids, "contractId": contract_ids[0] if contract_ids else None,
            "contractFolderId": text(notice.get("cbc:ContractFolderID")) or record.get("contractfolderid"),
            "lotId": lot_id, "cpv": cpv, "noticeId": record["idweb"], "publicationDate": record.get("dateparution"),
            "identifierNote": TEXT["identifierNote"],
        })
    return rows


def build(raw):
    unsupported, candidates, excluded = 0, [], 0
    for record in raw["records"]:
        rows = lot_rows(record)
        if rows is None:
            unsupported += 1
            continue
        for row in rows:
            if "excluded" in row:
                excluded += 1
            else:
                candidates.append(row)
    by_id = {}
    for row in candidates:
        by_id.setdefault(row["id"], []).append(row)
    unique, conflicting, duplicates = [], 0, 0
    for row_id, rows in by_id.items():
        variants = {json.dumps(r, sort_keys=True, ensure_ascii=False) for r in rows}
        duplicates += len(rows) - len(variants)
        if len(variants) > 1:
            conflicting += 1
        else:
            unique.append(rows[0])
    unique.sort(key=lambda r: hashlib.sha256(r["id"].encode("utf-8")).hexdigest())
    stats = {"records": len(raw["records"]), "unsupportedSchemaRecords": unsupported, "eligible_awarded_supplier": len(candidates),
             "excludedResults": excluded, "distinct_notice_lot_ids": len(by_id), "conflicting_notice_lot_ids_excluded": conflicting,
             "identical_duplicate_rows": duplicates, "unique_eligible_lots": len(unique)}
    return unique[:SAMPLE_SIZE], stats


def offline():
    raw = json.loads(gzip.decompress(RAW.read_bytes()))
    if raw["total"] != len(raw["records"]):
        raise ValueError("Raw snapshot incomplete")
    sample, stats = build(raw)
    path = DATA / "contracts.json"
    existing = json.loads(path.read_text(encoding="utf-8"))
    sampled = [r.get("dataFamily") == "boamp" and not r["id"].startswith("boamp-25-846-") for r in existing]
    first, last = sampled.index(True), len(sampled) - 1 - sampled[::-1].index(True)
    if not all(sampled[first:last + 1]):
        raise ValueError("Hand-documented rows found inside the sampled block")
    # Hand-documented rows (Mauges lots, CRC dossiers) keep their place around the sample.
    rows = existing[:first] + sample + existing[last + 1:]
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(stats, indent=1))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    if args.download:
        download()
        offline()
    elif args.offline:
        offline()
    else:
        parser.error("choose --download or --offline")
