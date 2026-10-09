#!/usr/bin/env python3
"""Project-wide reconciliation: Dijon "Maison des Associations" DECP rows versus BOAMP awards.

Every DECP source row whose object names the project is paired with an award
notice lot result only on an exact amount + date match that is unique across
the project's notices. Holder linkage requires the exact DECP SIRET in the
official register, with name tokens and postcode agreeing with that lot's
winner. Offer counts are compared, never chosen. Default is offline;
--fetch performs the frozen register/Ministry requests once.
--write-curated emits data/decp-cities-curated.json from linked evidence only.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
CACHE = Path.home() / '.cache/contract-signals/decp-conflict-dijon'
BUYER = '21210231300013'
PROJECT = {'id': 'dijon-maison-des-associations', 'match': 'maison des associations'}
MINISTRY = 'https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/decp-2022-marches-valides/records'
NOTICE_URL = 'https://www.boamp.fr/pages/avis/?q=idweb:'
CALLS = ('23-176628', '24-41255', '24-41260', '24-41263')  # calls for tender of the procedure and its relaunches


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


rec = load('dijon_reconcile', 'tools/reconcile-dijon-conflict.py')
holders = load('dijon_holders', 'tools/link-dijon-holders.py')
T = rec.text


def eforms_results(record):
    """All awarded lot results of one eForms award notice, following explicit references only."""
    notice = json.loads(record['donnees'])['EFORMS']['ContractAwardNotice']
    ext = notice['ext:UBLExtensions']['ext:UBLExtension']['ext:ExtensionContent']['efext:EformsExtension']
    nr = ext['efac:NoticeResult']
    orgs = rec.unique(ext['efac:Organizations']['efac:Organization'], lambda x: x['efac:Company']['cac:PartyIdentification']['cbc:ID'])
    lots = rec.unique(notice['cac:ProcurementProjectLot'], lambda x: x['cbc:ID'])
    tenders = rec.unique(nr.get('efac:LotTender'), lambda x: x['cbc:ID'])
    contracts = rec.unique(nr.get('efac:SettledContract'), lambda x: x['cbc:ID'])
    parties = rec.unique(nr.get('efac:TenderingParty'), lambda x: x['cbc:ID'])
    out = []
    for lr in rec.many(nr['efac:LotResult']):
        if not lr.get('efac:LotTender'):
            continue
        if isinstance(lr['efac:LotTender'], list) or isinstance(lr.get('efac:SettledContract'), list) or not lr.get('efac:SettledContract'):
            raise ValueError('Multiple or missing winning references; not resolved')
        lid = T(lr['efac:TenderLot']['cbc:ID'])
        tender = tenders[T(lr['efac:LotTender']['cbc:ID'])]
        contract = contracts[T(lr['efac:SettledContract']['cbc:ID'])]
        if T(tender['efac:TenderLot']['cbc:ID']) != lid or T(contract['efac:LotTender']['cbc:ID']) != T(tender['cbc:ID']):
            raise ValueError('Inconsistent lot/tender/contract relationship')
        party = parties[T(tender['efac:TenderingParty']['cbc:ID'])]
        winners = []
        for ref in rec.many(party['efac:Tenderer']):
            company = orgs[T(ref['cbc:ID'])]['efac:Company']
            winners.append({'name': T(company.get('cac:PartyName', {}).get('cbc:Name')),
                            'postcode': T(company.get('cac:PostalAddress', {}).get('cbc:PostalZone'))})
        node = tender['cac:LegalMonetaryTotal']['cbc:PayableAmount']
        title = T(lots[lid]['cac:ProcurementProject'].get('cbc:Name')) or ''
        # The structured InternalID is wrong in some notices; the lot title is what the buyer printed.
        printed = re.match(r'\s*Lot n°\s*(\d+)', title)
        out.append({'noticeId': record['idweb'], 'technicalLotId': lid, 'lotTitle': title,
                    'lotNumber': printed.group(1) if printed else None,
                    'contractReference': T(contract['efac:ContractReference']['cbc:ID']),
                    'amount': rec.amount(node), 'currency': node.get('@currencyID'),
                    'date': rec.date_component(contract['cbc:IssueDate']), 'offers': rec.offer_total(lr),
                    'winners': winners})
    return out


def simple_results(record):
    """A pre-eForms (FNSimple) award: one free-text attribution block, parsed only if unambiguous."""
    attribution = json.loads(record['donnees'])['FNSimple']['attribution']
    text = attribution['attributionMarche']
    title = attribution['natureMarche']['intitule']
    fields = {'offers': re.findall(r"Nombre d'offres reçues\s*:\s*(\d+)", text),
              'date': re.findall(r"Date d'attribution\s*:\s*(\d{2})/(\d{2})/(\d{2})\b", text),
              'reference': re.findall(r'Marché n°\s*:\s*(\S+)', text),
              'amount': re.findall(r'Montant H[Tt]\s*:\s*([\d\s\u00a0]+(?:,\d+)?)\s*Euros', text),
              'winner': re.findall(r'\n([^,\n]+),[^\n]*?\b(\d{5})\s+\S', text)}
    if any(len(v) != 1 for v in fields.values()):
        raise ValueError('Ambiguous simple attribution; not parsed')
    d, m, y = fields['date'][0]
    printed = re.search(r'lot\s+(\d+)\s*:', title, re.I)
    return [{'noticeId': record['idweb'], 'technicalLotId': None, 'lotTitle': title, 'lotNumber': printed.group(1) if printed else None,
             'contractReference': fields['reference'][0], 'amount': rec.amount(re.sub(r'[\s\u00a0]', '', fields['amount'][0]).replace(',', '.')),
             'currency': 'EUR', 'amountBasis': 'HT', 'date': f'20{y}-{m}-{d}', 'offers': int(fields['offers'][0]),
             'winners': [{'name': fields['winner'][0][0].strip(), 'postcode': fields['winner'][0][1]}]}]


def in_project(row):
    return row.get('acheteur_id') == BUYER and PROJECT['match'] in (row.get('objet') or '').lower()


def project_rows(raw):
    """Project rows plus every row sharing their buyer + identifier, so identifier collisions are visible."""
    ids = {r['id'] for r in raw if in_project(r)}
    return [r for r in raw if r.get('acheteur_id') == BUYER and r.get('id') in ids]


def reconcile(rows, results, responses):
    """One entry per distinct project source row; pairing, holder linkage and offer comparison."""
    entries, seen = [], set()
    for row in rows:
        sig = json.dumps(row, sort_keys=True, ensure_ascii=False)
        if sig in seen:
            continue
        seen.add(sig)
        sirets = holders.holder_sirets([row])
        matches = [x for x in results if x['currency'] == 'EUR' and x['amount'] is not None
                   and x['amount'] == rec.amount(row.get('montant')) and x['date'] == rec.date_component(row.get('datenotification'))]
        offers = row.get('offresrecues')
        offers = int(offers) if re.fullmatch(r'\d+', str(offers)) else None
        entry = {'contractId': row['id'], 'holderSiret': sirets[0], 'amount': rec.amount(row.get('montant')),
                 'date': rec.date_component(row.get('datenotification')), 'decpOffers': offers,
                 'joint': row.get('typegroupementoperateurs') in ('Conjoint', 'Solidaire'), 'inProject': in_project(row),
                 'matches': len(matches)}
        if len(matches) == 1:
            x = matches[0]
            reg = holders.register_entry(responses.get(sirets[0]) or {}, sirets[0]) if sirets[0] else None
            names = [w['name'] for w in x['winners']]
            linked = False
            if reg and reg['sirenMatchesSiret']:
                linked = any(holders.names_agree(w['name'], reg['names']) and w['postcode'] == reg['postcode'] for w in x['winners'])
            entry.update({k: x[k] for k in ['noticeId', 'technicalLotId', 'lotNumber', 'lotTitle', 'contractReference', 'offers']},
                         noticeOffers=x['offers'], holderLinked=linked, registerFound=reg is not None,
                         noticeWinnerCount=len(names),
                         offersDisagree=offers is not None and x['offers'] is not None and offers != x['offers'])
            entry.pop('offers')
        entries.append(entry)
    return entries


def curated(entries, raw_rows, timeline=()):
    """Curated overlay from linked evidence only. Raises rather than curate an unlinked row."""
    by_id = {}
    for e in entries:
        by_id.setdefault(e['contractId'], []).append(e)
    splits, offer_conflicts, unresolved = [], [], []
    for cid, group in sorted(by_id.items()):
        if len(group) > 1:
            lots, problem = [], None
            for e in group:
                if e['matches'] == 1 and e['holderLinked']:
                    lots.append({k: e[k] for k in ['holderSiret', 'amount', 'date', 'lotNumber', 'lotTitle', 'contractReference', 'noticeId']}
                                | {'evidence': 'notice-lot', 'decpOffers': e['decpOffers'], 'noticeOffers': e['noticeOffers']})
                elif e['matches'] == 0 and not e['inProject']:
                    # A different contract that reuses the identifier: kept on its own distinct source row.
                    row = next(r for r in raw_rows if r['id'] == cid and rec.amount(r.get('montant')) == e['amount']
                               and holders.holder_sirets([r])[0] == e['holderSiret'])
                    lots.append({'holderSiret': e['holderSiret'], 'amount': e['amount'], 'date': e['date'], 'lotNumber': None,
                                 'lotTitle': row.get('objet'), 'contractReference': None, 'noticeId': None,
                                 'evidence': 'distinct-source-row', 'decpOffers': e['decpOffers'], 'noticeOffers': None})
                else:
                    problem = 'a source row is not linked to exactly one notice lot and holder'
            if not problem and len({(l['holderSiret'], l['amount'], l['date']) for l in lots}) != len(lots):
                problem = 'split keys not unique'
            if not problem and len({l['contractReference'] for l in lots if l['contractReference']}) != sum(bool(l['contractReference']) for l in lots):
                problem = 'two rows attached to one notice lot'
            if problem and all(e['joint'] for e in group):
                # The importer merges a declared joint grouping into one contract (tools/import-decp-cities.py);
                # the notice-holder mismatch stays documented here.
                entry = {'buyerSiret': BUYER, 'contractId': cid, 'handledAs': 'joint-contract',
                         'reason': 'DECP declares a joint contract (Conjoint) published one row per holder; the award notice names a single winner. Holder set not confirmed by the notice.'}
                linked = sorted({e['holderSiret'] for e in group if e.get('holderLinked')})
                if len(linked) == 1 and len({e.get('noticeId') for e in group}) == 1:
                    # The notice's single winner is register-linked to one Ministry holder; the others are Ministry-only.
                    entry['holderEvidence'] = {'confirmed': linked, 'unconfirmed': sorted({e['holderSiret'] for e in group} - set(linked)),
                                               'noticeId': group[0].get('noticeId'), 'contractReference': group[0].get('contractReference')}
                unresolved.append(entry)
            elif problem:
                unresolved.append({'buyerSiret': BUYER, 'contractId': cid, 'reason': problem})
            else:
                splits.append({'buyerSiret': BUYER, 'contractId': cid, 'lots': lots})
        elif group[0].get('offersDisagree'):
            e = group[0]
            offer_conflicts.append({'buyerSiret': BUYER, 'contractId': cid, 'amount': e['amount'], 'decpOffers': e['decpOffers'],
                                    'noticeOffers': e['noticeOffers'], 'noticeId': e['noticeId'], 'contractReference': e['contractReference']})
    members = sorted({e['contractId'] for e in entries if e['inProject']})
    notices = sorted({e['noticeId'] for e in entries if e.get('noticeId')})
    return {'schemaVersion': '1.0',
            'about': 'Evidence-backed corrections to DECP six-city grouping, produced by tools/reconcile-dijon-project.py. Every entry cites an official notice or the distinct source rows; nothing is summed or chosen between conflicting values.',
            'procedureSplits': splits, 'offerConflicts': offer_conflicts, 'unresolvedGroups': unresolved,
            'projects': [{'id': PROJECT['id'], 'buyerSiret': BUYER, 'contractIds': members,
                          'title': 'Dijon · Maison des Associations · travaux 2024–2025',
                          'basis': ('Rapprochement documentaire : même acheteur et même opération nommée dans chaque objet DECP, rattachés aux avis BOAMP '
                                    "de la procédure initiale (2023VDAO1642) et de ses relances. Ce regroupement ne prouve aucune irrégularité ; les lots "
                                    "sont évalués séparément, sans total financier ni score de projet."),
                          'source': NOTICE_URL + rec.NOTICE, 'evidence': list(timeline)}]}


def fetch(root, sirets, known):
    planned = sorted(set(s for s in sirets if s) - set(known))
    if len(planned) > 25:
        raise ValueError('More holder SIRETs than the frozen request cap')
    holders.fetch(root, planned, cap=25)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence-dir', type=Path, default=CACHE)
    parser.add_argument('--fetch', action='store_true')
    parser.add_argument('--write-curated', action='store_true')
    args = parser.parse_args()
    root = args.evidence_dir.resolve()
    if root == ROOT or ROOT in root.parents:
        parser.error('Private evidence must remain outside repository')
    raw = json.loads((ROOT / 'data/decp-cities-raw.json').read_text())['records']
    rows = project_rows(raw)
    b = json.loads((root / 'official-discovery-20261008/boamp-contract-reference.response').read_text())['results']
    records = [r for r in b if r['idweb'] == rec.NOTICE]
    notice_dir = root / 'project-notices-20261008'
    manifest = json.loads((notice_dir / 'fetch-manifest.json').read_text())
    for e in manifest['entries']:
        body = (notice_dir / e['file']).read_bytes()
        payload = json.loads(body)
        if e.get('status') != 200 or hashlib.sha256(body).hexdigest() != e['sha256'] or payload['total_count'] != 1:
            raise ValueError('Invalid or ambiguous project notice response')
        records.extend(payload['results'])
    results = [x for r in records for x in eforms_results(r)]
    results += simple_results(json.loads((root / 'cached-boamp-25-33856.json').read_text()))
    responses = {}
    registries = [root / 'holder-registry-20261008', root / 'project-registry-20261008']
    if args.fetch:
        known = json.loads((registries[0] / 'registry-manifest.json').read_text())['entries']
        fetch(registries[1], holders.holder_sirets(rows), [e['siret'] for e in known if e.get('status') == 200])
    for directory in registries:
        if not (directory / 'registry-manifest.json').exists():
            continue
        for e in json.loads((directory / 'registry-manifest.json').read_text())['entries']:
            body = (directory / e['file']).read_bytes()
            if e.get('status') == 200 and not e.get('truncated') and hashlib.sha256(body).hexdigest() == e['sha256']:
                responses[e['siret']] = json.loads(body)
    entries = reconcile(rows, results, responses)
    discovery = json.loads((root / 'official-discovery-20261008/boamp-project-discovery.response').read_text())['results']
    cached = json.loads((root / 'cached-boamp-25-33856.json').read_text())
    timeline = []
    for r in sorted([d for d in discovery if d['idweb'] in CALLS] + records + [cached], key=lambda r: (r['dateparution'], r['idweb'])):
        award = r['nature'] == 'ATTRIBUTION'
        found = [x for x in results if x['noticeId'] == r['idweb']]
        timeline.append({'date': r['dateparution'], 'label': ('Avis d’attribution ' if award else 'Avis d’appel public ') + r['idweb'],
                         'description': (f"{len(found)} lot(s) attribué(s). " if award else '') + r['objet'],
                         'source': NOTICE_URL + r['idweb'], 'type': 'Donnée officielle'})
    unawarded = [{k: x[k] for k in ['noticeId', 'lotNumber', 'contractReference', 'amount', 'offers']}
                 for x in results if not any(e.get('contractReference') == x['contractReference'] for e in entries)]
    out = root / 'project-reconciliation.json'
    out.write_text(json.dumps({'project': PROJECT['id'], 'entries': entries, 'noticeResultsWithoutDecpRow': unawarded,
                               'noticeResults': len(results)}, default=str, indent=2) + '\n')
    out.chmod(0o600)
    if args.write_curated:
        (ROOT / 'data/decp-cities-curated.json').write_text(json.dumps(curated(entries, rows, timeline), default=float, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'sourceRows': len(entries), 'paired': sum(e['matches'] == 1 for e in entries),
                      'holdersLinked': sum(e.get('holderLinked', False) for e in entries),
                      'offerDisagreements': sum(e.get('offersDisagree', False) for e in entries),
                      'noticeResultsWithoutDecpRow': len(unawarded)}))


if __name__ == '__main__':
    main()
