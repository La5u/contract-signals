#!/usr/bin/env python3
"""Read-only, offline review. Run from any directory; prints JSON to stdout.

Importer regeneration is distinguished from independent raw field/relationship
checks. No importer main/offline/download entry point is called.
"""
import copy
import gzip
import hashlib
import importlib.util
import json
import math
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]

def load(name):
    p = ROOT / 'data' / name
    return json.loads(gzip.decompress(p.read_bytes()) if name.endswith('.gz') else p.read_text())

def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'tools' / (name + '.py'))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

def clean(v):
    return None if v in (None, '', 'CDL', 'INX') else v

def numeric(v):
    try:
        n = float(clean(v))
        return n if math.isfinite(n) and n >= 0 else None
    except (ValueError, TypeError):
        return None

def calendar(v):
    if not isinstance(v, str) or not re.match(r'^\d{4}-\d{2}-\d{2}', v):
        return None
    try:
        return date.fromisoformat(v[:10]).isoformat()
    except ValueError:
        return None

def offer(v):
    s = str(v)
    return int(s) if re.fullmatch('[0-9]+', s) else None

def distribution(rows, fields):
    return {f: {'known': sum(r.get(f) is not None for r in rows),
                'null': sum(r.get(f) is None for r in rows),
                'zero': sum(r.get(f) == 0 for r in rows)} for f in fields}

def mismatches(expected, published, ignore=()):
    actual = {r['id']: r for r in published}
    result = Counter()
    for r in expected:
        if r['id'] not in actual:
            result['missing_id'] += 1
            continue
        for k, v in r.items():
            if k not in ignore and actual[r['id']].get(k) != v:
                result[k] += 1
    result['extra_ids'] += len(set(actual) - {r['id'] for r in expected})
    return {k: v for k, v in result.items() if v}

def decp(rawname, pubname, m, cities=False):
    raw, published = load(rawname), load(pubname)
    regenerated = m.normalize(raw, None, {'counts': {}}) if cities else m.normalize(raw)
    if not cities:
        curated = load('decp-history-curated.json')['rows']
        for r in regenerated:
            r.update(curated.get(r['id'], {}))
    groups = defaultdict(list)
    for r in raw['records']:
        groups[(str(r['acheteur_id']), str(r['id']))].append(r)
    errors, conflictcounts, rawclasses = Counter(), Counter(), {}
    fields = {'amount': ('montant', numeric), 'offers': ('offresrecues', offer),
              'date': ('datenotification', calendar), 'publicationDate': ('datepublicationdonnees', calendar),
              'durationMonths': ('dureemois', numeric)}
    for f, (source, parse) in fields.items():
        rawclasses[f] = dict(Counter('missing_or_sentinel' if clean(r.get(source)) is None else
                                    'invalid' if parse(r.get(source)) is None else
                                    'zero' if parse(r.get(source)) == 0 else 'valid_nonzero'
                                    for r in raw['records']))
    mod_ambiguous, mod_examples, duplicate_rows = 0, [], 0
    history_supplier_omissions = Counter()
    for r in published:
        key = (r['buyerSiret'], r['contractId'])
        variants = groups[key]
        duplicate_rows += len(variants) - len({json.dumps(v, sort_keys=True) for v in variants})
        if r['id'] != 'decp-' + '-'.join(key): errors['id'] += 1
        where = parse_qs(urlparse(r['source']).query).get('where', [''])[0]
        if f"acheteur_id='{key[0]}'" not in where or "id='" + key[1].replace("'", "''") + "'" not in where:
            errors['source_filter'] += 1
        for f, (source, parse) in fields.items():
            vals = [parse(v.get(source)) for v in variants]
            conflict = any(v != vals[0] for v in vals[1:])
            conflictcounts[f] += conflict
            expected = None if conflict else vals[0]
            if r.get(f) != expected: errors[f] += 1
            if f != 'publicationDate' or cities:
                if (f in r['initialConflicts']) != conflict: errors[f + '_conflict_label'] += 1
        supplier_values = []
        for v in variants:
            ids = []
            for i in range(1, 4):
                ident, typ = clean(v.get(f'titulaire_id_{i}')), clean(v.get(f'titulaire_typeidentifiant_{i}'))
                if ident is not None:
                    item = {'id': str(ident), 'identifierType': str(typ) if typ else None}
                    if typ == 'SIRET' and re.fullmatch('[0-9]{14}', str(ident)): item['siren'] = str(ident)[:9]
                    if typ == 'SIREN' and re.fullmatch('[0-9]{9}', str(ident)): item['siren'] = str(ident)
                    ids.append(item)
            supplier_values.append(ids)
        expected_ids = None if any(v != supplier_values[0] for v in supplier_values) else supplier_values[0]
        if r['supplierIds'] != expected_ids: errors['supplierIds'] += 1
        mods = defaultdict(set)
        for event in r['history']:
            if event['kind'] == 'initial':
                if any(event.get(f) != r.get(f) for f in ['amount', 'date', 'publicationDate', 'durationMonths']):
                    errors['initial_history'] += 1
                if len(r['supplierIds'] or []) == 1 and event.get('supplierId') is None:
                    history_supplier_omissions['single_initial_holder'] += 1
            else:
                matching = [v for v in variants if str(clean(v.get('idmodification'))) == event['id'] and
                            numeric(v.get('montantmodification')) == event['amount'] and
                            numeric(v.get('dureemoismodification')) == event['durationMonths'] and
                            calendar(v.get('datenotificationmodificationmodification')) == event['date'] and
                            calendar(v.get('datepublicationdonneesmodificationmodification')) == event['publicationDate']]
                if not matching: errors['modification_history'] += 1
                if any(clean(v.get('idtitulairemodification')) is not None for v in matching) and event.get('supplierId') is None:
                    history_supplier_omissions['published_modification_holder'] += 1
        for v in variants:
            if clean(v.get('idmodification')) is not None:
                mods[str(v['idmodification'])].add((numeric(v.get('montantmodification')), numeric(v.get('dureemoismodification')),
                    calendar(v.get('datenotificationmodificationmodification')), calendar(v.get('datepublicationdonneesmodificationmodification')),
                    clean(v.get('idtitulairemodification')), clean(v.get('typeidentifianttitulairemodification'))))
        if any(len(v) > 1 for v in mods.values()):
            mod_ambiguous += 1
            if len(mod_examples) < 5: mod_examples.append(r['id'])
    pages = raw['queries']
    return {'retrievedAt': raw['retrievedAt'], 'rawRows': len(raw['records']), 'pages': len(pages),
            'pageCountSum': sum(p['count'] for p in pages), 'rawRowsByBuyer': dict(Counter(r['acheteur_id'] for r in raw['records'])),
            'declaredTotals': raw['totals'], 'normalizedRows': len(published), 'duplicatePublishedIds': len(published)-len({r['id'] for r in published}),
            'exactDuplicateRawRows': duplicate_rows, 'regenerationMismatches': mismatches(regenerated, published),
            'independentMappingErrors': dict(errors), 'rawValueClasses': rawclasses,
            'publishedFields': distribution(published, fields), 'conflictGroupsByReviewedField': dict(conflictcounts),
            'groupsWithInitialConflicts': sum(bool(r['initialConflicts']) for r in published),
            'groupsWithPublishedModifications': sum(len(r['history']) > 1 for r in published),
            'publishedModificationEvents': sum(len(r['history'])-1 for r in published),
            'rawSameModificationIdDifferentValuesGroups': mod_ambiguous, 'modificationAmbiguityExamples': mod_examples, 'historySupplierOmissions': dict(history_supplier_omissions),
            'invalidRawOfferValues': dict(Counter(str(r.get('offresrecues')) for r in raw['records'] if clean(r.get('offresrecues')) is not None and offer(r.get('offresrecues')) is None))}

# Independent XML-as-JSON accessors (do not use importer helpers here).
def many(v): return v if isinstance(v, list) else [] if v is None else [v]
def txt(v): return v.get('#text') if isinstance(v, dict) else v
def at(v, *keys):
    for k in keys:
        if isinstance(v, list): v = v[0] if v else None
        v = v.get(k) if isinstance(v, dict) else None
    return v[0] if isinstance(v, list) and v else v

def boamp(m):
    raw = load('boamp-raw.json.gz')
    sample, stats = m.build(raw)
    published = [r for r in load('contracts.json') if r.get('dataFamily') == 'boamp' and not r['id'].startswith('boamp-25-846-')]
    sampleids = {r['id'] for r in published}
    anomalies, errors, candidate_fields, currency, statistics, examples = Counter(), Counter(), [], Counter(), Counter(), defaultdict(list)
    first_record = None
    for record in raw['records']:
        rows = m.lot_rows(record)
        if rows is None: continue
        if first_record is None and any('excluded' not in r for r in rows): first_record = record
        n = json.loads(record['donnees'])['EFORMS']['ContractAwardNotice']
        ext = at(n, 'ext:UBLExtensions', 'ext:UBLExtension', 'ext:ExtensionContent', 'efext:EformsExtension')
        result = ext.get('efac:NoticeResult') or {}
        index = lambda name: {txt(at(x, 'cbc:ID')): x for x in many(result.get(name))}
        tenders, contracts, parties = index('efac:LotTender'), index('efac:SettledContract'), index('efac:TenderingParty')
        orgs = {txt(at(o, 'efac:Company', 'cac:PartyIdentification', 'cbc:ID')): at(o, 'efac:Company') for o in many((ext.get('efac:Organizations') or {}).get('efac:Organization'))}
        selected = [x for x in many(result.get('efac:LotResult')) if txt(at(x, 'cbc:TenderResultCode')) == 'selec-w']
        for res, row in zip(selected, rows):
            if 'excluded' in row: continue
            candidate_fields.append(row)
            def flag(name):
                anomalies[name] += 1
                if row['id'] in sampleids: anomalies[name + '_sample'] += 1
                if len(examples[name]) < 3: examples[name].append(row['id'])
            tids = [txt(at(t, 'cbc:ID')) for t in many(res.get('efac:LotTender'))]
            cids = [txt(at(c, 'cbc:ID')) for c in many(res.get('efac:SettledContract'))]
            tender = tenders.get(tids[0], {})
            node = at(tender, 'cac:LegalMonetaryTotal', 'cbc:PayableAmount')
            cur = node.get('@currencyID') if isinstance(node, dict) else None
            currency[str(cur)] += 1
            expected = numeric(txt(node)) if cur == 'EUR' else None
            if row['amount'] != expected: errors['amount'] += 1
            if row['amount'] is not None and not math.isfinite(row['amount']): flag('nonfinite_amount')
            issue = txt(at(contracts.get(cids[0], {}) if cids else {}, 'cbc:IssueDate'))
            if issue and calendar(issue) is None: flag('invalid_contract_date')
            if row['date'] != calendar(issue): errors['calendar_date'] += 1
            nums = []
            for s in many(res.get('efac:ReceivedSubmissionsStatistics')):
                code = txt(at(s, 'efbc:StatisticsCode'))
                statistics[str(code)] += 1
                if code == 'tenders': nums.append(txt(s.get('efbc:StatisticsNumeric')))
            parsed = [offer(v) for v in nums if offer(v) is not None]
            if len(set(parsed)) > 1: flag('conflicting_tenders_statistics')
            if any(isinstance(s.get('efbc:StatisticsNumeric'), dict) for s in many(res.get('efac:ReceivedSubmissionsStatistics')) if txt(at(s, 'efbc:StatisticsCode')) == 'tenders'):
                flag('text_node_tenders_numeric')
            expected_offers = parsed[-1] if parsed else None
            if row['offers'] != expected_offers: errors['offers'] += 1
            party = parties.get(txt(at(tender, 'efac:TenderingParty', 'cbc:ID')), {})
            refs = [txt(at(t, 'cbc:ID')) for t in many(party.get('efac:Tenderer'))]
            if any(t not in orgs for t in refs): flag('missing_tenderer_organization')
            names, supplierids = [], []
            for ref in refs:
                company = orgs.get(ref)
                if company is None: continue
                name = txt(at(company, 'cac:PartyName', 'cbc:Name'))
                if name: names.append(name)
                cid = (txt(at(company, 'cac:PartyLegalEntity', 'cbc:CompanyID')) or '').strip()
                if not cid: continue
                compact = re.sub(r'\s', '', cid)
                country = txt(at(company, 'cac:PostalAddress', 'cac:Country', 'cbc:IdentificationCode'))
                typ = 'SIRET' if country == 'FRA' and re.fullmatch('[0-9]{14}', compact) else 'SIREN' if country == 'FRA' and re.fullmatch('[0-9]{9}', compact) else 'identifiant publié'
                supplierids.append({'id': compact if typ != 'identifiant publié' else cid, 'identifierType': typ, 'siren': compact[:9] if typ != 'identifiant publié' else None})
                if country != 'FRA' and re.fullmatch('[0-9]{9}|[0-9]{14}', compact): flag('foreign_french_length_id')
            if row['supplier'] != ' / '.join(names): errors['supplier_name'] += 1
            if row['supplierIds'] != supplierids: errors['supplierIds'] += 1
            lotid = txt(at(res, 'efac:TenderLot', 'cbc:ID'))
            if row['id'] != f"boamp-{record['idweb']}-{lotid.lower()}" or row['noticeId'] != record['idweb'] or row['lotId'] != lotid or row['contractId'] != (cids[0] if cids else None): errors['source_ids'] += 1
    # Synthetic probes demonstrate parser behavior, not observed source errors.
    def probe(mutator):
        r = copy.deepcopy(first_record)
        n = json.loads(r['donnees'])
        notice = n['EFORMS']['ContractAwardNotice']
        ext = at(notice, 'ext:UBLExtensions', 'ext:UBLExtension', 'ext:ExtensionContent', 'efext:EformsExtension')
        res = ext['efac:NoticeResult']
        mutator(res)
        r['donnees'] = json.dumps(n)
        return next((x for x in m.lot_rows(r) if 'excluded' not in x), None)
    # Mutate all nodes so the first eligible result certainly exercises the probe.
    def amounts(result):
        for t in many(result.get('efac:LotTender')): t['cac:LegalMonetaryTotal'] = {'cbc:PayableAmount': {'@currencyID': 'EUR', '#text': 'Infinity'}}
    def dates(result):
        for c in many(result.get('efac:SettledContract')): c['cbc:IssueDate'] = '2025-02-30'
    def offers(result):
        for r in many(result.get('efac:LotResult')): r['efac:ReceivedSubmissionsStatistics'] = [{'efbc:StatisticsCode': 'tenders', 'efbc:StatisticsNumeric': '1'}, {'efbc:StatisticsCode': 'tenders', 'efbc:StatisticsNumeric': '2'}]
    def missing_org(result):
        for p in many(result.get('efac:TenderingParty')):
            p['efac:Tenderer'] = [{'cbc:ID': 'ORG-MISSING'}] + many(p.get('efac:Tenderer'))
    def dict_offers(result):
        for r in many(result.get('efac:LotResult')): r['efac:ReceivedSubmissionsStatistics'] = {'efbc:StatisticsCode': 'tenders', 'efbc:StatisticsNumeric': {'#text': '0'}}
    amount_probe = probe(amounts)
    organization_probe = probe(missing_org)
    return {'retrievedAt': raw['retrievedAt'], 'total': raw['total'], 'pages': len(raw['queries']), 'pageCountSum': sum(p['count'] for p in raw['queries']),
            'buildCounts': stats, 'publishedSampleRows': len(published), 'regenerationMismatches': mismatches(sample, published), 'sameSampleOrder': sample == published,
            'independentCandidateMappingErrors': dict(errors), 'allCandidateFields': distribution(candidate_fields, ['amount', 'offers', 'date', 'durationMonths']),
            'publishedFields': distribution(published, ['amount', 'offers', 'date', 'durationMonths']), 'candidateAmountCurrency': dict(currency),
            'candidateStatisticsCodes': dict(statistics), 'anomalies': dict(anomalies), 'examples': dict(examples),
            'syntheticProbes': {'infiniteAmountRetained': amount_probe['amount'] is not None and math.isinf(amount_probe['amount']), 'invalidCalendarDateRetained': probe(dates)['date'],
                               'conflictingOffersLastWins': probe(offers)['offers'], 'textNodeZeroOffersBecomes': probe(dict_offers)['offers'],
                               'missingFirstOrgExcluded': organization_probe is None,
                               'missingFirstOrgMisattributedInSourceReference': organization_probe is not None and 'supplier organization ORG-MISSING' in organization_probe['sourceReference']}}

def main():
    files = ['decp-cities-raw.json', 'decp-cities.json', 'decp-history-raw.json.gz', 'decp-history.json', 'decp-history-curated.json', 'boamp-raw.json.gz', 'contracts.json']
    output = {'sha256': {f: hashlib.sha256((ROOT / 'data' / f).read_bytes()).hexdigest() for f in files},
              'cities': decp(files[0], files[1], module('import-decp-cities'), True),
              'parisArdeche': decp(files[2], files[3], module('import-decp-paris-ardeche')),
              'boamp': boamp(module('import-boamp-sample'))}
    c = module('import-decp-cities')
    base = {'acheteur_id': c.BUYERS[0][0], 'id': 'REVIEW-SYNTHETIC', 'datenotification': '2024-01-01', 'montant': '0', 'offresrecues': '0'}
    zero = c.normalize({'records': [base]}, None, {'counts': {}})[0]
    conflict = c.normalize({'records': [base, dict(base, montant='INX', offresrecues='CDL')]}, None, {'counts': {}})[0]
    output['decpSyntheticProbes'] = {'zeroAmount': zero['amount'], 'zeroOffers': zero['offers'], 'zeroVersusUnknownAmount': conflict['amount'], 'zeroVersusUnknownOffers': conflict['offers'], 'conflicts': conflict['initialConflicts']}
    print(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False))

if __name__ == '__main__':
    main()
