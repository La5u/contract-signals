#!/usr/bin/env python3
"""Research only: court challenges to Romanian Competition Council decisions, from the courts' public portal.

For each company sanctioned in a decision (romania-cc/decisions.jsonl), asks the portal.just.ro web
service (portalquery.just.ro, CautareDosare, party-name search) for cases at the Bucharest Court of Appeal
and the High Court in which the Competition Council is also a party, from the decision date on. Serial,
spaced, cached (romania-cc/court/<hash>.xml). Writes romania-cc/court-cases.jsonl: one line per case with
parties (organisations only), object, hearings' outcome summaries and appeal routes. Interpretation
(final / pending / annulled) is a separate review step.
"""
import hashlib
import json
import re
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

BASE = Path.home() / '.cache/contract-signals/romania-cc'
URL = 'http://portalquery.just.ro/query.asmx'
NS = {'s': 'http://schemas.xmlsoap.org/soap/envelope/', 'p': 'portalquery.just.ro'}
COURTS = ['CurteadeApelBUCURESTI']   # the High Court is not in this portal (HTTP 500); its appeals show as routes
INTERVAL = 3.0
BODY = ('<?xml version="1.0" encoding="utf-8"?><soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
        '<soap:Body><CautareDosare xmlns="portalquery.just.ro"><numeParte>{party}</numeParte><institutie>{court}</institutie>'
        '<dataStart>{start}T00:00:00</dataStart><dataStop>2026-10-14T00:00:00</dataStop></CautareDosare></soap:Body></soap:Envelope>')


def query(party, court, start):
    body = BODY.format(party=party.replace('&', '&amp;').replace('<', ''), court=court, start=start)
    path = BASE / 'court' / (hashlib.sha256(body.encode()).hexdigest()[:24] + '.xml')
    if path.exists():
        return path.read_bytes()
    req = urllib.request.Request(URL, data=body.encode(), headers={
        'Content-Type': 'text/xml; charset=utf-8', 'SOAPAction': '"portalquery.just.ro/CautareDosare"',
        'User-Agent': 'contract-signals-label-research/1.0'})
    with urllib.request.urlopen(req, timeout=180) as r:
        data = r.read()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    time.sleep(INTERVAL)
    return data


def text(el, tag):
    x = el.find(f'p:{tag}', NS)
    return x.text.strip() if x is not None and x.text else None


def cases(xml):
    root = ET.fromstring(xml)
    for d in root.iter(f'{{{NS["p"]}}}Dosar'):
        parties = [(text(p, 'nume'), text(p, 'calitateParte')) for p in d.iter(f'{{{NS["p"]}}}DosarParte')]
        hearings = [{'date': (text(h, 'data') or '')[:10], 'solution': text(h, 'solutie'), 'summary': (text(h, 'solutieSumar') or '')[:600]}
                    for h in d.iter(f'{{{NS["p"]}}}DosarSedinta')]
        routes = [{'date': (text(c, 'dataDeclarare') or '')[:10], 'party': text(c, 'parteDeclaratoare'), 'type': text(c, 'tipCaleAtac')}
                  for c in d.iter(f'{{{NS["p"]}}}DosarCaleAtac')]
        yield {'number': text(d, 'numar'), 'court': text(d, 'institutie'), 'object': text(d, 'obiect'), 'stage': text(d, 'stadiuProcesualNume'),
               'date': (text(d, 'data') or '')[:10], 'parties': parties, 'hearings': hearings, 'appeals': routes}


def company_name(name):
    # The portal matches on name fragments; drop legal-form suffixes and punctuation.
    return re.sub(r'\b(S\.?C\.?|S\.?R\.?L\.?|S\.?A\.?|SRL|SA)\b', ' ', name or '', flags=re.I).replace('"', ' ').strip()


def main():
    decisions = [json.loads(l) for l in (BASE / 'decisions.jsonl').read_text().splitlines() if l.strip()]
    out, seen = [], set()
    for d in decisions:
        year = (d.get('date') or d.get('number') or '')[-4:]
        start = f'{year}-01-01' if re.fullmatch(r'20\d\d', year) else '2010-01-01'
        for c in d.get('companies') or []:
            party = company_name(c.get('name'))
            if not party:
                continue
            for court in COURTS:
                try:
                    xml = query(party, court, start)
                except Exception as e:
                    print('error', party, court, e, flush=True)
                    continue
                for case in cases(xml):
                    names = ' '.join((n or '') for n, _ in case['parties']).upper()
                    if 'CONCUREN' not in names or (case['number'], d['number']) in seen:
                        continue
                    seen.add((case['number'], d['number']))
                    out.append({'decision': d['number'], 'company_cui': c.get('cui'), **case,
                                'parties': [n for n, _ in case['parties']]})
            print(d['number'], party, len(out), flush=True)
    (BASE / 'court-cases.jsonl').write_text(''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in out))
    print(f'{len(out)} cases with the Council as a party', flush=True)


if __name__ == '__main__':
    main()
