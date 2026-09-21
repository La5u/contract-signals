#!/usr/bin/env python3
"""Import the bounded BOAMP cohort.  ``--offline`` regenerates from the saved raw extract."""
import argparse, json, re, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path

API = "https://www.boamp.fr/api/explore/v2.1/catalog/datasets/boamp/records"
DATE = "2025-02-03"
WHERE = "dateparution = date'2025-02-03' AND nature = 'APPEL_OFFRE' AND etat = 'INITIAL'"


def get(params):
    url = API + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=60) as response:
        return url, json.load(response)


def ids_in(record):
    values = record.get("annonce_lie") or []
    return {str(x) for x in (values if isinstance(values, list) else [values])}


def linked(root_id):
    """Fetch every page; truncation is an error, never a silently accepted extract."""
    rows, offset, first_url, total = [], 0, None, None
    while True:
        url, payload = get({"where": f"annonce_lie = '{root_id}'", "limit": 100,
                            "offset": offset, "order_by": "dateparution ASC, idweb ASC"})
        first_url = first_url or url
        total = payload.get("total_count", len(payload.get("results", [])))
        page = [r for r in payload.get("results", []) if root_id in ids_in(r)]
        rows.extend(page)
        raw_count = len(payload.get("results", []))
        if offset + raw_count >= total: break
        if raw_count == 0: raise RuntimeError(f"pagination interrompue pour {root_id}")
        offset += raw_count
    if len(rows) != total:
        # The API total includes only exact-array matches in this query; mismatch means unsafe data.
        raise RuntimeError(f"résultats liés incomplets pour {root_id}: {len(rows)}/{total}")
    return first_url, rows


def iso_date(value):
    return value[:10] if isinstance(value, str) and len(value) >= 10 else None


def kind(record):
    status, nature = (record.get("etat") or "").upper(), (record.get("nature") or "").upper()
    if status == "RECTIFICATIF" or nature == "RECTIFICATIF": return "correction"
    if status in {"ATTRIBUTION", "RESULTAT", "AWARD"} or nature in {"ATTRIBUTION", "RESULTAT"}: return "award"
    return "initial"


def parse_data(record):
    try: data = json.loads(record.get("donnees") or "{}")
    except (TypeError, json.JSONDecodeError): return {}, None
    schema = next(iter(data), None)
    body = data.get("FNSimple", {})
    section = body.get("initial") or body.get("rectificatif") or body.get("attribution") or {}
    return section, schema


def procedure(record, section):
    p = section.get("procedure", {})
    # In FNSimple, presence of procedureAdapteeO (even an empty value) is the affirmative flag.
    if "procedureAdapteeO" in p: return "MAPA"
    return record.get("procedure_categorise") or record.get("soustype_procedure") or record.get("type_procedure")


def cpv(value):
    value = str(value or "")
    return value if re.fullmatch(r"\d{8}", value) else None


def lots(section, record):
    raw = section.get("lots", {}).get("lot", [])
    if isinstance(raw, dict): raw = [raw]
    result = []
    for i, lot in enumerate(raw, 1):
        desc = lot.get("description")
        m = re.match(r"\s*([0-9]+[A-Za-z]?)\s*:", desc or "")
        ident = m.group(1) if m else None
        codes = lot.get("codeCPV", [])
        codes = codes if isinstance(codes, list) else [codes]
        result.append({"id": ident, "version": None, "description": desc,
                       "cpv": [x for x in (cpv(c.get("objetPrincipal", {}).get("classPrincipale")) for c in codes) if x],
                       "deadline": section.get("procedure", {}).get("dateReceptionOffres"),
                       "raw": lot})
    return result


def notice(record, source):
    section, schema = parse_data(record)
    p = section.get("procedure", {})
    return {"id": record.get("idweb"), "noticeIdentifier": record.get("idweb"),
            "version": None, "publicationState": record.get("etat"), "kind": kind(record),
            "publicationDate": iso_date(record.get("dateparution")),
            "deadline": record.get("datelimitereponse") or p.get("dateReceptionOffres"),
            "procedureType": procedure(record, section), "accelerated": None,
            "source": source, "previousNoticeIds": sorted(ids_in(record)),
            "correctionText": section.get("infosRectif"),
            "schema": schema, "parsedFields": {"cpv": cpv(section.get("natureMarche", {}).get("codeCPV", {}).get("objetPrincipal", {}).get("classPrincipale")),
            "procedureReference": section.get("communication", {}).get("identifiantInterne"),
            "procedureDocument": section.get("communication", {}).get("urlDocConsul") or section.get("communication", {}).get("urlProfilAch"),
            "lots": len(lots(section, record))}}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--offline", action="store_true"); args = ap.parse_args()
    out = Path(__file__).resolve().parents[1] / "data"
    old = json.loads((out / "consultations-raw.json").read_text()) if args.offline else None
    if old:
        retrieved = old.get("retrievedAt") or datetime.now(timezone.utc).isoformat()
        records = old["records"]
        roots = sorted((r for r in records if r.get("etat") == "INITIAL" and r.get("nature") == "APPEL_OFFRE"), key=lambda r: r.get("idweb", ""))[:10]
        root_payload = {"total_count": old["initialCohortMatches"]}; root_url = API + "?" + urllib.parse.urlencode({"where": WHERE, "limit": 10, "order_by": "idweb ASC"})
        # Older extracts called the cohort date simply ``date``.  Keep provenance
        # unambiguous when regenerating them offline.
        query_log = []
        for q in old.get("queries", []):
            q = dict(q); q.pop("date", None); q.setdefault("retrievedAt", retrieved); q.setdefault("cohortDate", DATE)
            query_log.append(q)
    else:
        root_url, root_payload = get({"where": WHERE, "limit": 10, "order_by": "idweb ASC"}); roots = sorted(root_payload.get("results", []), key=lambda r: r.get("idweb", ""))[:10]
        records, query_log, retrieved = list(roots), [], datetime.now(timezone.utc).isoformat()
        query_log.append({"url": root_url, "retrievedAt": retrieved, "cohortDate": DATE, "count": len(roots), "purpose": "bounded initial cohort"})
    rows, raw_by_id = [], {}
    for root in roots:
        rid = root["idweb"]; collected = {rid: [root]}; queue = [rid]
        while queue:
            parent = queue.pop(0)
            if args.offline:
                children = [r for r in records if parent in ids_in(r)]
                url = next((q.get("url") for q in query_log if q.get("from", q.get("root")) == parent), None)
            else:
                url, children = linked(parent)
                records.extend(child for child in children if child not in records)
                query_log.append({"url": url, "retrievedAt": retrieved, "cohortDate": DATE, "count": len(children), "purpose": "exact linked notices by annonce_lie", "root": rid, "from": parent})
            for child in children:
                cid = child.get("idweb");
                if cid and cid not in collected:
                    collected[cid] = [child]; queue.append(cid)
                elif cid and child not in collected[cid]:
                    collected[cid].append(child)
        chain = [x for group in collected.values() for x in group]
        for r in chain: raw_by_id.setdefault(r.get("idweb"), []).append(r)
        initial_section, _ = parse_data(root); all_lots = lots(initial_section, root)
        primary_cpv = cpv(initial_section.get("natureMarche", {}).get("codeCPV", {}).get("objetPrincipal", {}).get("classPrincipale"))
        procedure_reference = initial_section.get("communication", {}).get("identifiantInterne")
        deadline = root.get("datelimitereponse") or initial_section.get("procedure", {}).get("dateReceptionOffres")
        notices = [notice(root, root.get("url_avis") or root_url)]
        awards = []
        for item in sorted(chain, key=lambda r: (r.get("dateparution") or "", r.get("idweb") or "")):
            if item is root: continue
            n = notice(item, item.get("url_avis") or root_url)
            (awards if n["kind"] == "award" else notices).append(n)
        reasons = ["Cohorte bornée aux 10 premiers idweb; non exhaustive.", "Recherche des liens par identifiants BOAMP; aucune recherche TED indépendante.", "Complétude indépendante de la chaîne de corrections non démontrée."]
        if any(len(group) > 1 for group in collected.values()):
            reasons.append("Versions contradictoires du même idweb conservées ; calcul exclu.")
        rows.append({"id": f"boamp-consultation-{rid}", "buyer": root.get("nomacheteur") or "Acheteur non renseigné", "description": root.get("objet") or "Objet non renseigné", "dataStatus": "verified", "dataFamily": "boamp", "amount": None, "date": None, "offers": None, "durationMonths": None, "directAward": None, "procedure": procedure(root, initial_section), "procedureReference": procedure_reference, "deadline": deadline, "cpv": primary_cpv, "source": root.get("url_avis") or root_url, "sourceLabel": "BOAMP API — avis initial", "noticeId": rid, "publicationDate": root.get("dateparution"), "nature": root.get("nature"), "contractId": root.get("contractfolderid"), "lotId": None, "notes": "Schéma structuré FNSimple; champs parsés et données brutes conservées.", "consultation": {"procedureId": root.get("contractfolderid"), "procedureReference": procedure_reference, "lotId": None, "initialNoticeId": rid, "searchComplete": False, "exclusions": reasons, "lots": all_lots, "notices": notices, "matchedAwards": awards}})
    raw = {"source": API, "retrievedAt": retrieved, "initialCohortMatches": root_payload.get("total_count"), "records": records, "queries": query_log}
    (out / "consultations-raw.json").write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n")
    (out / "consultations.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n")
    coverage = {"source": API, "retrievedAt": retrieved, "scope": {"where": WHERE, "url": root_url, "cohortDate": DATE, "selection": "10 premiers avis initiaux idweb"}, "counts": {"initialCohortMatches": root_payload.get("total_count"), "initialDownloaded": len(roots), "rawRecordsDownloaded": len(records), "normalizedRows": len(rows), "corrections": sum(sum(n["kind"] == "correction" for n in r["consultation"]["notices"]) for r in rows), "matchedAwards": sum(len(r["consultation"]["matchedAwards"]) for r in rows)}, "queries": query_log, "exclusions": ["Le jeu est FNSimple (source_schema 3.2.5), pas eForms; aucun avis FNSimple n'est exclu.", "Aucun CPV ou lot n'est inventé; les versions conflictuelles restent dans le brut et sont exclues des calculs.", "searchComplete=false: la complétude indépendante des chaînes BOAMP n'est pas vérifiable."]}
    coverage["mapping"] = {"unit": "Une ligne par avis initial, pas par contrat ni lot attribué", "versions": "FNSimple ne fournit pas de numéro de version : null ; publicationState préserve INITIAL/RECTIFICATIF", "lots": "16 identifiants textuels transcrits du préfixe explicite de description, 25-12220 ; pas de correspondance aux résultats", "deadline": "datelimitereponse API avec fuseau si disponible, sinon dateReceptionOffres brute ; infosRectif conservé en texte sans inventer de fuseau", "cpv": "Huit chiffres publiés ; aucune clé de contrôle ajoutée", "awards": "annonce_lie exact, au niveau avis uniquement ; aucune jointure DECP"}
    coverage["rules"] = {"version": "2.1", "shortBiddingPeriod": {"strictlyLessThanCalendarDays": 15, "weight": 12, "family": "competition (maximum)", "evaluableRows": 0, "triggeredRows": 0, "excludedRows": len(rows), "requirements": "Procédure ouverte explicitement non accélérée, procédure/lot identifiés, versions complètes vérifiées, échéances explicites avec fuseau ; réductions, réouvertures et ambiguïtés exclues"}}
    coverage["limitations"] = ["10 premiers identifiants parmi 200 avis initiaux du jour, sans sélection par score ; pas représentatif.", "Aucun téléchargement TED indépendant. Les recherches exactes annonce_lie ne garantissent pas la complétude des rectificatifs.", "25-22678 reporte explicitement au 14 mars 2025 à 12:00 ; fuseau non donné dans le texte, aucun calcul automatique.", "Absence de résultat lié ne signifie pas absence d’attribution. Aucun montant initial, plafond, avenant ou paiement additionné."]
    (out / "consultations-coverage.json").write_text(json.dumps(coverage, ensure_ascii=False, indent=2) + "\n")

if __name__ == "__main__": main()
