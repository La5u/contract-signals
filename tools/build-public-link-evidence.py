#!/usr/bin/env python3
"""Hash-bound, offline public evidence ledger; fixed-request private reacquisition."""
import argparse
import datetime
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import subprocess
import time
from urllib.parse import urlsplit
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import canonical, require as check, sha  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ANNOTATIONS = 'research/public-link-observations.json'
LIMIT = 2 * 1024 * 1024
CEILING = 14
CONCLUSIONS = {'reference-pattern-supported-unconfirmed', 'lot-compatible-unconfirmed',
               'disfavored-notice-lot-mapping-not-proven-different-legal-contract'}
B = '/EFORMS/ContractAwardNotice'
N = B + '/ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/efext:EformsExtension/efac:NoticeResult'
NORMAL_FIELDS = {'id', 'contractId', 'lotId', 'cpv', 'amount', 'date', 'publicationDate', 'durationMonths'}
DECODED_SUFFIXES = {
 '/efac:ContractReference/cbc:ID', '/cbc:ID/#text', '/cbc:IssueDate', '/cbc:AwardDate',
 '/efac:LotTender/cbc:ID', '/efac:TenderLot/cbc:ID', '/efac:SettledContract/cbc:ID',
 '/efac:FrameworkAgreementValues/cbc:MaximumValueAmount/#text',
 '/cac:LegalMonetaryTotal/cbc:PayableAmount/#text', '/cac:LegalMonetaryTotal/cbc:PayableAmount/@currencyID',
 '/cac:ProcurementProject/cbc:ID', '/cac:ProcurementProject/cbc:Note/#text',
 '/cac:ProcurementProject/cac:MainCommodityClassification/cbc:ItemClassificationCode/#text',
 '/cac:ProcurementProject/cac:PlannedPeriod/cbc:DurationMeasure/#text',
 '/cac:ProcurementProject/cac:PlannedPeriod/cbc:DurationMeasure/@unitCode',
 '/cac:NoticeDocumentReference/cbc:ID'}

def render(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + '\n'

def pointer(value, path):
    if not path.startswith('/'):
        raise ValueError('invalid JSON pointer')
    for token in path[1:].split('/'):
        token = token.replace('~1', '/').replace('~0', '~')
        value = value[int(token)] if isinstance(value, list) else value[token]
    return value

def allowed_decoded(path):
    if path in {B + '/cbc:IssueDate', B + '/cbc:ContractFolderID'}:
        return True
    for base in [N + '/efac:SettledContract', N + '/efac:LotResult', N + '/efac:LotTender', B + '/cac:ProcurementProjectLot']:
        if path.startswith(base):
            tail = path[len(base):]
            pieces = tail.split('/')
            if len(pieces) > 1 and pieces[1].isdigit():
                tail = '/' + '/'.join(pieces[2:])
            return tail in DECODED_SUFFIXES
    return False

def build(root=ROOT, annotations=None):
    a = annotations if annotations is not None else json.loads((root / ANNOTATIONS).read_text())
    sources = {}
    for name, expected in a['sourceHashes'].items():
        check(name in {'data/contracts.json', 'data/decp-history.json', 'data/decp-cities.json',
                       'data/boamp-raw.json.gz', 'data/boamp-decp-links.json',
                       'research/public-boamp-decp-investigation.md'}, 'unexpected source')
        raw = (root / name).read_bytes()
        check(sha(raw) == expected, 'source hash mismatch: ' + name)
        if name.endswith('.json') or name.endswith('.gz'):
            sources[name] = json.loads(gzip.decompress(raw) if name.endswith('.gz') else raw)
    check(len(a['pairs']) == 9, 'expected nine reviewed pairs')
    links = sources['data/boamp-decp-links.json']['links']
    pairs = []
    for p in a['pairs']:
        check(p['conclusion'] in CONCLUSIONS, 'invalid conclusion')
        check(any(all(x[k] == p[k] for k in ['boampId', 'decpId', 'boampUrl', 'decpUrl'])
                  for x in links), 'pair or official URL mismatch')
        bf, bp = p['normalizedBoampPointer'].split('#')
        df, dp = p['normalizedDecpPointer'].split('#')
        boamp, decp = pointer(sources[bf], bp), pointer(sources[df], dp)
        check(boamp['id'] == p['boampId'] and decp['id'] == p['decpId'], 'normalized ID mismatch')
        check(decp['contractId'] == p['decpContractId'], 'public contract ID mismatch')
        rf, rp = p['rawNoticePointer'].split('#')
        record = pointer(sources[rf], rp)
        decoded_string = record['donnees']
        decoded = json.loads(decoded_string)
        check(pointer(decoded, p['decodedReferencePointer']) == p['publishedReference'], 'decoded reference mismatch')
        check(record['idweb'] == boamp['noticeId'], 'notice ID mismatch')
        fields = []
        for spec in p['fields']:
            scope, path = spec['scope'], spec['pointer']
            if scope == 'decoded':
                check(allowed_decoded(path), 'non-minimal decoded pointer')
                value = pointer(decoded, path)
            elif scope in {'boamp', 'decp'}:
                check(path[1:] in NORMAL_FIELDS, 'non-minimal normalized pointer')
                value = pointer(boamp if scope == 'boamp' else decp, path)
            elif scope == 'raw':
                check(path in {'/dateparution', '/idweb'}, 'non-minimal raw pointer')
                value = pointer(record, path)
            else:
                raise ValueError('invalid field scope')
            check(value is None or isinstance(value, (str, int, float, bool)), 'scalar required')
            check(sha(canonical(value)) == spec['scalarSha256'], 'scalar hash/pointer mismatch')
            if 'excerpt' in spec:
                check(scope == 'decoded' and path.endswith('/cbc:Note/#text') and spec['excerpt'] in value, 'invalid reviewed excerpt')
                value = spec['excerpt']
            fields.append({**spec, 'value': value})
        pairs.append({k: p[k] for k in ['pair', 'boampId', 'decpId', 'conclusion', 'notes', 'boampUrl', 'decpUrl',
                     'normalizedBoampPointer', 'normalizedDecpPointer', 'rawNoticePointer', 'decodedReferencePointer',
                     'publishedReference', 'decpContractId']} | {
                     'confirmed': False, 'linkStatus': 'candidate', 'resolution': None,
                     'rawRecordSha256': sha(canonical(record)),
                     'decodedStringSha256': sha(decoded_string.encode()), 'fields': fields})
    check(len({(p['boampId'], p['decpId']) for p in pairs}) == 9, 'duplicate pair')
    validate_requests(a['liveRequests'])
    return {'schemaVersion': 1, 'confirmed': 0, 'resolved': 0,
            'sourceHashes': a['sourceHashes'], 'snapshotTimes': a['snapshotTimes'],
            'annotationSha256': sha(canonical(a)), 'hashConventions': {
                'source': 'exact file bytes (compressed bytes for gzip)',
                'rawRecordAndScalar': 'UTF-8 sorted-key compact JSON, ensure_ascii=false',
                'decodedString': 'UTF-8 bytes of donnees string before JSON decoding'},
            'liveRequestsLabel': 'recorded live acquisition; not required for offline reproduction',
            'liveRequests': a['liveRequests'], 'pairs': pairs}

def fixed_requests():
    """Independent fixed request inventory, never general-purpose URL fetching."""
    from urllib.parse import urlencode
    requests = []
    for buyer, cid in [('21750001600019', x) for x in ['2024S05075','2024S05079','2025S01590']] + [('21440109300015', x) for x in ['2025F00012','2025F00013','2025F00016']] + [('21750001600019', x) for x in ['2025F02650','2025S02915','2025F02648']]:
        where = "acheteur_id='" + buyer + "'"
        if buyer == '21440109300015':
            where += " AND datenotification >= '2024-01-01' AND datenotification < '2026-01-01'"
        where += " AND id='" + cid + "'"
        params = {'where': where, 'limit': 100}
        if buyer == '21440109300015':
            params['order_by'] = 'datenotification asc,id asc'
        requests.append(('GET', 'https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/decp-2022-marches-valides/records?' + urlencode(params), None))
    for year in [2024, 2025]:
        requests.append(('GET', f'https://data.nantesmetropole.fr/api/explore/v2.1/catalog/datasets/244400404_marches-publics-conclus-{year}-nantes/exports/json', None))
    for ref in ['2024-88480', '20242024S05075', '2025F026500000']:
        requests.append(('POST', 'https://api.ted.europa.eu/v3/notices/search', {'query': f'FT ~ "{ref}"', 'limit': 10, 'fields': ['publication-number','notice-title','notice-identifier'], 'scope': 'ALL', 'checkQuerySyntax': True}))
    return requests

def validate_requests(requests):
    check(len(requests) == CEILING, 'request ceiling/inventory mismatch')
    for r, fixed in zip(requests, fixed_requests()):
        check((r['method'], r['url'], r['requestBody']) == fixed, 'request outside exact host/path/body allowlist')
        u = urlsplit(r['url'])
        check(u.scheme == 'https' and not u.username and not u.fragment and u.port is None, 'unsafe endpoint')
        if u.hostname == 'api.ted.europa.eu':
            check(r.get('searchExecuted') is False and r.get('syntaxOnly') is True,
                  'historical TED requests were syntax-only, not executed searches')
        # Historical excerpts are reviewed source assertions, not fresh acquisitions.
        # Keep their scalar selection as narrow as the opt-in response minimizer.
        fields = r.get('recordedFields', [])
        check(isinstance(fields, list), 'invalid recorded fields')
        prefix = '/results' if u.hostname == 'data.economie.gouv.fr' else ''
        keys = ('id|codecpv|datenotification|datepublicationdonnees|montant|dureemois|formeprix'
                if prefix else 'reference_interne_du_contrat|montant_du_contrat_attribue|'
                'date_de_notification|cpv_principal|duree_maximale_du_marche')
        seen = set()
        for field in fields:
            path = field.get('pointer', '')
            value = field.get('value')
            check(u.hostname != 'api.ted.europa.eu' and
                  re.fullmatch(prefix + r'/[0-9]+/(' + keys + ')', path) is not None,
                  'non-minimal recorded pointer')
            check(path not in seen, 'duplicate recorded pointer')
            seen.add(path)
            check(value is None or isinstance(value, (str, int, float, bool)), 'recorded scalar required')
            check(sha(canonical(value)) == field.get('scalarSha256'), 'recorded scalar checksum mismatch')

def minimize_response(request, body):
    """Select only non-personal reference/amount/classification/date scalars."""
    data = json.loads(body)
    host = urlsplit(request['url']).hostname
    if host == 'data.economie.gouv.fr':
        rows = data['results']
        keys = {'id', 'codecpv', 'datenotification', 'datepublicationdonnees', 'montant', 'dureemois', 'formeprix'}
        prefix = '/results'
    elif host == 'data.nantesmetropole.fr':
        rows = data
        keys = {'reference_interne_du_contrat', 'montant_du_contrat_attribue', 'date_de_notification', 'cpv_principal', 'duree_maximale_du_marche'}
        prefix = ''
    else:
        # Do not copy titles or notices, which may contain incidental personal data.
        total, timed_out = data.get('totalNoticeCount'), data.get('timedOut')
        check(total is None or isinstance(total, int), 'unexpected TED count')
        check(timed_out is None or isinstance(timed_out, bool), 'unexpected TED timeout')
        return {'noticeCount': len(data.get('notices', [])),
                'totalNoticeCount': total, 'timedOut': timed_out}
    check(isinstance(rows, list), 'unexpected response schema')
    return [{'pointer': prefix + '/' + str(i), 'fields': {
        k: v for k, v in row.items() if k in keys and
        (v is None or isinstance(v, (str, int, float, bool)))}} for i, row in enumerate(rows)]


def acquire(request, dest):
    """Stream curl stdout with a hard body bound and enclosing 15-second deadline."""
    command = ['curl', '--disable', '--silent', '--show-error', '--proto', '=https',
               '--proto-redir', '=https', '--max-redirs', '0', '--retry', '0',
               '--connect-timeout', '5', '--max-time', '15', '--max-filesize', str(LIMIT),
               '--request', request['method'], '--write-out', '%{stderr}%{http_code}', request['url']]
    if request['requestBody'] is not None:
        command += ['--header', 'Content-Type: application/json', '--data-binary', canonical(request['requestBody']).decode()]
    start = time.monotonic()
    result = {'retrievedAt': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'failure': None}
    count = 0
    digest = hashlib.sha256()
    with dest.open('xb') as out:
        os.chmod(dest, 0o600)
        # stderr is private, bounded by curl's fixed error output; never publish it.
        with (dest.parent / (dest.name + '.status')).open('xb') as status:
            os.chmod(status.name, 0o600)
            proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=status, env={**os.environ, 'CURL_HOME': str(dest.parent)})
            sel = selectors.DefaultSelector()
            sel.register(proc.stdout, selectors.EVENT_READ)
            try:
                while True:
                    remaining = 15 - (time.monotonic() - start)
                    if remaining <= 0:
                        result['failure'] = 'timeout'
                        break
                    if not sel.select(remaining):
                        result['failure'] = 'timeout'
                        break
                    chunk = os.read(proc.stdout.fileno(), 65536)
                    if not chunk:
                        break
                    if count + len(chunk) > LIMIT:
                        result['failure'] = 'body-limit'
                        break
                    out.write(chunk)
                    digest.update(chunk)
                    count += len(chunk)
                if result['failure']:
                    proc.kill()
                try:
                    code = proc.wait(timeout=max(0.001, 15 - (time.monotonic() - start)))
                except subprocess.TimeoutExpired:
                    proc.kill()
                    code = proc.wait()
                    result['failure'] = 'timeout'
            finally:
                if proc.poll() is None:
                    proc.kill()
                    proc.wait()
                proc.stdout.close()
                sel.close()
    status_text = (dest.parent / (dest.name + '.status')).read_bytes()[-3:].decode(errors='replace')
    result.update({'httpStatus': status_text if status_text.isdigit() else None, 'curlExit': code,
                   'bytes': count, 'bodySha256': digest.hexdigest()})
    if not result['failure']:
        result['failure'] = ('redirect-not-followed' if status_text.startswith('3') else
                             'timeout' if code == 28 else 'body-limit' if code == 63 else
                             'transfer-failed' if code else 'http-failed' if status_text != '200' else None)
    if result['failure'] is None:
        try:
            result['minimized'] = minimize_response(request, dest.read_bytes())
        except (ValueError, KeyError, TypeError, AttributeError):
            result['minimizationFailure'] = 'invalid-json-or-schema'
    return result

def fetch(requests, directory, root=ROOT):
    validate_requests(requests)
    directory = Path(directory).expanduser()
    check(directory.is_absolute(), 'private directory must be absolute')
    resolved = directory.resolve()
    check(not resolved.is_relative_to(root.resolve()), 'raw artifacts must be outside repository')
    # mkdir is exclusive: never reuse prior evidence or follow an existing final symlink.
    directory.mkdir(mode=0o700, parents=False, exist_ok=False)
    os.chmod(directory, 0o700)
    results = []
    for i, request in enumerate(requests):
        try:
            result = acquire(request, directory / f'{i+1:02d}.body')
        except (OSError, ValueError):
            result = {'failure': 'acquisition-failed', 'retrievedAt': datetime.datetime.now(datetime.timezone.utc).isoformat()}
        metadata = {k: request[k] for k in ['method', 'url', 'requestBody']}
        if urlsplit(request['url']).hostname == 'api.ted.europa.eu':
            metadata.update(searchExecuted=False, syntaxOnly=True)
        results.append(metadata | result)
        target = directory / 'manifest.json'
        target.write_text(render(results))
        os.chmod(target, 0o600)
    return results

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'data/public-link-evidence.json')
    parser.add_argument('--fetch', action='store_true')
    parser.add_argument('--private-dir', type=Path)
    args = parser.parse_args()
    if args.fetch and not args.private_dir:
        parser.error('--fetch requires a NEW external --private-dir')
    if args.private_dir and not args.fetch:
        parser.error('--private-dir requires --fetch')
    ledger = build()
    if args.fetch:
        fetch(ledger['liveRequests'], args.private_dir)
    else:
        args.output.write_text(render(ledger))

if __name__ == '__main__':
    main()
