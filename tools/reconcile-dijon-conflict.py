#!/usr/bin/env python3
"""Offline candidate lot reconciliation for one Dijon procedure-ID collision.

No dataset writes, sums, scoring, arbitrary source precedence or holder inference.
"""
import argparse
from datetime import date
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
CACHE = Path.home() / '.cache/contract-signals/decp-conflict-dijon'
BUYER, PROCEDURE, NOTICE = '21210231300013', '2023VDAO1642', '24-79759'


def text(value):
    return value.get('#text') if isinstance(value, dict) else value


def many(value):
    return value if isinstance(value, list) else [] if value is None else [value]


def unique(items, accessor):
    result = {}
    for item in many(items):
        key = text(accessor(item))
        if not key or key in result:
            raise ValueError('Missing or duplicate relationship identity')
        result[key] = item
    return result


def amount(value):
    value = text(value)
    if isinstance(value, bool) or value is None:
        return None
    try:
        n = Decimal(str(value))
    except InvalidOperation:
        return None
    return n if n.is_finite() and n >= 0 else None


def date_component(value):
    value = text(value)
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value[:10]).isoformat()
    except ValueError:
        return None


def offer_total(result):
    vals = []
    for item in many(result.get('efac:ReceivedSubmissionsStatistics')):
        if text(item.get('efbc:StatisticsCode')) == 'tenders':
            value = text(item.get('efbc:StatisticsNumeric'))
            vals.append(int(value) if re.fullmatch(r'\d+', str(value)) else None)
    return vals[0] if vals and all(v == vals[0] for v in vals) else None


def identifiers(row):
    return {str(row['titulaire_id_' + str(i)]) for i in range(1, 4)
            if row.get('titulaire_typeidentifiant_' + str(i)) == 'SIRET'
            and re.fullmatch(r'\d{14}', str(row.get('titulaire_id_' + str(i), '')))}


def reconcile(ministry, record):
    notice = json.loads(record['donnees'])['EFORMS']['ContractAwardNotice']
    if record['idweb'] != NOTICE or text(notice['cac:ProcurementProject']['cbc:ID']) != PROCEDURE:
        raise ValueError('Notice or exact procedure identity mismatch')
    ext = notice['ext:UBLExtensions']['ext:UBLExtension']['ext:ExtensionContent']['efext:EformsExtension']
    nr = ext['efac:NoticeResult']
    orgs = unique(ext['efac:Organizations']['efac:Organization'], lambda x: x['efac:Company']['cac:PartyIdentification']['cbc:ID'])
    buyer_ref = text(notice['cac:ContractingParty']['cac:Party']['cac:PartyIdentification']['cbc:ID'])
    buyer_company = orgs[buyer_ref]['efac:Company']
    buyer_ids = [text(x.get('cbc:CompanyID')) for x in many(buyer_company.get('cac:PartyLegalEntity'))]
    if BUYER not in buyer_ids:
        raise ValueError('Exact buyer SIRET mismatch')
    lots = unique(notice['cac:ProcurementProjectLot'], lambda x: x['cbc:ID'])
    tenders = unique(nr['efac:LotTender'], lambda x: x['cbc:ID'])
    contracts = unique(nr['efac:SettledContract'], lambda x: x['cbc:ID'])
    parties = unique(nr['efac:TenderingParty'], lambda x: x['cbc:ID'])
    awarded = []
    for result in many(nr['efac:LotResult']):
        if not result.get('efac:LotTender') or not result.get('efac:SettledContract'):
            continue
        if isinstance(result['efac:LotTender'], list) or isinstance(result['efac:SettledContract'], list):
            raise ValueError('Multiple winning references; not resolved')
        lid = text(result['efac:TenderLot']['cbc:ID'])
        tender_id = text(result['efac:LotTender']['cbc:ID'])
        cid = text(result['efac:SettledContract']['cbc:ID'])
        tender, contract = tenders[tender_id], contracts[cid]
        if text(tender['efac:TenderLot']['cbc:ID']) != lid or text(contract['efac:LotTender']['cbc:ID']) != tender_id:
            raise ValueError('Inconsistent lot/tender/contract relationship')
        node = tender['cac:LegalMonetaryTotal']['cbc:PayableAmount']
        party = parties[text(tender['efac:TenderingParty']['cbc:ID'])]
        holder_ids = []
        for ref in many(party['efac:Tenderer']):
            company = orgs[text(ref['cbc:ID'])]['efac:Company']
            holder_ids.extend(text(x.get('cbc:CompanyID')) for x in many(company.get('cac:PartyLegalEntity')))
        valid_holders = {str(x) for x in holder_ids if re.fullmatch(r'\d{14}', str(x))}
        awarded.append({'technicalLotId': lid, 'printedLotNumber': text(lots[lid]['cac:ProcurementProject'].get('cbc:ID')),
                        'internalContractId': cid, 'contractReference': text(contract['efac:ContractReference']['cbc:ID']),
                        'amount': amount(node), 'currency': node.get('@currencyID'),
                        'conclusionDate': date_component(contract['cbc:IssueDate']), 'offers': offer_total(result),
                        '_holderIds': valid_holders})
    candidates = []
    for index, row in enumerate(ministry):
        if row.get('acheteur_id') != BUYER or row.get('id') != PROCEDURE:
            raise ValueError('Ministry source outside exact scope')
        vals = [a for a in awarded if a['currency'] == 'EUR' and a['amount'] is not None
                and a['amount'] == amount(row.get('montant'))
                and a['conclusionDate'] == date_component(row.get('datenotification'))
                and str(a['contractReference']).upper().startswith(PROCEDURE)]
        current_offers = row.get('offresrecues')
        current_offers = int(current_offers) if re.fullmatch(r'\d+', str(current_offers)) else None
        candidate = {'ministryRowIndex': index, 'exactBuyerAndProcedureMatched': True,
                     'candidateCount': len(vals), 'status': 'ambiguous_or_unmatched', 'decpOffers': current_offers}
        if len(vals) == 1:
            a = vals[0]
            holder_confirmed = bool(identifiers(row)) and identifiers(row) == a['_holderIds']
            candidate.update({k: v for k, v in a.items() if not k.startswith('_')},
                             holderIdentityConfirmed=holder_confirmed,
                             offersDisagree=current_offers is not None and a['offers'] is not None and current_offers != a['offers'],
                             status='candidate_lot_match_not_verified',
                             dateMeaning='DECP notification versus notice conclusion: same date, distinct semantics',
                             amountBasis='Notice winning-tender PayableAmount; tax comparability unresolved')
        candidates.append(candidate)
    # Do not allow two source rows to silently attach to one candidate lot.
    assigned = [c.get('technicalLotId') for c in candidates if c['candidateCount'] == 1]
    if len(assigned) != len(set(assigned)):
        for c in candidates:
            c['status'] = 'non_unique_source_to_lot_mapping'
    return {'noticeId': NOTICE, 'procedureId': PROCEDURE, 'buyerSiret': BUYER,
            'noticeUuid': text(notice['cbc:ID']), 'noticeVersion': str(text(notice['cbc:VersionID'])),
            'awardedResults': len(awarded), 'candidates': candidates,
            'otherAwardedLots': [{k: v for k, v in a.items() if not k.startswith('_')}
                                 for a in awarded if a['technicalLotId'] not in assigned],
            'publicationAction': 'none; grouped DECP row remains excluded',
            'limits': ['Exact buyer/procedure linkage, but no trustworthy BOAMP holder IDs to independently match individual DECP rows',
                       'Amounts and dates support candidate pairing; not sole proof of canonical contract identity',
                       'No signed buyer contracts or source precedence established']}


def corroborate_pdf(document, findings):
    if not re.search(re.escape(findings['noticeUuid']) + r'\s*-\s*' + re.escape(findings['noticeVersion']) + r'\b', document):
        raise ValueError('PDF notice UUID/version mismatch')
    if f"Annonce n° {NOTICE}" not in document or PROCEDURE not in document:
        raise ValueError('PDF notice/procedure mismatch')
    headings = list(re.finditer(r'6\.1\s+Résultat\s*[–-]\s*Identifiants des lots\s*:\s*(LOT-\d+)', document))
    for candidate in findings['candidates']:
        if candidate['candidateCount'] != 1:
            continue
        spans = [(h.end(), headings[i + 1].start() if i + 1 < len(headings) else len(document))
                 for i, h in enumerate(headings) if h.group(1) == candidate['technicalLotId']]
        if len(spans) != 1:
            raise ValueError('PDF result missing or ambiguous')
        section = document[spans[0][0]:spans[0][1]]
        amounts = re.findall(r'Valeur du résultat\s*:\s*([\d,.]+)\s+Euro', section)
        refs = re.findall(r'Identifiant du marché\s*:\s*([^\n]+)', section)
        dates = re.findall(r'Date de conclusion du marché\s*:\s*(\d{2}/\d{2}/\d{4})', section)
        offers = re.findall(r'Type de soumissions reçues\s*:\s*Offres\s*\n\s*Nombre d’offres ou de demandes de participation reçues\s*:\s*(\d+)', section)
        parsed_date = None
        if len(dates) == 1:
            d, m, y = map(int, dates[0].split('/'))
            parsed_date = date(y, m, d).isoformat()
        candidate['pdfCorroboration'] = {
            'amount': len(amounts) == 1 and bool(re.fullmatch(r'(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?', amounts[0])) and amount(amounts[0].replace(',', '')) == candidate['amount'],
            'contractReference': len(refs) == 1 and refs[0].strip() == candidate['contractReference'],
            'conclusionDate': parsed_date == candidate['conclusionDate'],
            'offers': len(offers) == 1 and int(offers[0]) == candidate['offers'],
            'taxBasis': 'unresolved', 'holderIdentity': 'unresolved'}
    return findings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence-dir', type=Path, default=CACHE)
    args = parser.parse_args()
    root = args.evidence_dir.resolve()
    if root == ROOT or ROOT in root.parents:
        parser.error('Private evidence must remain outside repository')
    discovery = root / 'official-discovery-20261008'
    raw_ministry = discovery / 'ministry-exact.response'
    raw_boamp = discovery / 'boamp-contract-reference.response'
    m, b = json.loads(raw_ministry.read_text()), json.loads(raw_boamp.read_text())
    if m['total_count'] != len(m['results']) or b['total_count'] != len(b['results']):
        raise ValueError('Incomplete exact-ID response; no candidate reconciliation')
    records = [r for r in b['results'] if r['idweb'] == NOTICE]
    if len(records) != 1:
        raise ValueError('Missing or ambiguous exact award notice')
    findings = reconcile(m['results'], records[0])
    findings['inputsSha256'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [raw_ministry, raw_boamp]}
    pdf = root / 'boamp-24-79759.pdf'
    if pdf.exists():
        from pypdf import PdfReader
        manifest = json.loads((root / 'pdf-manifest.json').read_text())
        digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
        if manifest.get('status') != 200 or manifest.get('truncated') or digest != manifest['sha256']:
            raise ValueError('Invalid or hash-mismatched PDF acquisition')
        reader = PdfReader(pdf)
        document = '\n'.join(p.extract_text() or '' for p in reader.pages)
        findings = corroborate_pdf(document, findings)
        findings['pdfEvidence'] = {'sha256': digest, 'pages': len(reader.pages), 'url': manifest['url'], 'retrievedAt': manifest['retrievedAt']}
    out = root / 'lot-candidate-reconciliation.json'
    out.write_text(json.dumps(findings, default=str, indent=2) + '\n')
    out.chmod(0o600)
    print(json.dumps({'sourceRows': len(findings['candidates']),
                      'uniqueCandidateLotMatches': sum(c['candidateCount'] == 1 for c in findings['candidates']),
                      'offerCountDisagreements': sum(c.get('offersDisagree', False) for c in findings['candidates']),
                      'holderIdentitiesConfirmed': sum(c.get('holderIdentityConfirmed', False) for c in findings['candidates']),
                      'publishedChanges': 0}))


if __name__ == '__main__':
    main()
