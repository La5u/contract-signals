#!/usr/bin/env python3
"""Import the preselected six-city DECP cohort; --offline regenerates from raw JSON."""
import argparse, json, re, math, sys, urllib.parse, urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

API = "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/decp-2022-marches-valides/records"
LOOKUP = "https://recherche-entreprises.api.gouv.fr/search"
FROM, TO = "2024-01-01", "2026-01-01"
COHORT = "decp-six-cities-2024-2025"
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
BUYERS = [
    ("21350238800019", "Commune de Rennes", "Rennes"),
    ("21440109300015", "Commune de Nantes", "Nantes"),
    ("21330063500017", "Commune de Bordeaux", "Bordeaux"),
    ("21380185500015", "Commune de Grenoble", "Grenoble"),
    ("21210231300013", "Commune de Dijon", "Dijon"),
    ("21370261600011", "Commune de Tours", "Tours"),
]

def where(siret):
    return f"acheteur_id='{siret}' AND datenotification >= '{FROM}' AND datenotification < '{TO}'"

def url_for(params): return API + "?" + urllib.parse.urlencode(params)
def fetch(url):
    with urllib.request.urlopen(url, timeout=90) as r: return json.load(r)
def clean(v): return None if v in (None, "", "CDL", "INX") else v
def identifier(v):
    v = clean(v)
    return str(v) if v is not None else None

def number(v):
    v = clean(v)
    try:
        value = float(v) if v is not None else None
        return value if value is not None and value >= 0 and math.isfinite(value) else None
    except (TypeError, ValueError): return None
def date(v):
    if not isinstance(v, str) or not re.match(r'^\d{4}-\d{2}-\d{2}', v): return None
    try: return datetime.strptime(v[:10], '%Y-%m-%d').strftime('%Y-%m-%d')
    except ValueError: return None
def supplier_ids(r, modification=False):
    p = "idtitulairemodification" if modification else "titulaire_id_"
    t = "typeidentifianttitulairemodification" if modification else "titulaire_typeidentifiant_"
    vals = []
    if modification:
        pairs = [(r.get(p), r.get(t))]
    else:
        pairs = [(r.get(p+str(i)), r.get(t+str(i))) for i in range(1,4)]
    for ident, typ in pairs:
        ident, typ = clean(ident), clean(typ)
        if ident is not None:
            item = {"id": str(ident), "identifierType": str(typ) if typ else None}
            if typ == "SIRET" and re.fullmatch(r"\d{14}", str(ident)): item["siren"] = str(ident)[:9]
            elif typ == "SIREN" and re.fullmatch(r"\d{9}", str(ident)): item["siren"] = str(ident)
            vals.append(item)
    return vals

def price_types(v):
    """Several price types are an unordered set: the same types listed in another order are not a conflict."""
    v = clean(v)
    return ", ".join(sorted(x.strip() for x in v.split(","))) if isinstance(v, str) and "," in v else v

def initial_tuple(r):
    offers = r.get("offresrecues")
    try: offers = int(offers) if str(offers).isdigit() and int(offers) >= 0 else None
    except (TypeError, ValueError): offers = None
    return {"description": clean(r.get("objet")), "amount": number(r.get("montant")), "offers": offers,
      "date": date(r.get("datenotification")), "publicationDate": date(r.get("datepublicationdonnees")), "durationMonths": number(r.get("dureemois")), "cpv": clean(r.get("codecpv")),
      "procedure": clean(r.get("procedure")), "priceType": price_types(r.get("typesprix")), "priceForm": clean(r.get("formeprix")),
      "nature": clean(r.get("nature")), "supplierIds": supplier_ids(r), "frameworkId": identifier(r.get("idaccordcadre")),
      "executionModalities": clean(r.get("modalitesexecution")), "techniques": clean(r.get("techniques"))}

def is_mod(r): return clean(r.get("idmodification")) is not None

# Exact labels observed in the DECP cohorts (plus the official negotiated label).
PROCEDURE_DIRECT = {"Marché passé sans publicité ni mise en concurrence préalable": True,
                    "Marché négocié sans publicité ni mise en concurrence préalable": True}
PROCEDURE_COMPETITIVE = {"Appel d'offres ouvert": False, "Appel d'offres restreint": False,
                         "Procédure avec négociation": False, "Dialogue compétitif": False}
def direct(procedure):
    if procedure in PROCEDURE_DIRECT: return True
    if procedure in PROCEDURE_COMPETITIVE: return False
    return None

def alternatives_equal(a,b):
    return a == b

def single_siret(r):
    ids=[x["id"] for x in supplier_ids(r) if x.get("identifierType")=="SIRET"]
    return ids[0] if len(ids)==1 else None

def split_units(buyer, cid, unique, split):
    """Evidence-backed split of one buyer+identifier group into its distinct contracts.

    Every distinct source row must match exactly one curated entry by holder SIRET,
    amount and notification date, and every entry must be used: otherwise the
    curation is stale and the import stops rather than guess."""
    if any(is_mod(r) for r in unique): raise ValueError(f"{cid} : modification publiée, découpage curé à revoir.")
    units=[]; used=set()
    for r in unique:
        hits=[i for i,l in enumerate(split["lots"]) if l["holderSiret"]==single_siret(r) and l["amount"]==number(r.get("montant")) and l["date"]==date(r.get("datenotification"))]
        if len(hits)!=1 or hits[0] in used: raise ValueError(f"{cid} : découpage curé périmé ou ambigu.")
        used.add(hits[0]); units.append((buyer,cid,[r],split["lots"][hits[0]]))
    if len(used)!=len(split["lots"]): raise ValueError(f"{cid} : lot curé sans ligne source.")
    return units

JOINT = ("Conjoint", "Solidaire")
TUPLE_FIELDS = ["description","amount","offers","date","publicationDate","durationMonths","cpv","procedure","priceType","priceForm","nature","supplierIds","frameworkId","executionModalities","techniques"]

def partition_contracts(unique):
    """Distinct contracts behind one buyer+identifier group, from the rows' own content.

    Rows sharing every initial field are one contract (its modification rows repeat
    those columns). A group differing only in holders, with every row declaring a
    joint grouping, is one joint contract. Anything else differs in a declared
    contract field and is a separate contract under the same published identifier."""
    parts={}
    for r in unique: parts.setdefault(json.dumps(initial_tuple(r),sort_keys=True,ensure_ascii=False),[]).append(r)
    parts=list(parts.values())
    if len(parts)>1 and all(r.get("typegroupementoperateurs") in JOINT for r in unique):
        strip=lambda r:json.dumps({k:v for k,v in initial_tuple(r).items() if k!="supplierIds"},sort_keys=True,ensure_ascii=False)
        if len({strip(p[0]) for p in parts})==1: return [unique], True
    def order(part):
        t=initial_tuple(part[0])
        return (t["date"] or "", t["amount"] if t["amount"] is not None else -1, json.dumps(t["supplierIds"]), t["description"] or "", json.dumps(part[0],sort_keys=True,ensure_ascii=False))
    return sorted(parts,key=order), False

def possibly_same(a, b):
    """Same holders, object, notification date and framework: the rows may be one contract published twice."""
    x,y=initial_tuple(a),initial_tuple(b)
    return bool(x["supplierIds"]) and all(x[k]==y[k] for k in ["supplierIds","description","date","frameworkId"])

def unit_suffix(lot, n):
    return f"lot-{lot['lotNumber']}" if lot.get("lotNumber") else f"contrat-{n}"

def normalize(raw, out, coverage, curated=None):
    curated=curated or {}
    splits={(x["buyerSiret"],x["contractId"]):x for x in curated.get("procedureSplits",[])}
    offer_conflicts={(x["buyerSiret"],x["contractId"]):x for x in curated.get("offerConflicts",[])}
    projects={(p["buyerSiret"],cid):p for p in curated.get("projects",[]) for cid in p["contractIds"]}
    rows = raw["records"]
    by = {}
    for r in rows:
        key=(identifier(r.get('acheteur_id')), identifier(r.get('id')))
        if key[0] not in {s for s, _, _ in BUYERS} or not key[1]:
            raise ValueError('Acheteur hors périmètre ou identifiant manquant : import interrompu, brut préservé.')
        if not date(r.get('datenotification')) or not FROM <= date(r['datenotification']) < TO:
            raise ValueError('Notification hors périmètre ou invalide.')
        by.setdefault(key, []).append(r)
    result=[]; duplicate_rows=0; conflict_groups=0; split_groups=0; joint_groups=0; mod_events=0; mod_conflict_groups=0
    conflict_fields=Counter(); mod_conflict_fields=Counter()
    units=[]
    for (buyer, cid), records in sorted(by.items()):
        # identical source rows are duplicate publication copies, not separate versions
        unique=[]
        seen=set()
        for r in records:
            sig=json.dumps(r,sort_keys=True,ensure_ascii=False)
            if sig in seen: duplicate_rows += 1
            else: seen.add(sig); unique.append(r)
        if (buyer,cid) in splits:
            units.extend({"buyer":b,"cid":c,"rows":u,"lot":l,"split":None,"joint":False} for b,c,u,l in split_units(buyer,cid,unique,splits[(buyer,cid)]))
            continue
        parts,joint=partition_contracts(unique)
        if joint: joint_groups += 1
        if len(parts)==1:
            units.append({"buyer":buyer,"cid":cid,"rows":parts[0],"lot":None,"split":None,"joint":joint})
            continue
        split_groups += 1
        ids=[f"decp-{buyer}-{cid}-{k+1}" for k in range(len(parts))]
        for k,part in enumerate(parts):
            dup=[ids[j] for j,other in enumerate(parts) if j!=k and possibly_same(part[0],other[0])]
            units.append({"buyer":buyer,"cid":cid,"rows":part,"lot":None,"joint":False,"split":{"id":ids[k],"members":ids,"possibleDuplicateOf":dup}})
    unused=set(splits)-{(u["buyer"],u["cid"]) for u in units if u["lot"]}
    if unused: raise ValueError(f"Découpage curé sans groupe source : {sorted(unused)}")
    for unit in units:
        buyer,cid,unique,lot=unit["buyer"],unit["cid"],unit["rows"],unit["lot"]
        # Modification records repeat the initial columns. Filtering them out
        # loses contracts for which only a modification is present.
        vals=[initial_tuple(r) for r in unique]
        base=vals[0]
        fields=TUPLE_FIELDS
        conflicts=[f for f in fields if any(v[f] != base[f] for v in vals[1:])]
        if unit["joint"]:
            # One joint contract: holders are combined, not conflicting.
            conflicts=[f for f in conflicts if f!="supplierIds"]
            merged={}
            for v in vals:
                for x in v["supplierIds"]: merged.setdefault(x["id"],x)
            base={**base,"supplierIds":[merged[k] for k in sorted(merged)]}
        if conflicts:
            conflict_groups += 1
            conflict_fields.update(conflicts)
        chosen={f:(None if f in conflicts else base[f]) for f in fields}
        mods=[r for r in unique if is_mod(r)]
        mod_conflicts=[]
        for mod_id in sorted({str(clean(r.get("idmodification"))) for r in mods}):
            same=[r for r in mods if str(clean(r.get("idmodification"))) == mod_id]
            modvals=[{"amount":number(r.get("montantmodification")), "durationMonths":number(r.get("dureemoismodification")),
                      "date":date(r.get("datenotificationmodificationmodification")), "publicationDate":date(r.get("datepublicationdonneesmodificationmodification")),
                      "supplierId":tuple(x["id"] for x in supplier_ids(r, True))} for r in same]
            mf=[f for f in modvals[0] if any(v[f] != modvals[0][f] for v in modvals[1:])]
            if mf:
                mod_conflicts.append({"id":mod_id, "fields":mf})
                mod_conflict_fields.update(mf)
        if mod_conflicts: mod_conflict_groups += 1
        # A source link is deliberately scoped to this buyer and contract.
        q=where(buyer)+" AND id='"+cid.replace("'", "''")+"'"
        source=url_for({"where":q,"limit":100,"order_by":"datenotification asc,id asc"})
        # History uses conflict-safe chosen values, never an arbitrary first row.
        hist=[{"kind":"initial","id":str(cid),"date":chosen["date"],"publicationDate":chosen["publicationDate"],"amount":chosen["amount"],"durationMonths":chosen["durationMonths"],"supplierId":(chosen["supplierIds"][0]["id"] if len(chosen["supplierIds"] or [])==1 else None)}]
        # retain all distinct published modification versions, ordered by notification/publication/id
        for r in sorted(mods,key=lambda x:(date(x.get("datenotificationmodificationmodification")) or "",date(x.get("datepublicationdonneesmodificationmodification")) or "",str(x.get("idmodification")))):
            ev={"kind":"modification","id":str(clean(r.get("idmodification"))),"date":date(r.get("datenotificationmodificationmodification")),"publicationDate":date(r.get("datepublicationdonneesmodificationmodification")),"amount":number(r.get("montantmodification")),"durationMonths":number(r.get("dureemoismodification")),"supplierId":(supplier_ids(r,True)[0]["id"] if len(supplier_ids(r,True))==1 else None)}
            if ev not in hist: hist.append(ev); mod_events += 1
        name=next((x[1] for x in BUYERS if x[0]==buyer), f"Acheteur {buyer}")
        alt=[]
        for v in vals: alt.append(v)
        row={"amount":chosen["amount"],"offers":chosen["offers"],"date":chosen["date"],"durationMonths":chosen["durationMonths"],"cpv":chosen["cpv"],"procedure":chosen["procedure"],"priceType":chosen["priceType"],"priceForm":chosen["priceForm"],"nature":chosen["nature"],"description":chosen["description"] or "Objet non renseigné","id":f"decp-{str(buyer)}-{str(cid)}","buyer":name,"buyerSiret":str(buyer),"contractId":str(cid),"lotId":None,"noticeId":None,"publicationDate":chosen["publicationDate"],"frameworkId":chosen["frameworkId"],"executionModalities":chosen["executionModalities"],"techniques":chosen["techniques"],"supplier":(" / ".join(f"{x.get('identifierType') or 'Identifiant'} {x['id']}" for x in chosen["supplierIds"]) if chosen["supplierIds"] else None),"supplierIds":chosen["supplierIds"],"directAward":direct(chosen["procedure"]),"officialFinding":None,"dataStatus":"verified","dataFamily":"decp","cohortId":COHORT,"source":source,"sourceLabel":"DECP — enregistrements officiels exacts acheteur + contrat","sourceReference":f"SIRET acheteur {buyer} ; identifiant {cid}. {len(unique)} ligne(s) source ; {len(hist)-1} modification(s) distincte(s).","amountBasis":"Montant initial déclaré du marché ; le montant d’une modification est le nouveau montant total déclaré, jamais additionné. Il ne s’agit pas nécessairement de paiements.","dateNote":"Date de notification initiale ; fenêtre 2024–2025. Les modifications publiées peuvent être postérieures à 2025.","notes":"Cohorte de six communes choisies avant tout calcul de score. Modalités/techniques sont du contexte publié, sans addition ni somme. CDL/INX et absences restent inconnus ; aucun nom de fournisseur n’est inventé.","history":hist,"initialConflicts":conflicts,"initialAlternatives":alt,"sourceRowVariants":unique,"modificationConflicts":mod_conflicts}
        if lot:
            siblings=[u for u in units if u["buyer"]==buyer and u["cid"]==cid]
            ids=[f"decp-{buyer}-{cid}-{unit_suffix(u['lot'], k+1)}" for k,u in enumerate(siblings)]
            if len(set(ids))!=len(ids): raise ValueError(f"{cid} : identifiants de lots non uniques.")
            row["id"]=ids[next(k for k,u in enumerate(siblings) if u is unit)]
            row["lotId"]=lot.get("lotNumber"); row["noticeId"]=lot.get("noticeId")
            same_notice=all(u["lot"]["evidence"]=="notice-lot" for u in siblings) and len({u["lot"]["noticeId"] for u in siblings})==1
            row["procedureGroup"]={"id":f"decp-{buyer}-{cid}","contractId":str(cid),"members":ids,
                "kind":"lots" if same_notice else "shared-identifier",
                "contractReference":lot.get("contractReference"),"lotTitle":lot.get("lotTitle"),
                "basis":("L’identifiant DECP est celui de la procédure ; chaque ligne est un marché de lot distinct, rattaché par l’avis "+str(lot.get("noticeId"))+" (montant, date, référence de marché, titulaire vérifié au répertoire SIRENE).") if same_notice else
                        ("Le même identifiant DECP couvre des marchés distincts (objets, montants et titulaires différents) ; chaque ligne source est conservée séparément"+(", celle-ci rattachée à l’avis "+str(lot.get("noticeId")) if lot.get("noticeId") else "")+".")}
            row["sourceReference"]=f"SIRET acheteur {buyer} ; identifiant {cid} partagé par {len(ids)} marchés distincts" + (f" ; lot {lot['lotNumber']}, réf. {lot['contractReference']} (avis {lot['noticeId']})." if lot.get("lotNumber") else ".")
            conflict=lot if lot.get("noticeOffers") is not None and lot.get("decpOffers")!=lot.get("noticeOffers") else None
        elif unit["split"]:
            g=unit["split"]
            row["id"]=g["id"]
            row["procedureGroup"]={"id":f"decp-{buyer}-{cid}","contractId":str(cid),"members":g["members"],"kind":"shared-identifier",
                "basis":"Le même identifiant DECP est publié pour plusieurs marchés : leurs champs déclarés (objet, montant, titulaire, date, CPV…) diffèrent. Chaque marché distinct est conservé séparément ; aucun identifiant n’est inventé."}
            if g["possibleDuplicateOf"]: row["possibleDuplicateOf"]=g["possibleDuplicateOf"]
            row["sourceReference"]=f"SIRET acheteur {buyer} ; identifiant {cid} partagé par {len(g['members'])} marchés distincts ; {len(unique)} ligne(s) source pour celui-ci ; {len(hist)-1} modification(s) distincte(s)."
            conflict=None
        else:
            if unit["joint"]: row["sourceReference"]+=" Marché conjoint publié sur une ligne par cotitulaire : titulaires réunis."
            conflict=offer_conflicts.get((buyer,cid))
            if conflict and (row["amount"]!=conflict["amount"] or row["offers"]!=conflict["decpOffers"]): raise ValueError(f"{cid} : conflit d’offres curé périmé.")
        if conflict:
            # Two declarations by the same buyer disagree: the count is unknown, never chosen.
            row["offers"]=None
            row["offersConflict"]={"decp":conflict["decpOffers"],"notice":conflict["noticeOffers"],"noticeId":conflict["noticeId"],"contractReference":conflict["contractReference"]}
        if (buyer,cid) in projects and (not lot or lot.get("evidence")=="notice-lot"):
            p=projects[(buyer,cid)]
            row["project"]={k:p[k] for k in ["id","title","basis","source","evidence"]}
        result.append(row)
    coverage["counts"].update({"contracts":len(result),"groupsWithInitialConflicts":conflict_groups,"initialConflictFields":dict(conflict_fields),"groupsWithModificationConflicts":mod_conflict_groups,"modificationConflictFields":dict(mod_conflict_fields),"duplicateRowsDeduplicated":duplicate_rows,"identifierGroupsSplit":split_groups,"jointContractsMerged":joint_groups,"possibleDuplicateRows":sum(bool(r.get("possibleDuplicateOf")) for r in result),"publishedModificationEvents":mod_events})
    return result

def apply_holder_evidence(rows, curated):
    """Holders named only by the Ministry rows, where the award notice and the buyer feed both name others.

    The unconfirmed holder is moved out of supplierIds (it no longer drives supplier indicators) into
    unconfirmedHolders, kept visible with the evidence. Applied only if the buyer feed agrees."""
    import decp_feeds
    feed=decp_feeds.load()["records"]
    applied=[]
    for group in curated.get("unresolvedGroups",[]):
        ev=group.get("holderEvidence")
        if not ev: continue
        targets=[r for r in rows if r["buyerSiret"]==group["buyerSiret"] and r["contractId"]==group["contractId"]]
        if len(targets)!=1: continue
        r=targets[0]
        listed={str(f["titulaire_id"]) for f in feed if f["acheteur_id"]==r["buyerSiret"] and f["id"]==r["contractId"] and f["dateNotification"]==r["date"]
                and f["modification_id"] in (0,None) and f["titulaire_id"] and f["sourceDataset"]!=decp_feeds.SCRAPED}
        if not listed or not listed<=set(ev["confirmed"]): continue
        moved=[x for x in r["supplierIds"] if x["id"] in ev["unconfirmed"]]
        r["supplierIds"]=[x for x in r["supplierIds"] if x["id"] not in ev["unconfirmed"]]
        r["supplier"]=" / ".join(f"{x.get('identifierType') or 'Identifiant'} {x['id']}" for x in r["supplierIds"]) or None
        r["unconfirmedHolders"]=[{**x,"source":"ministry","reason":f"Seulement dans le jeu ministériel ; l’avis d’attribution {ev['noticeId']} (réf. {ev['contractReference']}) et le flux de l’acheteur ne nomment que {', '.join(ev['confirmed'])}."} for x in moved]
        r["verification"]["holdersUnconfirmed"]=True
        applied.append({"id":r["id"],"confirmed":ev["confirmed"],"unconfirmed":[x["id"] for x in moved],"noticeId":ev["noticeId"]})
    return applied

def apply_feeds(rows, snapshot):
    """Buyer-feed amounts, verification status and contracts missing from the Ministry snapshot."""
    import decp_feeds
    feed=decp_feeds.load(portals=decp_feeds.PORTALS)
    cpv=decp_feeds.cpv_lookup(rows)
    text=decp_feeds.source_text(feed)
    names={s:n for s,n,_ in BUYERS}
    def build(contract, in_use):
        r=contract["initial"]; buyer=r["acheteur_id"]
        rec=decp_feeds.feed_fields(contract, cpv, direct)
        portal=next((x for x in feed.get("portals") or [] if r["sourceDataset"].startswith("portal_") and x["label"].startswith(r["sourceDataset"][7:])), None)
        where=({"source":portal["dataset_page"],"sourceLabel":"Liste open data des marchés conclus, publiée par l’acheteur"} if portal else text)
        rec.update({"id":decp_feeds.new_id(buyer, r["id"], in_use),"buyer":names[buyer],"buyerSiret":buyer,"cohortId":COHORT,**where,
            "sourceReference":f"SIRET acheteur {buyer} ; identifiant {r['id']} ; flux {r['sourceDataset']} (uid {r['uid']}). Absent du jeu ministériel au {snapshot}.",
            "amountBasis":"Montant initial déclaré dans le flux de l’acheteur ; une modification est un nouveau montant total, jamais additionné.",
            "dateNote":"Date de notification initiale ; fenêtre 2024–2025.","notes":("Marché présent dans la liste open data de l’acheteur mais absent du jeu ministériel et des flux DECP : source unique, non vérifiée par une seconde source. Pour Nantes, les accords-cadres y sont indiqués à leur montant maximum." if portal else "Marché présent dans le flux de publication de l’acheteur mais absent du jeu ministériel : source unique, non vérifiée par une seconde source."),
            "sourceRowVariants":[]})
        return rec
    added,stats=decp_feeds.apply(rows, feed, set(names), build, COHORT)
    return rows+added, {"file":"decp-feeds-raw.json.gz","tool":"tools/decp_feeds.py","feedSource":feed["source"],"portals":feed.get("portals"),"statistics":stats,
        "rules":decp_feeds.__doc__.strip()}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--offline",action="store_true"); args=ap.parse_args(); root=Path(__file__).resolve().parents[1]; data=root/"data"
    now=datetime.now(timezone.utc).isoformat()
    if args.offline: raw=json.loads((data/"decp-cities-raw.json").read_text()); now=raw.get("retrievedAt",now)
    else:
        records=[]; pages=[]; totals={}
        for siret,name,city in BUYERS:
            w=where(siret); offset=0; total=None
            while True:
                u=url_for({"where":w,"limit":100,"offset":offset,"order_by":"datenotification asc,id asc"}); p=fetch(u); page=p.get("results",[])
                if total is not None and total != p.get('total_count'): raise RuntimeError('total_count a changé pendant la pagination ; recommencer.')
                total=p['total_count']
                records.extend(page); pages.append({"url":u,"buyerSiret":siret,"offset":offset,"count":len(page),"total":total,"retrievedAt":datetime.now(timezone.utc).isoformat()})
                if offset+len(page)>=total: break
                if not page: raise RuntimeError("pagination vide avant total_count")
                offset += len(page)
            if offset+len(page) != total: raise RuntimeError('Comptage de pagination incohérent.')
            totals[siret]=total
        lookups=[]
        for siret,name,city in BUYERS:
            lu=LOOKUP+"?"+urllib.parse.urlencode({"q":siret,"per_page":25})
            payload=fetch(lu)
            matches=[{"nom_complet":x.get("nom_complet"),"siret":x.get("siege",{}).get("siret"),"adresse":x.get("siege",{}).get("adresse")} for x in payload.get("results",[]) if x.get("siege",{}).get("siret")==siret]
            if not any(x.get("nom_complet")==name.upper() and x.get("siret")==siret for x in matches): raise RuntimeError(f"acheteur non vérifié par SIRET: {siret}")
            lookups.append({"url":lu,"requestedSiret":siret,"matches":matches})
        raw={"source":API,"retrievedAt":now,"records":records,"queries":pages,"totals":totals,"buyerLookups":lookups,"fieldSchema":"DECP arrêté 2022, dataset decp-2022-marches-valides; units: montant EUR, dureemois months, dates ISO calendar; one row may be initial or modification."}
        (data/"decp-cities-raw.json").write_text(json.dumps(raw,ensure_ascii=False,indent=2)+"\n")
    coverage={"schemaVersion":"2.0","title":"Cohorte DECP — six communes, notifications 2024–2025","source":{"dataset":"decp-2022-marches-valides","api":API,"metadata":"https://data.economie.gouv.fr/explore/dataset/decp-2022-marches-valides/","schemaSource":"https://github.com/139bercy/decp-arr2022/blob/main/schemes/schema_decp_v2.0.4.json","queries":raw.get("queries",[]),"buyerLookups":[LOOKUP+"?"+urllib.parse.urlencode({"q":s,"per_page":25}) for s,_,_ in BUYERS]},"scope":{"cohortId":COHORT,"buyers":[{"siret":s,"name":n,"city":c} for s,n,c in BUYERS],"notificationFrom":FROM,"notificationTo":"2025-12-31","selection":"Six city communes preselected by geography (six distinct French regional cities) and public purchasing size before any score or indicator calculation; exact commune SIRETs, not métropoles.","rationale":"Diversified metropolitan geography and a manageable range of published purchasing volumes; exploratory, not representative. No score-based selection."},"downloadedAt":now,"counts":{"rawRows":len(raw["records"])},"fields":{"amount":"montant, EUR declared total","offers":"offresrecues, integer text; CDL/INX unknown","date":"datenotification, initial notification date","durationMonths":"dureemois, months","cpv":"codecpv, 8-digit CPV with check digit","supplierIds":"titulaire_id_1..3 + titulaire_typeidentifiant_1..3; modification identifiers in idtitulairemodification","modificationId":"idmodification","modificationAmount":"montantmodification, new declared total in EUR","modificationNotificationDate":"datenotificationmodificationmodification"},"modificationSemantics":"Official schema v2.0.4 calls Modification.montant a Nouveau montant; retained as a revised total, never summed with the initial amount. Multiple published modification rows are retained in history.","retrieval":{"pageSize":100,"orderBy":"datenotification asc,id asc","pagination":"each city paged through total_count; raw records include all pages"},"mapping":{"unit":"one normalized row per distinct contract: buyer SIRET + DECP id + declared initial fields (see mapping.conflicts); no amount sums. Groups in decp-cities-curated.json use notice-linked lot rows","conflicts":"all differing initial field values are null in the normalized row, with initialConflicts and initialAlternatives; conflicting groups excluded from retrospective calculations by script.js","duplicates":"identical raw rows deduplicated only; distinct modification versions preserved","sources":"each normalized source URL filters exact buyer SIRET and exact contract id"},"limitations":["DECP valid dataset publication is not proof of legal regularity or payment.","No names inferred for suppliers; identifiers and their published type are preserved.","The API may expose only indexed/latest modifications; absence of a published modification does NOT prove absence of a real amendment.","No UI changes and no cross-source joins."],"buyerVerification":raw.get("buyerLookups",[]),"mappingSelectedBuyerVerification":"Buyer SIRETs verified by exact SIRET results in Recherche entreprises; Grenoble and Dijon are communes, not Grenoble-Alpes-Métropole or Dijon Métropole."}
    coverage["procedureMapping"]={"observed":sorted({r.get("procedure") for r in raw["records"] if r.get("procedure")}),"direct":sorted(PROCEDURE_DIRECT),"competitive":sorted(PROCEDURE_COMPETITIVE),"unknown":"Any other label maps to null; exact labels only."}
    coverage["limitations"].append("Absence de modification publiée ne prouve PAS l’absence d’un avenant ou d’une modification réelle.")
    for s, _, _ in BUYERS:
        if sum(r.get('acheteur_id') == s for r in raw['records']) != raw['totals'][s]: raise ValueError('Brut incomplet pour '+s)
    curated_file=data/"decp-cities-curated.json"
    curated=json.loads(curated_file.read_text()) if curated_file.exists() else None
    rows=normalize(raw, data, coverage, curated)
    rows,coverage["feedReconciliation"]=apply_feeds(rows, (raw.get("retrievedAt") or "")[:10])
    coverage["holderEvidence"]=apply_holder_evidence(rows, curated or {})
    coverage["counts"]["contracts"]=len(rows); coverage["counts"]["contractsAddedFromFeeds"]=sum(bool(r["verification"].get("addedFromFeed")) for r in rows)
    identity_file = data / 'supplier-identities.json'
    profiles = {}
    if identity_file.exists():
        for p in json.loads(identity_file.read_text())['identities']:
            if (p.get('status') == 'available' and p.get('diffusionStatus') == 'O' and
                re.fullmatch(r'\d{9}', p.get('siren', '')) and isinstance(p.get('name'), str) and p['name'].strip() and
                p.get('source') == LOOKUP+'?'+urllib.parse.urlencode({'q':p['siren'],'per_page':25})):
                profiles[p['siren']] = {k:p.get(k) for k in ['siren','name','administrativeState','diffusionStatus','source','retrievedAt','status']}
        for row in rows:
            sirens = {s.get('siren') for s in row['supplierIds'] or []}
            row['supplierProfiles'] = [profiles[s] for s in sorted(sirens - {None}) if s in profiles]
    coverage['identityEnrichment'] = {'snapshot':'supplier-identities.json','coverage':'supplier-identities-coverage.json',
        'contractsWithCurrentNames':sum(bool(r.get('supplierProfiles')) for r in rows), 'availableSirens':len(profiles),
        'historicalNamesVerified':False,'matching':'SIREN derived only from typed French SIRET/SIREN; names do not replace published contract identifiers.'}
    coverage['limitations'] = [s for s in coverage['limitations'] if s != 'No UI changes and no cross-source joins.']
    coverage['limitations'].extend(['Offset pagination is checked against total_count but the API provides no immutable snapshot; tied ordering and subsequent corrections can affect completeness.',
        'The DECP id is often not a contract identifier for these buyers (truncated by the AWS export, or a platform counter): rows sharing buyer+id whose declared fields differ are published as separate contracts linked by procedureGroup; no identifier is invented (research/decp-identifier-collisions.md).',
        'Rows with the same holder, object, notification date and framework but a different amount may be one contract published twice: flagged possibleDuplicateOf, scored individually and counted once in buyer-level baselines.',
        'Current public company names are an identity context only, not historical names, establishment status, relationship evidence or scoring inputs.'])
    coverage['mapping']['conflicts'] = 'Rows of one buyer+id are one contract only when all declared initial fields agree (modification rows repeat them); otherwise each distinct set is its own contract, linked by procedureGroup. A group differing only in holders with a declared joint grouping is one joint contract. Any remaining differing initial values would become null and the contract excluded. Raw rows remain available.'
    coverage['counts']['contractsWithPublishedModifications'] = sum(len(r['history']) > 1 for r in rows)
    coverage['counts']['ambiguousGroupsExcluded'] = sum(bool(r['initialConflicts'] or r['modificationConflicts']) for r in rows)
    coverage['curation'] = {'file':'decp-cities-curated.json','tool':'tools/reconcile-dijon-project.py',
        'splitGroups':len((curated or {}).get('procedureSplits',[])),'rowsFromSplits':sum(bool(r.get('procedureGroup')) for r in rows),
        'offerConflicts':sum(bool(r.get('offersConflict')) for r in rows),'projectRows':sum(bool(r.get('project')) for r in rows),
        'rule':'Only exact buyer+identifier groups whose every source row is linked to one award-notice lot (amount, date, contract reference, register-verified holder) or is an evidently distinct contract are split. Disagreeing offer counts become null with both values retained.'}
    coverage['fieldAvailability'] = {key:sum(r[key] is not None for r in rows) for key in ['amount','offers','date','durationMonths','cpv','directAward']}
    (data/"decp-cities.json").write_text(json.dumps(rows,ensure_ascii=False,indent=2)+"\n")
    coverage["counts"].update({"rawRows":len(raw["records"]),"normalizedRows":len(rows),"rawRowsByBuyer":{s:sum(r.get("acheteur_id")==s for r in raw["records"]) for s,_,_ in BUYERS},"contractsByBuyer":{s:sum(r["buyerSiret"]==s for r in rows) for s,_,_ in BUYERS}})
    # Keep sections written by later tools or by hand (historical rules, verification, index pointers).
    previous=data/"decp-cities-coverage.json"
    if previous.exists():
        for key,value in json.loads(previous.read_text()).items(): coverage.setdefault(key,value)
    (data/"decp-cities-coverage.json").write_text(json.dumps(coverage,ensure_ascii=False,indent=2)+"\n")
if __name__=="__main__": main()
