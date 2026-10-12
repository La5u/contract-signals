#!/usr/bin/env python3
"""Build conservative BOAMP ↔ DECP evidence links; no scores or raw exports."""
import argparse
from collections import Counter, defaultdict
from datetime import date
import gzip
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
INPUTS = ('data/contracts.json', 'data/decp-history.json', 'data/decp-cities.json',
          'data/boamp-raw.json.gz')
HOSTS = {'www.boamp.fr', 'boamp.fr', 'data.economie.gouv.fr', 'www.data.gouv.fr',
         'data.gouv.fr', 'data.nantesmetropole.fr', 'opendata.bordeaux-metropole.fr'}


def official_url(value):
    try:
        u = urlsplit(value)
        return (u.scheme == 'https' and u.hostname in HOSTS and not u.username
                and not u.password and u.port in (None, 443))
    except (ValueError, TypeError):
        return False


def many(value):
    return value if isinstance(value, list) else [] if value is None else [value]


def text(value):
    if isinstance(value, dict):
        value = value.get('#text')
    return value.strip() if isinstance(value, str) else None


def identifier(value):
    return text(value.get('cbc:ID')) if isinstance(value, dict) else None


def reference(value):
    value = text(value)
    # eForms CON identifiers are notice-local, never published contract references.
    return value if value and not re.fullmatch(r'CON-\d+', value, re.I) else None


def raw_references(records):
    """Unique notice, unique winning lot result, unique settled contract only."""
    notices = defaultdict(list)
    for record in records:
        notices[record.get('idweb')].append(record)
    recovered = {}
    for notice_id, entries in notices.items():
        if not notice_id or len(entries) != 1:
            continue
        try:
            notice = json.loads(entries[0]['donnees'])['EFORMS']['ContractAwardNotice']
            ext = notice['ext:UBLExtensions']['ext:UBLExtension']['ext:ExtensionContent']['efext:EformsExtension']
            result = ext.get('efac:NoticeResult') or {}
            contracts = defaultdict(list)
            for contract in many(result.get('efac:SettledContract')):
                contracts[identifier(contract)].append(contract)
            lots = defaultdict(list)
            for lot in many(result.get('efac:LotResult')):
                lots[identifier(lot.get('efac:TenderLot'))].append(lot)
            for lot_id, rows in lots.items():
                if not lot_id or len(rows) != 1:
                    continue
                row = rows[0]
                if text(row.get('cbc:TenderResultCode')) != 'selec-w':
                    continue
                ids = many(row.get('efac:SettledContract'))
                if len(ids) != 1:
                    continue
                matches = contracts.get(identifier(ids[0]), [])
                if len(matches) != 1:
                    continue
                refs = many(matches[0].get('efac:ContractReference'))
                if len(refs) == 1:
                    ref = reference(identifier(refs[0]))
                    if ref:
                        recovered[(notice_id, lot_id)] = ref
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
    return recovered


def siret(value):
    return value if isinstance(value, str) and re.fullmatch(r'[0-9]{14}', value) else None


def holders(record):
    return {v['id'] for v in record.get('supplierIds', [])
            if v.get('identifierType') == 'SIRET' and siret(v.get('id'))}


def valid_date(value):
    try:
        return value if isinstance(value, str) and date.fromisoformat(value).isoformat() == value else None
    except ValueError:
        return None


def cpv(value):
    return value[:8] if isinstance(value, str) and re.fullmatch(r'\d{8}(?:-\d)?', value) else None


def build_links(boamp, decp, raw):
    refs = raw_references(raw)
    buyers = defaultdict(list)
    for row in decp:
        if row.get('dataFamily') == 'decp' and siret(row.get('buyerSiret')):
            buyers[row['buyerSiret']].append(row)
    links = []
    for b in sorted(boamp, key=lambda r: r['id']):
        if b.get('dataFamily') != 'boamp' or not siret(b.get('buyerSiret')):
            continue
        recovered = refs.get((b.get('noticeId'), b.get('lotId')))
        # contractId is deliberately ignored on BOAMP; it is an eForms local ID.
        published_ref = recovered or reference(b.get('contractReference'))
        for d in sorted(buyers[b['buyerSiret']], key=lambda r: r['id']):
            reasons = []
            if published_ref and published_ref == reference(d.get('contractId')):
                reasons.append('buyer-published-contract-reference')
            if (b.get('noticeId') and b.get('lotId') and b['noticeId'] == d.get('noticeId')
                    and b['lotId'] == d.get('lotId')):
                reasons.append('buyer-exact-notice-lot')
            if reasons:
                status = 'confirmed'
            elif (valid_date(b.get('date')) and b['date'] == valid_date(d.get('date'))
                  and holders(b) & holders(d)):
                status = 'candidate'
                reasons = ['buyer-holder-siret-same-date']
            else:
                continue
            warnings = []
            if status == 'candidate':
                warnings.append('unconfirmed-no-exact-reference')
            if cpv(b.get('cpv')) and cpv(d.get('cpv')) and cpv(b['cpv']) != cpv(d['cpv']):
                warnings.append('different-cpv')
            if not official_url(b.get('source')) or not official_url(d.get('source')):
                raise ValueError(f"Non-official source URL for {b['id']} / {d['id']}")
            links.append({'boampId': b['id'], 'decpId': d['id'], 'status': status,
                          'basis': reasons, 'warnings': warnings,
                          'boampUrl': b['source'], 'decpUrl': d['source']})
    # Ambiguity is directional in both datasets; never choose one duplicate.
    bc = Counter(v['boampId'] for v in links)
    dc = Counter(v['decpId'] for v in links)
    for link in links:
        if bc[link['boampId']] > 1:
            link['warnings'].append('multiple-decp-matches')
        if dc[link['decpId']] > 1:
            link['warnings'].append('multiple-boamp-matches')
    return links, len(refs)


def build(root=ROOT):
    loaded, sources = [], []
    for name in INPUTS:
        payload = (root / name).read_bytes()
        data = json.loads(gzip.decompress(payload) if name.endswith('.gz') else payload)
        records = data['records'] if isinstance(data, dict) else data
        loaded.append(records)
        sources.append({'path': name, 'sha256': hashlib.sha256(payload).hexdigest(),
                        'count': len(records)})
    boamp, history, cities, raw = loaded
    links, recovered = build_links(boamp, history + cities, raw)
    counts = Counter(link['status'] for link in links)
    return {'schemaVersion': 1, 'sources': sources,
            'counts': {'confirmed': counts['confirmed'], 'candidate': counts['candidate'],
                       'ambiguous': sum(any(w.startswith('multiple-') for w in v['warnings']) for v in links),
                       'differentCpv': sum('different-cpv' in v['warnings'] for v in links),
                       'rawNoticeLotReferences': recovered},
            'links': links}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'data/boamp-decp-links.json')
    args = parser.parse_args()
    artifact = build()
    args.output.write_text(json.dumps(artifact, ensure_ascii=False, separators=(',', ':')) + '\n')
    print(json.dumps(artifact['counts'], sort_keys=True))


if __name__ == '__main__':
    main()
