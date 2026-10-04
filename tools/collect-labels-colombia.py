#!/usr/bin/env python3
"""Collect contract-linked OUTCOME labels for the Colombia SECOP II cohort.

Source: datos.gov.co "SECOPII - Multas y Sanciones" (it5q-hg94, CC BY-SA 4.0), joined on the exact
SECOP II contract identifier (id_contrato == contractId). Name matching is never used.

Label target (tri-state, null = unknown, never "clean"):
  contractual_sanction  true  -> an official record of a fine / penalty clause exists for that contract
                        null  -> otherwise (absence of a record is not evidence of a clean contract)

Default mode prints the request plan and touches no network. --fetch performs the requests
(serial, >=1 s apart, hard budget, responses cached outside git so reruns resume).
--from-cache builds the output from the cache only.

Natural persons' names and ID numbers are never written to the output: sanctioned-supplier columns
are dropped and only contract identifiers, dates, types and amounts are kept.
"""
import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = Path.home() / '.cache/contract-signals/labels'
HOST = 'https://www.datos.gov.co'
SANCTIONS = 'it5q-hg94'            # SECOPII - Multas y Sanciones
SANCTIONS_I = '4n4q-k399'          # Multas y Sanciones SECOP I (legacy platform)
CONTRACTS = 'jbjy-vk9h'            # SECOP II - Contratos Electronicos
OTHER_REGISTERS = ('jr8e-e8tu', 'iaeu-rcn6')   # Contraloria fiscal responsibility, Procuraduria SIRI
USER_AGENT = 'contract-signals-label-research/1.0 (public open-data research)'
SANCTION_TYPES = {'Multa', 'Clausula Penal'}
PAGE = 1000
DEFAULT_BUDGET = 600
MIN_INTERVAL = 1.2


class BudgetExceeded(RuntimeError):
    pass


class Fetcher:
    """Serial, throttled, cached HTTP GET with a hard request budget and 429/503 backoff."""

    def __init__(self, cache_dir, budget=DEFAULT_BUDGET, network=False, min_interval=MIN_INTERVAL,
                 opener=None, sleep=time.sleep):
        self.cache_dir = Path(cache_dir)
        self.budget = budget
        self.network = network
        self.min_interval = min_interval
        self.opener = opener or self._urlopen
        self.sleep = sleep
        self.requests = 0
        self.last = 0.0

    @staticmethod
    def _urlopen(url):
        req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT, 'Accept': 'application/json'})
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, r.read()

    def key(self, url):
        return self.cache_dir / (hashlib.sha256(url.encode()).hexdigest()[:32] + '.json')

    def cached(self, url):
        return self.key(url).exists()

    def get(self, url):
        """Return {'body': bytes, 'sha256', 'retrieved_at', 'url', 'cached'}; raises if unavailable."""
        path = self.key(url)
        if path.exists():
            meta = json.loads(path.read_text())
            body = bytes.fromhex(meta['body_hex'])
            return {**{k: meta[k] for k in ('url', 'sha256', 'retrieved_at')}, 'body': body, 'cached': True}
        if not self.network:
            raise FileNotFoundError(f'not cached and network disabled: {url}')
        for attempt in range(4):
            if self.requests >= self.budget:
                raise BudgetExceeded(f'request budget {self.budget} reached; rerun to resume from cache')
            wait = self.min_interval - (time.monotonic() - self.last)
            if wait > 0:
                self.sleep(wait)
            self.requests += 1
            self.last = time.monotonic()
            try:
                status, body = self.opener(url)
            except urllib.error.HTTPError as e:
                if e.code in (429, 503) and attempt < 3:
                    retry = e.headers.get('Retry-After') if e.headers else None
                    self.sleep(min(float(retry) if retry and retry.isdigit() else 5 * 2 ** attempt, 120))
                    continue
                raise
            except (TimeoutError, urllib.error.URLError):
                if attempt < 3:
                    self.sleep(5 * 2 ** attempt)
                    continue
                raise
            break
        meta = {'url': url, 'sha256': hashlib.sha256(body).hexdigest(), 'status': status,
                'retrieved_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
                'body_hex': body.hex()}
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        path.with_suffix('.tmp').write_text(json.dumps(meta))
        path.with_suffix('.tmp').replace(path)
        return {**{k: meta[k] for k in ('url', 'sha256', 'retrieved_at')}, 'body': body, 'cached': False}


def soql(dataset, **params):
    return f'{HOST}/resource/{dataset}.json?' + urllib.parse.urlencode(params)


def view_url(dataset):
    return f'{HOST}/api/views/{dataset}.json'


def cohort_buyers(rows):
    return sorted({r['buyerNit'] for r in rows})


def cohort_buyer_names(rows):
    return sorted({r['buyer'] for r in rows})


def in_list(values):
    return ','.join("'" + v.replace("'", "''") + "'" for v in values)


def parse_view(body):
    d = json.loads(body)
    return {'id': d.get('id'), 'name': d.get('name'), 'attribution': d.get('attribution'),
            'license': (d.get('license') or {}).get('name'), 'licenseLink': (d.get('license') or {}).get('termsLink'),
            'rowsUpdatedAt': d.get('rowsUpdatedAt'), 'columns': [c['fieldName'] for c in d.get('columns', [])]}


def sanction_evidence(rec):
    """Keep only contract-level facts; drop supplier name and supplier identifier columns."""
    return {'dataset': SANCTIONS, 'contract_id': rec.get('id_contrato'), 'process_id': rec.get('id_proceso'),
            'sanction_type': rec.get('tipo_de_sancion'), 'record_type': rec.get('tipo'), 'status': rec.get('estado'),
            'version': rec.get('numero_de_version'), 'event_date': (rec.get('fecha_evento') or '')[:10] or None,
            'amount_cop': rec.get('valor'), 'amount_paid_cop': rec.get('valor_pagado'),
            'act_number': rec.get('numero_de_acto')}


def label_contract(matches):
    """Tri-state: true only for a classified fine / penalty-clause record; otherwise unknown (null)."""
    return {'contractual_sanction': True if any(m['sanction_type'] in SANCTION_TYPES for m in matches) else None}


def join_sanctions(contracts, records):
    by_contract = {}
    for rec in records:
        cid = rec.get('id_contrato')
        by_contract.setdefault(cid, []).append(rec)
    ids = {c['contractId'] for c in contracts}
    rows = []
    for c in contracts:
        ev = [sanction_evidence(r) for r in by_contract.get(c['contractId'], [])]
        rows.append({'dataset': 'colombia-secop2', 'id': c['id'], 'contractId': c['contractId'],
                     'buyerNit': c['buyerNit'], 'signedDate': c.get('date'),
                     'labels': label_contract(ev), 'evidence': ev,
                     'dates': sorted({e['event_date'] for e in ev if e['event_date']})})
    diag = Counter()
    unmatched = Counter()
    for rec in records:
        cid = rec.get('id_contrato') or ''
        if cid in ids:
            diag['records_matched_exact'] += 1
        elif not cid.startswith('CO1.PCCNTR.'):
            unmatched['no_secop2_contract_identifier'] += 1
        else:
            unmatched['contract_not_in_cohort'] += 1
    return rows, dict(diag), dict(unmatched)


def request_plan(buyers, names):
    nit = in_list(buyers)
    return [
        ('metadata', view_url(SANCTIONS)), ('metadata', view_url(SANCTIONS_I)),
        ('metadata', view_url(OTHER_REGISTERS[0])), ('metadata', view_url(OTHER_REGISTERS[1])),
        ('entity-codes', soql(CONTRACTS, **{'$select': 'codigo_entidad,nit_entidad,count(*) as n',
                                            '$group': 'codigo_entidad,nit_entidad',
                                            '$where': f'nit_entidad in ({nit}) and nombre_entidad in ({in_list(names)})'})),
        ('count-secop2-sanctions', soql(SANCTIONS, **{'$select': 'count(*)'})),
        ('secop2-sanctions-page-0', soql(SANCTIONS, **{'$limit': PAGE, '$offset': 0, '$order': ':id'})),
        ('secop1-sanctions-buyers', soql(SANCTIONS_I, **{'$where': f'nit_entidad in ({nit})', '$limit': PAGE})),
    ]


def run(args):
    contracts = json.loads(Path(args.contracts).read_text())
    buyers = cohort_buyers(contracts)
    fetcher = Fetcher(args.cache, budget=args.budget, network=args.fetch)
    plan = request_plan(buyers, cohort_buyer_names(contracts))
    if not args.fetch and not args.from_cache:
        print(f'PLAN (offline, no requests made): cohort {len(contracts)} contracts, buyers {buyers}')
        for name, url in plan:
            print(f'  [{"cached" if fetcher.cached(url) else "to fetch"}] {name}: {url}')
        print('  further pages of secop2-sanctions are requested only while a page is full (1000 rows)')
        print(f'  max requests {args.budget}, spacing >= {MIN_INTERVAL}s; rerun with --fetch to execute')
        return 0
    got = {name: fetcher.get(url) for name, url in plan[4:6]}
    provenance = [{k: v for k, v in fetcher.get(url).items() if k != 'body'} for name, url in plan[:6]]
    views = {url.rsplit('/', 1)[1].removesuffix('.json'): parse_view(fetcher.get(url)['body'])
             for name, url in plan[:4]}
    total = int(json.loads(got['count-secop2-sanctions']['body'])[0]['count'])
    records, pages = [], []
    offset = 0
    while offset < total:
        url = soql(SANCTIONS, **{'$limit': PAGE, '$offset': offset, '$order': ':id'})
        page = fetcher.get(url)
        pages.append({k: v for k, v in page.items() if k != 'body'})
        batch = json.loads(page['body'])
        records += batch
        offset += PAGE
        if len(batch) < PAGE:
            break
    secop1 = fetcher.get(plan[7][1])
    secop1_rows = json.loads(secop1['body'])
    entities = json.loads(got['entity-codes']['body'])
    codes = {e['codigo_entidad'] for e in entities}
    rows, diag, unmatched = join_sanctions(contracts, records)
    in_buyers = [r for r in records if r.get('codigo_entidad_creadora') in codes]
    positives = sum(1 for r in rows if r['labels']['contractual_sanction'] is True)
    out = {
        'target': 'colombia-secop2', 'built_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'cohort': {'file': 'data/colombia-secop2.json', 'contracts': len(contracts), 'buyerNits': buyers,
                   'window': [min(c['date'] for c in contracts), max(c['date'] for c in contracts)]},
        'sources': {
            'secop2_sanctions': {'dataset': SANCTIONS, 'portal': f'{HOST}/d/{SANCTIONS}', 'view': views[SANCTIONS],
                                 'rows_declared': total, 'rows_downloaded': len(records), 'pages': pages},
            'secop1_sanctions_context': {'dataset': SANCTIONS_I, 'rows_for_cohort_buyers': len(secop1_rows),
                                         'note': 'SECOP I is the legacy platform; cohort contracts are SECOP II only, so it cannot join.',
                                         'response': {k: v for k, v in secop1.items() if k != 'body'}},
            'other_registers_checked': {k: views[k] for k in (*OTHER_REGISTERS, SANCTIONS_I)},
            'entity_code_lookup': {'dataset': CONTRACTS, 'response': {k: v for k, v in got['entity-codes'].items() if k != 'body'},
                                   'entities': entities},
        },
        'provenance': provenance,
        'join': {'key': 'it5q-hg94.id_contrato == cohort contractId (exact string)', 'name_matching': False,
                 'sanction_records_total': len(records), **diag,
                 'records_for_cohort_buyer_entity_codes': len(in_buyers),
                 'cohort_buyer_records': [{'contract_id': r.get('id_contrato'), 'process_id': r.get('id_proceso'),
                                           'event_date': (r.get('fecha_evento') or '')[:10] or None,
                                           'sanction_type': r.get('tipo_de_sancion'), 'estado': r.get('estado')}
                                          for r in in_buyers],
                 'unmatched_reasons': unmatched,
                 'cohort_contracts_with_record': sum(1 for r in rows if r['evidence']),
                 'join_rate_records': (diag.get('records_matched_exact', 0) / len(records)) if records else None,
                 'join_rate_contracts': sum(1 for r in rows if r['evidence']) / len(contracts)},
        'coverage_note': ('The dataset has no buyer NIT column; the cohort buyers were identified through the entity '
                          'code(s) published in the SECOP II contracts dataset for the exact NIT and buyer name '
                          '(NIT 899999061 is shared by many Bogota local mayoralties, hence the name filter). Dataset completeness is not documented by the '
                          'publisher, so contracts without a record stay null, never false.'),
        'other_registers': {
            'jr8e-e8tu': 'Contraloria fiscal-responsibility register: person/NIT and resolution only, no contract identifier; not joinable.',
            'iaeu-rcn6': 'Procuraduria SIRI disciplinary records: sanctioned natural persons, no contract identifier; not joinable and not collected.'},
        'summary': {'targets': {'contractual_sanction': {'true': positives, 'false': 0,
                                                         'null': len(rows) - positives}},
                    'requests_made_this_run': fetcher.requests},
        'rows': rows,
    }
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n')
    print(f'wrote {args.output}: {positives} positives of {len(rows)}; requests this run {fetcher.requests}')
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--contracts', default=str(ROOT / 'data/colombia-secop2.json'))
    p.add_argument('--output', default=str(ROOT / 'research/labels/colombia.json'))
    p.add_argument('--cache', default=str(CACHE / 'colombia'))
    p.add_argument('--budget', type=int, default=DEFAULT_BUDGET)
    p.add_argument('--fetch', action='store_true', help='perform network requests (default: offline plan)')
    p.add_argument('--from-cache', action='store_true', help='build output from cached responses only')
    return run(p.parse_args(argv))


if __name__ == '__main__':
    sys.exit(main())
