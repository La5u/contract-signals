#!/usr/bin/env python3
"""Tours full-notice cohort. Stdlib offline preparation, not a site dependency.
Online: BOAMP cohort + exact procedure/reference discovery. TED is downloaded by
 tools/download-tours-ted.py. --offline never changes saved retrieval provenance.
"""
import argparse
import hashlib
import json
import math
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/tours-notices/raw'
API = 'https://www.boamp.fr/api/explore/v2.1/catalog/datasets/boamp/records'
SIRET = '21370261600011'
WHERE = "dateparution >= date'2025-01-01' AND dateparution < date'2026-01-01' AND donnees LIKE '%21370261600011%'"
UUID = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I)


def array(v): return v if isinstance(v, list) else [] if v is None else [v]
def text(v):
    if isinstance(v, dict): return v.get('#text')
    return str(v) if v is not None else None

def get(d, *keys):
    for k in keys:
        if not isinstance(d, dict): return None
        d = d.get(k)
    return d

def value(d, *keys): return text(get(d, *keys))
def walk(d, path=''):
    if isinstance(d, dict):
        for k, v in d.items():
            p = path+'/'+k
            yield p, k, v
            yield from walk(v, p)
    elif isinstance(d, list):
        for i, v in enumerate(d): yield from walk(v, path+f'[{i}]')

def root_notice(record):
    try:
        data = json.loads(record.get('donnees') or '{}').get('EFORMS', {})
        roots = [(k, v) for k, v in data.items() if isinstance(v, dict) and value(v, 'cbc:ID')]
        return roots[0] if len(roots) == 1 else (None, {})
    except (ValueError, TypeError): return None, {}

def buyers(root):
    orgs = {}
    for _, key, v in walk(root):
        if key != 'efac:Company' or not isinstance(v, dict): continue
        oid = value(v, 'cac:PartyIdentification', 'cbc:ID')
        entry = {'id': oid, 'siret': re.sub(r'\s+', '', value(v, 'cac:PartyLegalEntity', 'cbc:CompanyID') or ''),
                 'name': value(v, 'cac:PartyName', 'cbc:Name')}
        orgs.setdefault(oid, []).append(entry)
    result = []
    for party in array(root.get('cac:ContractingParty')):
        oid = value(party, 'cac:Party', 'cac:PartyIdentification', 'cbc:ID')
        matches = orgs.get(oid, [])
        if len(matches) == 1: result.append(matches[0])
    return result

def finite(v):
    try:
        n = float(text(v))
        return n if math.isfinite(n) and n >= 0 else None
    except (ValueError, TypeError): return None

def boolean(v): return {'true': True, 'false': False}.get(text(v))
def safe_url(v):
    return v.strip() if isinstance(v, str) and urllib.parse.urlparse(v.strip()).scheme in ('https', 'http') else None

def deadline(lot):
    d = get(lot, 'cac:TenderingProcess', 'cac:TenderSubmissionDeadlinePeriod') or {}
    day, time = value(d, 'cbc:EndDate'), value(d, 'cbc:EndTime')
    iso = None
    if day and time and re.fullmatch(r'\d{4}-\d{2}-\d{2}(?:Z|[+-]\d{2}:\d{2})?', day) and re.fullmatch(r'\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})', time):
        candidate = day[:10]+'T'+time
        try:
            datetime.fromisoformat(candidate.replace('Z', '+00:00'))
            if len(day) == 10 or day[10:] == time[8:]: iso = candidate
        except ValueError: pass
    return {'date': day, 'time': time, 'iso': iso}

def procedure(root, source):
    p = root.get('cac:TenderingProcess') or {}
    reasons = []
    accelerated = []
    for n, j in enumerate(array(p.get('cac:ProcessJustification'))):
        code_node = j.get('cbc:ProcessReasonCode')
        category = code_node.get('@listName') if isinstance(code_node, dict) else None
        if category == 'accelerated-procedure': accelerated.append(boolean(code_node))
        reasons.append({'code':text(code_node), 'category':category,
                        'text':value(j, 'cbc:Description'), 'scope':'procedure',
                        'path':f'cac:TenderingProcess/cac:ProcessJustification[{n}]', 'source':source})
    accel = accelerated[0] if accelerated and len(set(accelerated)) == 1 else None
    return {'type':value(p, 'cbc:ProcedureCode'), 'description':value(p, 'cbc:Description'),
            'accelerated':accel, 'justifications':reasons,
            'relaunch': next((boolean(v) for _, k, v in walk(p) if k == 'efbc:ProcedureRelaunchIndicator'), None)}

def award_criteria(lot, lid, source):
    # Only AwardingTerms in THIS lot, never SelectionCriteria or another lot.
    terms = get(lot, 'cac:TenderingTerms', 'cac:AwardingTerms') or {}
    out = []
    def visit(node, path):
        for i, criterion in enumerate(array(node)):
            p = path+f'[{i}]'
            criterion_type = value(criterion, 'cbc:AwardingCriterionTypeCode')
            description = value(criterion, 'cbc:Description')
            name = value(criterion, 'cbc:Name')
            formula = value(criterion, 'cbc:CalculationExpression')
            if criterion_type or description or name or formula:
                params = []
                # Do not pull parameters from nested subordinate criteria.
                for subpath, key, parameter in walk(criterion.get('ext:UBLExtensions') or {}):
                    if key != 'efac:AwardCriterionParameter': continue
                    for par in array(parameter):
                        code = get(par, 'efbc:ParameterCode')
                        params.append({'code':text(code), 'codeList':code.get('@listName') if isinstance(code, dict) else None,
                                       'rawValue':value(par, 'efbc:ParameterNumeric'), 'value':finite(get(par, 'efbc:ParameterNumeric'))})
                out.append({'lotId':lid, 'type':criterion_type, 'name':name, 'description':description,
                            'formula':formula, 'parameters':params, 'source':source, 'path':p})
            visit(criterion.get('cac:SubordinateAwardingCriterion'), p+'/cac:SubordinateAwardingCriterion')
    visit(terms.get('cac:AwardingCriterion'), 'cac:ProcurementProjectLot['+str(lid)+']/cac:TenderingTerms/cac:AwardingTerms/cac:AwardingCriterion')
    return out

def references(root):
    refs = []
    for path, k, v in walk(root):
        if k == 'efbc:ChangedNoticeIdentifier': refs.append({'kind':'correction-of','id':text(v),'path':path})
        if k == 'cac:NoticeDocumentReference':
            for x in array(v):
                if value(x, 'cbc:ID'): refs.append({'kind':'previous-notice','id':value(x,'cbc:ID'),'path':path})
    return refs

def xml_local(e): return e.tag.rsplit('}',1)[-1]
def xml_value(e, name):
    return next((x.text for x in e if xml_local(x) == name), None)

def ted_evidence(root, lid, downloads):
    uuid, version = value(root, 'cbc:ID'), value(root, 'cbc:VersionID')
    out=[]
    for item in downloads:
        if not item.get('verified') or item.get('actual_uuid') != uuid: continue
        path = ROOT / item['file']
        doc = ET.parse(path).getroot()
        notice = next((e for e in doc.iter() if xml_local(e) in ('ContractNotice','ContractAwardNotice','ConcessionNotice') and xml_value(e, 'ID') == uuid), None)
        if notice is None: continue
        # A matching UUID alone is not enough to equate two notice versions.
        ted_version = xml_value(notice, 'VersionID')
        lot = next((e for e in notice if xml_local(e) == 'ProcurementProjectLot' and xml_value(e,'ID') == lid), None)
        period = next((e for e in lot.iter() if xml_local(e)=='TenderSubmissionDeadlinePeriod'), None) if lot is not None else None
        day = xml_value(period, 'EndDate') if period is not None else None
        time = xml_value(period, 'EndTime') if period is not None else None
        out.append({'noticeUuid':uuid,'version':ted_version,'versionMatches':ted_version==version,'lotId':lid if lot is not None else None,
                    'publicationNumber':item['publication_number'], 'publicationDate':(item.get('ted_publication_date') or '')[:10] or None,
                    'deadlineDate':day,'deadlineTime':time,'source':item['url'],'localFile':item['file'],'retrievedAt':item.get('retrieved_at')})
    return out

def normalize(records, manifest, ted_manifest):
    qualified=[]; excluded=[]
    for record in records:
        kind, root = root_notice(record)
        bs = buyers(root)
        if not any(b['siret']==SIRET for b in bs):
            excluded.append({'noticeId':record['idweb'],'reason':'SIRET absent du rôle acheteur résolu (ou structure non prise en charge)','resolvedBuyers':bs})
        else: qualified.append((record, root, bs))
    by_reference={}
    for r, root, _ in qualified:
        for ref in [r['idweb'],value(root,'cbc:ID'),f"{value(root,'cbc:ID')}-{value(root,'cbc:VersionID')}"]:
            by_reference.setdefault(ref, []).append(r['idweb'])
    rows=[]
    for record, root, bs in qualified:
        rid=record['idweb']; source=record.get('url_avis') or 'https://www.boamp.fr/pages/avis/?q=idweb:'+rid
        refs=references(root); proc=procedure(root,source); uuid=value(root,'cbc:ID'); version=value(root,'cbc:VersionID')
        changed=any(ref['kind']=='correction-of' for ref in refs)
        nature='correction' if changed else 'award' if record.get('nature')=='ATTRIBUTION' else 'initial'
        linked=[]
        for ref in refs:
            targets=by_reference.get(ref['id'],[])
            legacy = next((t for t in ted_manifest.get('downloads',[]) if t.get('verified') and t.get('publication_number') == ref['id']), None)
            linked.append({**ref,'matchedNoticeIds':targets if len(targets)==1 else [],'ambiguous':len(targets)>1,
                           'tedSource':legacy.get('url') if legacy else None})
        for lot in array(root.get('cac:ProcurementProjectLot')) or [{}]:
            lid=value(lot,'cbc:ID'); project=lot.get('cac:ProcurementProject') or {}
            dl=deadline(lot); ted=ted_evidence(root,lid,ted_manifest.get('downloads',[]))
            criteria=award_criteria(lot,lid,source)
            docs=[]
            for path,k,v in walk(get(lot,'cac:TenderingTerms','cac:CallForTendersDocumentReference') or {}):
                if k=='cbc:URI' and safe_url(text(v)): docs.append({'url':safe_url(text(v)),'path':path,'downloaded':False})
            explanation=['Chaîne complète des versions TED et publication initiale pertinente non certifiées : aucun score de délai.']
            if changed: explanation.append('Rectificatif identifié par ChangedNoticeIdentifier, malgré etat=INITIAL dans l’index BOAMP.')
            if proc['relaunch'] is True: explanation.append('Relance déclarée : l’historique antérieur reste à examiner.')
            if proc['accelerated'] is None: explanation.append('Accélération non renseignée explicitement.')
            if not dl['iso']: explanation.append('Échéance d’offre exploitable absente ; une date de candidature n’est pas substituée.')
            deadline_conflict=any(t['versionMatches'] and (t['deadlineDate']!=dl['date'] or t['deadlineTime']!=dl['time']) for t in ted)
            if deadline_conflict: explanation.append('Horaires/fuseaux BOAMP et TED divergents pour la même version : aucune sélection arbitraire.')
            ev={'noticeId':rid,'noticeUuid':uuid,'version':version,'kind':nature,'lotId':lid,'lotReference':value(project,'cbc:ID'),
                'procedureId':value(root,'cbc:ContractFolderID'),'procedureReference':value(root,'cac:ProcurementProject','cbc:ID'),
                'procedureType':proc['type'],'procedureDescription':proc['description'],'accelerated':proc['accelerated'],'relaunch':proc['relaunch'],
                'legalBasis':value(root,'cbc:RegulatoryDomain'),'justifications':proc['justifications'],
                'awardCriteria':criteria,'documents':docs,'references':linked,'buyers':bs,
                'publicationDate':record.get('dateparution'),'dispatchDate':value(root,'cbc:IssueDate'),'dispatchTime':value(root,'cbc:IssueTime'),
                'deadline':dl,'ted':ted,'deadlineConflict':deadline_conflict,
                'source':source,'sourcePath':'EFORMS/'+root_notice(record)[0],
                'inPublicationWindow':'2025-01-01'<=record.get('dateparution','')<'2026-01-01'}
            # Discovery by procedure UUID is contextual, not proof of an award-to-lot match.
            ev['sameProcedureNotices']=[{'id':r['idweb'],'source':r.get('url_avis'),'basis':'même UUID de procédure, pas une preuve d’attribution au lot'} for r,rr,_ in qualified if r['idweb']!=rid and value(rr,'cbc:ContractFolderID')==ev['procedureId']]
            row={'id':f'tours-notice-{rid}-{lid or "unknown-lot"}','buyer':'Ville de Tours'+(' · achat conjoint' if len(bs)>1 else ''),
                 'buyerSiret':SIRET,'description':value(project,'cbc:Name') or record.get('objet') or 'Objet inconnu',
                 'supplier':None,'supplierIds':None,'amount':None,'date':None,'offers':None,'durationMonths':None,'directAward':None,
                 'officialFinding':None,'dataStatus':'verified','dataFamily':'boamp','cohortId':'tours-full-notices-2025',
                 'procedure':proc['type'],'cpv':value(project,'cac:MainCommodityClassification','cbc:ItemClassificationCode'),
                 'noticeId':rid,'lotId':lid,'contractFolderId':ev['procedureId'],'publicationDate':record.get('dateparution'),
                 'source':source,'sourceLabel':'Avis BOAMP complet — texte déclaré par l’acheteur',
                 'notes':'Unité : version d’avis + lot, pas marché attribué unique. Pas de somme financière, pas de transfert de constat ni de justification entre lots.',
                 'noticeEvidence':ev,
                 'consultation':{'procedureId':ev['procedureId'],'procedureReference':ev['procedureReference'],'lotId':lid,
                     'initialNoticeId':rid if nature=='initial' else None,'searchComplete':False,'exclusions':explanation,
                     'notices':[{'id':rid,'noticeIdentifier':uuid,'version':version,'kind':nature,'publicationDate':record.get('dateparution'),
                         'publicationState':record.get('etat'),'deadline':dl['iso'],'procedureType':proc['type'],'accelerated':proc['accelerated'],
                         'source':source,'previousNoticeIds':[i for x in linked for i in x['matchedNoticeIds']]}],'matchedAwards':[]}}
            rows.append(row)
    by_notice_lot = {(r['noticeId'], r['lotId']):r for r in rows}
    for r in rows: r['noticeEvidence']['linkedNoticeLots'] = []
    links = set()
    for r in rows:
        e = r['noticeEvidence']
        for ref in e['references']:
            for notice_id in ref['matchedNoticeIds']:
                previous = by_notice_lot.get((notice_id, r['lotId']))
                if previous and previous['contractFolderId'] == r['contractFolderId'] and previous['id'] != r['id']:
                    links.add((previous['id'], r['id'], ref['kind']))
                    for owner, target, direction in [(r, previous, ref['kind']), (previous, r, 'referenced-by')]:
                        te = target['noticeEvidence']
                        owner['noticeEvidence']['linkedNoticeLots'].append({'noticeId':target['noticeId'],'lotId':target['lotId'],
                            'version':te['version'],'kind':te['kind'],'publicationDate':te['publicationDate'],
                            'deadline':te['deadline']['iso'],'source':te['source'],'relation':direction,
                            'basis':'Référence explicite d’avis + même UUID de procédure + même identifiant de lot. Pas de transfert de montant ou de titulaire.'})
    ids=[r['id'] for r in rows]
    if len(ids)!=len(set(ids)): raise ValueError('Identifiant avis/lot dupliqué ou versions contradictoires : import à examiner.')
    coverage={'retrievedAt':manifest['retrievedAt'],'source':API,'scope':{'buyerSiret':SIRET,'publicationFrom':'2025-01-01','publicationTo':'2025-12-31','where':WHERE,
        'selection':'Commune de Tours choisie avant examen des scores ; tous les candidats exact-SIRET indexés, puis vérification du rôle acheteur. Achats conjoints explicitement étiquetés. Liens hors période conservés.'},
        'queries':manifest['queries'],'counts':{'apiCandidates':next((q.get('total') for q in manifest['queries'] if q.get('total') is not None),None),
            'rawBoampNotices':len(records),'buyerQualifiedNotices':len(qualified),'excludedBuyerNotices':len(excluded),'noticeLotRows':len(rows),
            'qualifiedNoticesIn2025':sum('2025-01-01'<=r.get('dateparution','')<'2026-01-01' for r,_,_ in qualified),
            'correctionNotices':len(set(r['noticeId'] for r in rows if r['noticeEvidence']['kind']=='correction')),
            'rowsWithCriteria':sum(bool(r['noticeEvidence']['awardCriteria']) for r in rows),
            'awardCriteriaEntries':sum(len(r['noticeEvidence']['awardCriteria']) for r in rows),
            'rowsWithNumericCriterionParameters':sum(any(a['parameters'] for a in r['noticeEvidence']['awardCriteria']) for r in rows),
            'rowsWithProcedureDescription':sum(bool(r['noticeEvidence']['procedureDescription']) for r in rows),
            'rowsWithTedXml':sum(bool(r['noticeEvidence']['ted']) for r in rows),
            'rowsWithDeadlineConflict':sum(r['noticeEvidence']['deadlineConflict'] for r in rows),
            'evaluableBiddingPeriods':0,'triggeredBiddingPeriods':0,'explicitNoticeLotLinks':len(links)}, 
        'excludedBuyerNotices':excluded,'tedManifest':'data/tours-notices/raw/ted-manifest.json',
        'tedDownloads':len(ted_manifest.get('downloads',[])),
        'tedQualifiedNoticeMatches':len(set(r['noticeId'] for r in rows if r['noticeEvidence']['ted'])),
        'tedRetrievalStartedAt':ted_manifest.get('created_at'),
        'tedLastRecordedDownloadAt':max((x.get('retrieved_at','') for x in ted_manifest.get('downloads',[])),default=None),
        'scoring':'Documents without an evaluable chronology display Non évalué, not a claim of no suspicion. No extra points for criteria or legal justification.',
        'verificationCommands':['node tests/tours.cjs','node tests/rules.cjs','node tests/cities.cjs','python -m unittest discover -s tests -p test_*.py','node tests/browser.cjs'],
        'mapping':{'unit':'notice version + lot, not unique contracts or spending',
            'justification':'Exact ProcessJustification code/list/text and procedure Description with procedure-wide scope; no inferred direct award for any lot.',
            'criteria':'Only lot-local TenderingTerms/AwardingTerms, nested criterion structure paths preserved. SelectionCriteria excluded. Numeric parameter codes/raw values preserved, not assumed percentages.',
            'links':'Explicit ChangedNoticeIdentifier / NoticeDocumentReference; same procedure UUID discovery labelled separately. No DECP join.',
            'publication':'BOAMP dateparution and TED wrapper publication date; dispatch IssueDate/Time separate.',
            'deadlines':'Lot TenderSubmissionDeadlinePeriod only; original dates and timezone strings retained separately for BOAMP and TED.',
            'buyer':'ContractingParty/Party/PartyIdentification -> matching Organizations/Company/PartyLegalEntity/CompanyID; supplier/name-only matches excluded.'},
        'limitations':['Exact text SIRET search may miss notices with another establishment identifier, spacing or unindexed formats; not all purchases of Tours.',
            'TED candidate discovery by name/date is not matching evidence: each XML association requires exact root notice UUID and records its version.',
            'The TED search is not a complete procedure-version audit; no bidding score enabled. Conflicting timezone declarations remain visible.',
            'RegulatoryDomain is a directive/legal framework, not proof of an R2122 exception. A procedure-wide explanation may concern lots outside the present notice.',
            'Award criteria are context only; unspecified weights remain unknown. No buyer portal documents downloaded, only their published links.',
            'Sources can themselves be inaccurate. No finding of irregularity, historical DECP join or payment total inferred.']}
    return rows, coverage


def fetch_pages(where, purpose, queries):
    records=[]; offset=0; expected=None
    while True:
        url=API+'?'+urllib.parse.urlencode({'where':where,'limit':100,'offset':offset,'order_by':'dateparution ASC, idweb ASC'})
        at=datetime.now(timezone.utc).isoformat()
        with urllib.request.urlopen(url,timeout=90) as response: payload=json.load(response)
        total=payload['total_count']; page=payload['results']
        if expected is not None and expected!=total: raise ValueError('Changing API total; retry complete extraction.')
        expected=total; queries.append({'url':url,'purpose':purpose,'count':len(page),'total':total,'retrievedAt':at})
        records.extend(page); offset+=len(page)
        if offset==total: return records
        if not page or offset>total: raise ValueError('Incomplete pagination.')


def main():
    p=argparse.ArgumentParser();p.add_argument('--offline',action='store_true');args=p.parse_args();RAW.mkdir(parents=True,exist_ok=True)
    if args.offline:
        records=json.loads((RAW/'api-records.json').read_text());manifest=json.loads((RAW/'manifest.json').read_text())
    else:
        queries=[];at=datetime.now(timezone.utc).isoformat();records=fetch_pages(WHERE,'full exact-SIRET cohort candidates',queries)
        processed=set();seen={json.dumps(r,sort_keys=True) for r in records}
        for record in records:
            _,root=root_notice(record)
            # Forward links and exact procedure identifiers; no name-based association.
            searches=[('annonce_lie',record['idweb'])]
            if value(root,'cbc:ContractFolderID'): searches.append(('contractfolderid',value(root,'cbc:ContractFolderID')))
            for ref in references(root):
                if UUID.match((ref['id'] or '')[:36]): searches.append(('uuid',ref['id'][:36]))
            for field,val in searches:
                if (field,val) in processed: continue
                processed.add((field,val)); escaped=val.replace("'","''")
                query=f"donnees LIKE '%{escaped}%'" if field=='uuid' else f"{field} = '{escaped}'"
                for r in fetch_pages(query,'exact reference discovery '+field,queries):
                    signature=json.dumps(r,sort_keys=True)
                    if signature not in seen: seen.add(signature);records.append(r)
            if len(records)>500: raise ValueError('Related-notice discovery exceeded safety limit; review cohort without publishing partial output.')
        manifest={'source':API,'retrievedAt':at,'query':WHERE,'records':len(records),'queries':queries}
        (RAW/'api-records.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
        (RAW/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    ted_path=RAW/'ted-manifest.json';ted=json.loads(ted_path.read_text()) if ted_path.exists() else {}
    rows,coverage=normalize(records,manifest,ted)
    (ROOT/'data/tours-notices.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
    (ROOT/'data/tours-notices-coverage.json').write_text(json.dumps(coverage,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(coverage['counts'],ensure_ascii=False))

if __name__=='__main__':main()
