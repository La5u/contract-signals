#!/usr/bin/env python3
"""Preregistered random-sample accuracy check of French DECP amounts against BOAMP award notices.

  --plan      freeze a stratified random sample (seeded; exclusive file, never overwritten)
  --fetch     one bounded BOAMP query per sampled contract (frozen, no reruns)
  (default)   offline evaluation of the frozen responses

Strata are the verification statuses of tools/decp_feeds.py. A notice lot is linked only when
its contract reference contains the DECP identifier, or the winner's SIRET and the conclusion
date both equal the contract's. The shown amount is then 'confirmed' if any amount printed for
that lot equals it, otherwise 'contradicted'. Contracts without a linkable notice stay
'no-notice'. This measures agreement with award notices where they exist; it is not proof of
truth, and contracts without notices are not covered. Raw responses stay private.
"""
import argparse
from datetime import date, timedelta
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import re
import urllib.parse

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('dijon_holders', ROOT / 'tools/link-dijon-holders.py')
NAMES = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(NAMES)
CACHE = Path.home() / '.cache/contract-signals/accuracy-sample-20261008'
DATASETS = ['data/decp-cities.json', 'data/decp-history.json']
SEED, PER_STRATUM = 20261008, 30
BOAMP = 'https://www.boamp.fr/api/explore/v2.1/catalog/datasets/boamp/records'
CITY = {'21350238800019': 'Rennes', '21440109300015': 'Nantes', '21330063500017': 'Bordeaux', '21380185500015': 'Grenoble',
        '21210231300013': 'Dijon', '21370261600011': 'Tours', '21750001600019': 'Paris', '22070001700019': 'Ardèche'}
STOP = {'pour', 'dans', 'avec', 'des', 'les', 'une', 'aux', 'sur', 'ville', 'marche', 'marché', 'travaux', 'prestations',
        'fourniture', 'fournitures', 'services', 'accord', 'cadre', 'relatif', 'relatifs', 'relative', 'concernant',
        'commune', 'paris', 'dijon', 'nantes', 'rennes', 'bordeaux', 'grenoble', 'tours', 'lot', 'lots'}


def records():
    rows = []
    for path in DATASETS:
        rows += json.loads((ROOT / path).read_text())
    return rows


def sample(rows):
    rng = random.Random(SEED)
    strata = {}
    for status in ['notice-checked', 'sources-agree', 'sources-disagree', 'single-source']:
        pool = sorted(r['id'] for r in rows if (r.get('verification') or {}).get('status') == status and r.get('date'))
        strata[status] = pool if len(pool) <= PER_STRATUM else sorted(rng.sample(pool, PER_STRATUM))
    return strata


def keywords(text):
    # The title part of a DECP object is what notices repeat; long descriptions drift.
    words = [w for w in re.findall(r"[A-Za-zÀ-ÿ]{5,}", (text or '')[:100]) if w.lower() not in STOP]
    return sorted(set(words), key=lambda w: (-len(w), w))[:2]


def query(row):
    start = date.fromisoformat(row['date']) - timedelta(days=10)
    end = date.fromisoformat(row['date']) + timedelta(days=400)
    parts = [f'search(nomacheteur,"{CITY[row["buyerSiret"]]}")', 'nature="ATTRIBUTION"',
             f'dateparution>="{start}"', f'dateparution<="{end}"'] + [f'search(donnees,"{w}")' for w in keywords(row['description'])]
    return BOAMP + '?' + urllib.parse.urlencode({'where': ' AND '.join(parts), 'limit': 20, 'select': 'idweb,dateparution,objet,donnees'})


def amounts(node):
    """Every monetary amount printed anywhere in a notice fragment."""
    found = []
    if isinstance(node, dict):
        for k, v in node.items():
            if 'Amount' in k and isinstance(v, dict) and '#text' in v:
                try:
                    found.append(round(float(v['#text']), 2))
                except ValueError:
                    pass
            else:
                found += amounts(v)
    elif isinstance(node, list):
        for v in node:
            found += amounts(v)
    return found


def text(v):
    return v.get('#text') if isinstance(v, dict) else v


def many(v):
    return v if isinstance(v, list) else [] if v is None else [v]


def lots(record):
    """Linked-lot candidates from one eForms award notice: reference, date, winner SIRETs, amounts."""
    try:
        notice = json.loads(record['donnees'])['EFORMS']['ContractAwardNotice']
    except (KeyError, TypeError, ValueError):
        return []
    ext = notice['ext:UBLExtensions']['ext:UBLExtension']['ext:ExtensionContent']['efext:EformsExtension']
    nr = ext.get('efac:NoticeResult') or {}
    orgs = {text(o['efac:Company']['cac:PartyIdentification']['cbc:ID']): o['efac:Company'] for o in many(ext.get('efac:Organizations', {}).get('efac:Organization'))}
    tenders = {text(t['cbc:ID']): t for t in many(nr.get('efac:LotTender'))}
    parties = {text(p['cbc:ID']): p for p in many(nr.get('efac:TenderingParty'))}
    contracts = many(nr.get('efac:SettledContract'))
    out = []
    for result in many(nr.get('efac:LotResult')):
        for tref in many(result.get('efac:LotTender')):
            tender = tenders.get(text(tref.get('cbc:ID')))
            if not tender:
                continue
            settled = [c for c in contracts if any(text(x.get('cbc:ID')) == text(tender['cbc:ID']) for x in many(c.get('efac:LotTender')))]
            party = parties.get(text((tender.get('efac:TenderingParty') or {}).get('cbc:ID')), {})
            sirets, names = set(), []
            for ref in many(party.get('efac:Tenderer')):
                company = orgs.get(text(ref.get('cbc:ID')), {})
                sirets |= {str(text(x.get('cbc:CompanyID'))) for x in many(company.get('cac:PartyLegalEntity'))}
                names.append(text((company.get('cac:PartyName') or {}).get('cbc:Name')))
            for c in settled or [{}]:
                out.append({'reference': str(text((c.get('efac:ContractReference') or {}).get('cbc:ID')) or ''),
                            'date': str(text(c.get('cbc:IssueDate')) or '')[:10], 'sirets': sirets, 'names': [n for n in names if n],
                            'amounts': sorted(set(amounts(tender) + amounts(result)))})
    return out


def evaluate(row, response):
    holders = {s['id'] for s in row.get('supplierIds') or []}
    cid = row['contractId'].lower()
    known_ref = ((row.get('procedureGroup') or {}).get('contractReference') or '').lower()
    register = [p['name'] for p in row.get('supplierProfiles') or [] if p.get('name')]
    linked = []
    for record in (response or {}).get('results', []):
        candidates = lots(record)
        by_ref = [l for l in candidates if (l['reference'].lower() == known_ref if known_ref else len(cid) >= 6 and cid in l['reference'].lower())]
        if len(by_ref) > 1:
            # An identifier contained in several lot references (procedure ids, truncated ids) needs the holder too.
            by_ref = [l for l in by_ref if holders & l['sirets']]
        for lot in by_ref:
            linked.append({**lot, 'notice': record['idweb'], 'how': 'reference'})
        for lot in candidates:
            if lot in by_ref or lot['date'] != row['date']:
                continue
            if holders & lot['sirets']:
                linked.append({**lot, 'notice': record['idweb'], 'how': 'holder+date'})
            elif register and any(NAMES.names_agree(n, register) for n in lot['names']):
                # Amendment 2 (2026-10-08, before seeing these outcomes): notices often carry placeholder
                # SIRETs; the winner's name must agree with the holder's register name, on the same date.
                linked.append({**lot, 'notice': record['idweb'], 'how': 'register-name+date'})
    if not linked:
        return {'outcome': 'no-notice'}
    shown = row.get('amount')
    printed = sorted({a for lot in linked for a in lot['amounts']})
    others = sorted({s['amount'] for s in row.get('amountSources') or [] if s.get('amount') is not None} - {shown})
    outcome = ('notice-without-amount' if not printed else 'confirmed' if shown is not None and shown in printed
               else 'unknown-amount' if shown is None else 'contradicted')
    return {'outcome': outcome, 'notices': sorted({l['notice'] for l in linked}), 'link': sorted({l['how'] for l in linked}),
            'shownAmount': shown, 'noticeAmounts': printed, 'otherSourceMatchesNotice': any(a in printed for a in others)}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--plan', action='store_true')
    parser.add_argument('--fetch', action='store_true')
    args = parser.parse_args()
    rows = {r['id']: r for r in records()}
    plan_path = CACHE / 'plan.json'
    if args.plan:
        CACHE.mkdir(parents=True, exist_ok=True, mode=0o700)
        strata = sample(list(rows.values()))
        inputs = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in DATASETS}
        plan = {'seed': SEED, 'perStratum': PER_STRATUM, 'inputs': inputs, 'strata': strata,
                'queries': {i: query(rows[i]) for ids in strata.values() for i in ids}}
        with plan_path.open('x') as stream:
            stream.write(json.dumps(plan, ensure_ascii=False, indent=2) + '\n')
        print({k: len(v) for k, v in strata.items()})
        return
    plan = json.loads(plan_path.read_text())
    if args.fetch:
        spec = importlib.util.spec_from_file_location('f', ROOT / 'tools/fetch-decp-conflict-evidence.py')
        f = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(f)
        if not (CACHE / 'responses').exists():
            f.requests = lambda: [{'label': i, 'url': u} for i, u in plan['queries'].items()]
            f.fetch(CACHE / 'responses')
            return
        # Amendment (2026-10-08): the first run stopped at a response above the 2 MiB cap. Remaining
        # and truncated queries run once more with a 12 MiB cap; complete responses are never re-requested.
        done = {e['label'] for e in json.loads((CACHE / 'responses/fetch-manifest.json').read_text())['entries']
                if e.get('status') == 200 and not e.get('truncated')}
        f.MAX_BYTES = 12 * 1024 * 1024
        f.requests = lambda: [{'label': i, 'url': u} for i, u in plan['queries'].items() if i not in done]
        f.fetch(CACHE / 'responses-resume')
        return
    got = {}
    for directory in ['responses', 'responses-resume']:
        if not (CACHE / directory / 'fetch-manifest.json').exists():
            continue
        for e in json.loads((CACHE / directory / 'fetch-manifest.json').read_text())['entries']:
            body = (CACHE / directory / e['file']).read_bytes()
            if e.get('status') == 200 and body and not e.get('truncated'):
                got[e['label']] = json.loads(body)
    results = {}
    for status, ids in plan['strata'].items():
        results[status] = {i: evaluate(rows[i], got.get(i)) if i in rows else {'outcome': 'record-missing'} for i in ids}
    summary = {s: {o: sum(r['outcome'] == o for r in res.values()) for o in ['confirmed', 'contradicted', 'notice-without-amount', 'unknown-amount', 'no-notice', 'record-missing']}
               for s, res in results.items()}
    (CACHE / 'results.json').write_text(json.dumps({'summary': summary, 'results': results, 'fetched': len(got)}, indent=2, default=list) + '\n')
    print(json.dumps(summary, indent=1))


if __name__ == '__main__':
    main()
