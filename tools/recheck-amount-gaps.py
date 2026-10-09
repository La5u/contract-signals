#!/usr/bin/env python3
"""Bounded current-source research. Default: freeze a private plan, no network.

--fetch freezes a new plan before at most three serial requests. No updates to
published data, exports, attachments, credentials, redirects or retries.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
CACHE = Path.home() / '.cache/contract-signals'
QUEUE = CACHE / 'missing-amounts-review/review.jsonl'
BOAMP = 'https://www.boamp.fr/api/explore/v2.1/catalog/datasets/boamp/records'
COLOMBIA = 'https://www.datos.gov.co/resource/jbjy-vk9h.json'
MAX_BYTES = 2 * 1024 * 1024
SELECTIONS = (('boamp', 'raw_source_missing'), ('boamp', 'raw_source_zero'),
              ('colombia', 'raw_source_zero'))


def load_review():
    spec = importlib.util.spec_from_file_location('gap_review', ROOT / 'tools/review-missing-amounts.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


REVIEW = load_review()


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def private_json(path, value):
    blob = (json.dumps(value, indent=2, ensure_ascii=True, allow_nan=False) + '\n').encode()
    private_bytes(path, blob)


def private_bytes(path, blob):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(blob)
        stream.flush()
        os.fsync(stream.fileno())


def private_run():
    # Fixed cache only; never accept a repository/serve output directory.
    base = CACHE / 'current-amount-recheck'
    for path in (CACHE.parent, CACHE, base):
        if path.is_symlink():
            raise ValueError('Symlinked cache directories are not allowed')
    base.mkdir(parents=True, exist_ok=True, mode=0o700)
    resolved = base.resolve()
    if ROOT == resolved or ROOT in resolved.parents or not resolved.is_relative_to(Path.home().resolve() / '.cache'):
        raise ValueError('Output must remain in private home cache, outside repository')
    base.chmod(0o700)
    directory = Path(tempfile.mkdtemp(prefix='run-', dir=base))
    directory.chmod(0o700)
    return directory


def url_for(dataset, row):
    if dataset == 'boamp':
        identity = row['noticeId']
        if not isinstance(identity, str) or not identity or any(c not in '0123456789-' for c in identity):
            raise ValueError('Invalid exact BOAMP notice ID')
        return BOAMP + '?' + urllib.parse.urlencode({'where': f'idweb="{identity}"', 'limit': 2})
    identity = row['contractId']
    if not isinstance(identity, str) or not identity or any(ord(c) < 32 for c in identity):
        raise ValueError('Invalid full Colombia contract ID')
    return COLOMBIA + '?' + urllib.parse.urlencode({
        '$select': 'id_contrato,proceso_de_compra,valor_del_contrato,estado_contrato',
        '$where': "id_contrato = '" + identity.replace("'", "''") + "'", '$limit': 2})


def boamp_identity(row, records):
    """Supplement the offline helper with exact result and winning-tender IDs."""
    many, text = REVIEW.Review.many, REVIEW.Review.text
    identities = []
    for record in records:
        if record.get('idweb') != row.get('noticeId'):
            continue
        notice = json.loads(record['donnees']).get('EFORMS', {}).get('ContractAwardNotice', {})
        for ext in many(notice.get('ext:UBLExtensions', {}).get('ext:UBLExtension')):
            result = ext.get('ext:ExtensionContent', {}).get('efext:EformsExtension', {}).get('efac:NoticeResult')
            for nr in many(result):
                for lot in many(nr.get('efac:LotResult')):
                    if any(text(x.get('cbc:ID')) == row['lotId'] for x in many(lot.get('efac:TenderLot'))):
                        identities.append({'result_id': text(lot.get('cbc:ID')),
                                           'tender_ids': [text(x.get('cbc:ID')) for x in many(lot.get('efac:LotTender'))],
                                           'contract_ids': [text(x.get('cbc:ID')) for x in many(lot.get('efac:SettledContract'))]})
    if len(identities) != 1 or not identities[0]['result_id'] or len(identities[0]['tender_ids']) != 1 or not identities[0]['tender_ids'][0]:
        raise ValueError('Original/current BOAMP exact result/tender identity unresolved')
    return identities[0]


def freeze(queue_blob, normalized, helper):
    queue = [json.loads(line) for line in queue_blob.splitlines() if line.strip()]
    entries = []
    for dataset, status in SELECTIONS:
        selected = sorted((x for x in queue if x['dataset'] == dataset and x['status'] == status), key=lambda x: x['id'])
        if not selected:
            raise ValueError('Preregistered stratum missing')
        entry = selected[0]
        rows = [r for r in normalized[dataset] if r.get('id') == entry['id']]
        if len(rows) != 1:
            raise ValueError('Normalized ID is not unique')
        # Store only identity/amount fields, never buyer/supplier/contact text.
        row = {k: rows[0].get(k) for k in ('id', 'noticeId', 'lotId', 'contractId', 'processId', 'amount', 'currency')}
        original = helper.reconcile(dataset, row)
        if original['status'] != status or original['conflicts'] or original['exact_match_count'] != 1:
            raise ValueError('Accuracy review no longer agrees with retained source')
        item = {'dataset': dataset, 'review_status': status, 'row': row,
                'original_review': entry, 'original_reconciled': original, 'url': url_for(dataset, row)}
        if dataset == 'boamp':
            raw, _ = helper.json_source('data/boamp-raw.json.gz')
            item['original_identity'] = boamp_identity(row, raw['records'])
        entries.append(item)
    return {'schema_version': 1, 'created_utc': utc(), 'queue_sha256': sha(queue_blob),
            'policy': {'max_requests': 3, 'timeout_seconds': 15, 'delay_seconds': 2,
                       'max_response_bytes': MAX_BYTES, 'redirects': False, 'retries': 0,
                       'updates': False}, 'entries': entries}


def compare(item, payload):
    row, dataset = item['row'], item['dataset']
    conflicts, values, sources = [], [], []
    if dataset == 'boamp':
        records = payload['results']
        if len(records) != 1 or records[0].get('idweb') != row['noticeId'] or payload.get('total_count') != 1:
            conflicts.append('current_notice_not_exact_unique')
        helper = REVIEW.Review(ROOT)
        digest = sha(json.dumps(records, sort_keys=True).encode())
        helper.indexes['data/boamp-raw.json.gz'] = ({(row['noticeId'],): list(enumerate(records))}, digest)
        matches = helper.boamp_values(row, sources, values, conflicts)
        try:
            if boamp_identity(row, records) != item['original_identity']:
                conflicts.append('original_result_tender_identity_changed')
        except (ValueError, KeyError, TypeError):
            conflicts.append('current_result_tender_identity_unresolved')
    else:
        matches = len(payload)
        for i, record in enumerate(payload):
            if record.get('id_contrato') != row['contractId'] or record.get('proceso_de_compra') != row['processId']:
                conflicts.append('current_contract_process_identity_mismatch')
            values.append(REVIEW.evidence(f'/{i}/valor_del_contrato', record.get('valor_del_contrato'),
                                          'secop_contract', 'COP', record.get('estado_contrato')))
    status, candidate = REVIEW.decide(row, matches, values, conflicts)
    # This is current research, NOT an importer-loss conclusion.
    return {'dataset': dataset, 'id': row['id'], 'status': 'current_positive_candidate' if candidate else status,
            'candidate_only': candidate, 'conflicts': sorted(set(conflicts)),
            'exact_match_count': matches, 'current_source_values': values,
            'original_source_values': item['original_reconciled']['source_values'],
            'published_currency': row['currency'], 'published_amount': row['amount']}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request(url):
    # ProxyHandler({}) avoids ambient proxy credentials; never use environment tokens.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    req = urllib.request.Request(url, headers={'Accept': 'application/json', 'Accept-Encoding': 'identity',
                                             'User-Agent': 'contract-signals-bounded-recheck/1.0'})
    try:
        response = opener.open(req, timeout=15)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        blob = response.read(MAX_BYTES)
        return response.code, blob


def fetch_plan(plan, directory, requester=request, sleeper=time.sleep):
    # Persisted plan is the only request input; no reselection during fetch.
    outcomes = []
    for i, item in enumerate(plan['entries']):
        if i >= 3:
            raise ValueError('Request bound exceeded')
        if i:
            sleeper(2)
        meta = {'url': item['url'], 'request_started_utc': utc(), 'dataset': item['dataset']}
        try:
            code, blob = requester(item['url'])
            meta.update({'retrieved_utc': utc(), 'http_status': code, 'bytes': len(blob),
                         'sha256': sha(blob), 'response_file': f'response-{i}.bin'})
            private_bytes(directory / meta['response_file'], blob)
            if len(blob) >= MAX_BYTES:
                raise ValueError('Response reached 2 MiB cap; retained bounded prefix only')
            if code != 200:
                raise ValueError(f'HTTP {code}; stopped without redirect or retry')
            result = compare(item, json.loads(blob))
            meta['comparison'] = result
            outcomes.append(meta)
            private_json(directory / f'retrieval-{i}.json', meta)
            if result['conflicts'] or result['exact_match_count'] != 1:
                break
        except Exception as error:
            # Error text/URLs remain private. Stdout is counts only.
            meta.update({'failed_utc': utc(), 'failure_type': type(error).__name__, 'failure': str(error)})
            outcomes.append(meta)
            private_json(directory / f'retrieval-{i}.json', meta)
            break
    summary = {'planned': len(plan['entries']), 'attempted': len(outcomes),
               'completed': sum('comparison' in o for o in outcomes),
               'failed': sum('failure' in o for o in outcomes),
               'unattempted': len(plan['entries']) - len(outcomes),
               'candidates': sum(o.get('comparison', {}).get('candidate_only', False) for o in outcomes),
               'statuses': dict(Counter(o['comparison']['status'] for o in outcomes if 'comparison' in o)),
               'identity_conflicts': sum(bool(o.get('comparison', {}).get('conflicts')) for o in outcomes)}
    private_json(directory / 'summary.json', summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fetch', action='store_true', help='Authorize bounded serial official API recheck')
    args = parser.parse_args()
    queue_blob = QUEUE.read_bytes()
    paths = {'boamp': ROOT / 'data/contracts.json', 'colombia': ROOT / 'data/colombia-secop2.json'}
    blobs = {key: path.read_bytes() for key, path in paths.items()}
    plan = freeze(queue_blob, {key: json.loads(blob) for key, blob in blobs.items()}, REVIEW.Review(ROOT))
    plan['normalized_sha256'] = {key: sha(blob) for key, blob in blobs.items()}
    directory = private_run()
    private_json(directory / 'plan.json', plan)
    # Round trip the durable frozen plan before any network activity.
    plan = json.loads((directory / 'plan.json').read_bytes())
    summary = fetch_plan(plan, directory) if args.fetch else {'planned': 3, 'attempted': 0, 'network': False}
    print(json.dumps(summary, sort_keys=True))
    return 1 if summary.get('failed') or summary.get('identity_conflicts') or summary.get('unattempted') else 0


if __name__ == '__main__':
    raise SystemExit(main())
