#!/usr/bin/env python3
"""Paris & Ardèche DECP cohort (notifications 2024–2025): rebuilt importer.

The original importer for this cohort predates the repository and was lost. This
tool re-implements its documented rules (docs/project-journal.md, "DECP history
2024–2025") and reuses the six-city parsing helpers. It was checked against the
file published on 2026-09-13: identical on every contract except where the source
itself changed (see data/decp-coverage.json, "rebuild").

  --download  fetch every row for the two buyer SIRETs into data/decp-history-raw.json.gz
  --offline   regenerate data/decp-history.json from that raw snapshot

The three rows of the Paris 13 November 2025 dossier carry hand-curated fields
(supplier name, name source, framework id, project evidence). They live in
data/decp-history-curated.json and are applied last, so manual edits stay visible.
"""
import argparse
import gzip
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "decp-history-raw.json.gz"
CURATED = DATA / "decp-history-curated.json"
spec = importlib.util.spec_from_file_location("decp_cities", ROOT / "tools/import-decp-cities.py")
cities = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cities)

COHORT = "decp-paris-ardeche-2024-2025"
BUYERS = [("21750001600019", "Ville de Paris"), ("22070001700019", "Département de l’Ardèche")]
# The original cohort also recognised "Dialogue compétitif" as competitive.
COMPETITIVE = set(cities.PROCEDURE_COMPETITIVE) | {"Dialogue compétitif"}
ALTERNATIVE_FIELDS = ["amount", "offers", "date", "durationMonths", "cpv", "procedure", "priceType", "priceForm", "nature", "supplierIds", "description"]
CONFLICT_FIELDS = ALTERNATIVE_FIELDS
TEXT = {
    "sourceLabel": "DECP — enregistrements officiels de ce contrat (JSON)",
    "amountBasis": "Montant HT initial forfaitaire ou estimé déclaré, jamais additionné entre variantes ou cotitulaires. Une modification indique un nouveau montant déclaré, pas nécessairement une dépense payée ni un prix unitaire.",
    "dateNote": "Date de notification initiale ; cohorte 2024–2025. Les dates des modifications peuvent être postérieures à 2025.",
    "notes": "Cohorte exploratoire des lignes publiées pour ces deux SIRET ; pas garantie d’exhaustivité des achats réels. CDL/INX et valeurs absentes restent inconnus. Les fournisseurs sont affichés par identifiant, sans nom inféré. Une procédure adaptée n’est pas présumée concurrentielle. Les modifications indexées peuvent être partielles ou ne contenir que la dernière version.",
}


def direct(procedure):
    if procedure in cities.PROCEDURE_DIRECT:
        return True
    return False if procedure in COMPETITIVE else None


def source_url(buyer, cid):
    return cities.url_for({"where": f"acheteur_id='{buyer}' AND id='{cid.replace(chr(39), chr(39) * 2)}'", "limit": 100})


def download():
    records, pages, totals = [], [], {}
    started = datetime.now(timezone.utc).isoformat()
    for siret, _ in BUYERS:
        offset, total = 0, None
        while True:
            url = cities.url_for({"where": cities.where(siret), "limit": 100, "offset": offset, "order_by": "datenotification asc,id asc"})
            page = cities.fetch(url)
            if total is not None and total != page["total_count"]:
                raise RuntimeError("total_count changed during pagination; start again")
            total = page["total_count"]
            rows = page.get("results", [])
            records.extend(rows)
            pages.append({"url": url, "buyerSiret": siret, "offset": offset, "count": len(rows), "total": total})
            if offset + len(rows) >= total:
                break
            if not rows:
                raise RuntimeError("empty page before total_count")
            offset += len(rows)
        totals[siret] = total
    raw = {"source": cities.API, "retrievedAt": started, "records": records, "queries": pages, "totals": totals}
    RAW.write_bytes(gzip.compress((json.dumps(raw, ensure_ascii=False, indent=1) + "\n").encode("utf-8"), mtime=0))
    print(f"saved {len(records)} rows: {totals}")


def normalize(raw):
    groups = {}
    for r in raw["records"]:
        key = (cities.identifier(r.get("acheteur_id")), cities.identifier(r.get("id")))
        if key[0] not in dict(BUYERS) or not key[1]:
            raise ValueError("Buyer outside the cohort or missing contract id")
        d = cities.date(r.get("datenotification"))
        if not d or not cities.FROM <= d < cities.TO:
            raise ValueError("Notification outside the window")
        groups.setdefault(key, []).append(r)
    rows = []
    for (buyer, cid), records in groups.items():
        unique, seen = [], set()
        for r in records:
            sig = json.dumps(r, sort_keys=True, ensure_ascii=False)
            if sig not in seen:
                seen.add(sig)
                unique.append(r)
        values = [{f: cities.initial_tuple(r)[f] for f in ALTERNATIVE_FIELDS} for r in unique]
        base = values[0]
        conflicts = [f for f in CONFLICT_FIELDS if any(v[f] != base[f] for v in values[1:])]
        chosen = {f: None if f in conflicts else base[f] for f in CONFLICT_FIELDS}
        publication = {cities.date(r.get("datepublicationdonnees")) for r in unique}
        mods = [r for r in unique if cities.is_mod(r)]
        history = [{"kind": "initial", "id": cid, "date": chosen["date"],
                    "publicationDate": publication.pop() if len(publication) == 1 else None,
                    "amount": chosen["amount"], "durationMonths": chosen["durationMonths"], "supplierId": None}]
        for r in sorted(mods, key=lambda x: (cities.date(x.get("datenotificationmodificationmodification")) or "", str(x.get("idmodification")))):
            event = {"kind": "modification", "id": str(cities.clean(r.get("idmodification"))),
                     "date": cities.date(r.get("datenotificationmodificationmodification")),
                     "publicationDate": cities.date(r.get("datepublicationdonneesmodificationmodification")),
                     "amount": cities.number(r.get("montantmodification")),
                     "durationMonths": cities.number(r.get("dureemoismodification")), "supplierId": None}
            if event not in history:
                history.append(event)
        ids = chosen["supplierIds"]
        rows.append({
            "amount": chosen["amount"], "offers": chosen["offers"], "date": chosen["date"], "durationMonths": chosen["durationMonths"],
            "cpv": chosen["cpv"], "procedure": chosen["procedure"], "priceType": chosen["priceType"], "priceForm": chosen["priceForm"],
            "nature": chosen["nature"], "description": chosen["description"] or "Objet non renseigné",
            "id": f"decp-{buyer}-{cid}", "buyer": dict(BUYERS)[buyer], "buyerSiret": buyer, "contractId": cid,
            "lotId": None, "noticeId": None, "publicationDate": history[0]["publicationDate"],
            "supplier": " / ".join(f"{x.get('identifierType') or 'Identifiant'} {x['id']}" for x in ids) if ids else None,
            "supplierIds": ids, "directAward": direct(chosen["procedure"]), "officialFinding": None,
            "dataStatus": "verified", "dataFamily": "decp", "cohortId": COHORT,
            "source": source_url(buyer, cid), "sourceLabel": TEXT["sourceLabel"],
            "sourceReference": f"SIRET acheteur {buyer} ; identifiant {cid}. {len(unique)} ligne(s) source ; {len(history) - 1} modification(s) distincte(s) publiée(s).",
            "amountBasis": TEXT["amountBasis"], "dateNote": TEXT["dateNote"], "notes": TEXT["notes"],
            "history": history, "initialConflicts": conflicts, "initialAlternatives": values if conflicts else [], "rawVariantCount": len(unique),
        })
    return rows


def offline():
    raw = json.loads(gzip.decompress(RAW.read_bytes()))
    for siret, _ in BUYERS:
        if sum(r.get("acheteur_id") == siret for r in raw["records"]) != raw["totals"][siret]:
            raise ValueError("Raw snapshot incomplete for " + siret)
    rows = normalize(raw)
    curated = json.loads(CURATED.read_text(encoding="utf-8"))
    by_id = {r["id"]: r for r in rows}
    for row_id, fields in curated["rows"].items():
        by_id[row_id].update(fields)
    profiles = {}
    identity_file = DATA / "supplier-identities.json"
    if identity_file.exists():
        for p in json.loads(identity_file.read_text(encoding="utf-8"))["identities"]:
            if p.get("status") == "available" and p.get("diffusionStatus") == "O" and p.get("name"):
                profiles[p["siren"]] = {k: p.get(k) for k in ["siren", "name", "administrativeState", "diffusionStatus", "source", "retrievedAt", "status"]}
    for row in rows:
        sirens = {s.get("siren") for s in row["supplierIds"] or []} - {None}
        row["supplierProfiles"] = [profiles[s] for s in sorted(sirens) if s in profiles]
    rows.sort(key=lambda r: (r["buyerSiret"] != BUYERS[0][0], r["contractId"]))
    (DATA / "decp-history.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(rows)} contracts; {sum(bool(r['initialConflicts']) for r in rows)} with initial conflicts; "
          f"{sum(len(r['history']) > 1 for r in rows)} with published modifications; raw retrieved {raw['retrievedAt']}")


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
