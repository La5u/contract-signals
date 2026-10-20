#!/usr/bin/env python3
"""Offline exact TED investigation; opt-in bounded acquisition to a NEW private directory.

No titles, contacts or free text are exported. Search hits are discovery, never a
BOAMP/DECP crosswalk. XML root notice UUID AND VersionID establish version identity.
"""
import argparse
import datetime as dt
import gzip
import json
import os
from pathlib import Path
import re
import selectors
import subprocess
import time
import xml.etree.ElementTree as ET
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import text as scalar, sha  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
TARGETS = ('25-21317', '25-21329', '25-37616', '25-45958', '25-47556')
API = 'https://api.ted.europa.eu/v3/notices/search'
DOC = 'https://docs.ted.europa.eu/api/latest/search.html'
LIMIT = 2 * 1024 * 1024
PUB = re.compile(r'[1-9][0-9]{0,5}-20[0-9]{2}')
UUID = re.compile(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', re.I)
B = '/EFORMS/ContractAwardNotice'


def walk(v, p=''):
    if isinstance(v, dict):
        for k, x in v.items():
            yield from walk(x, p + '/' + k.replace('~', '~0').replace('/', '~1'))
    elif isinstance(v, list):
        for i, x in enumerate(v):
            yield from walk(x, p + '/' + str(i))
    else:
        yield p, v


def inventory(path):
    blob = path.read_bytes()
    data = json.loads(gzip.decompress(blob))
    out = []
    for rid in TARGETS:
        matches = [(i, r) for i, r in enumerate(data['records']) if r['idweb'] == rid]
        if len(matches) != 1:
            raise ValueError('target must occur exactly once: ' + rid)
        i, r = matches[0]
        n = json.loads(r['donnees'])['EFORMS']['ContractAwardNotice']
        fields = []
        for p, v in walk(n, B):
            header = p in {B + '/cbc:ID/#text', B + '/cbc:VersionID', B + '/cbc:ContractFolderID', B + '/cbc:IssueDate'}
            reference = '/cac:NoticeDocumentReference/' in p or '/efac:ContractReference/' in p
            date = '/efac:SettledContract/' in p and p.endswith(('/cbc:IssueDate', '/cbc:AwardDate'))
            contract_id = '/efac:SettledContract/' in p and p.endswith(('/cbc:ID', '/cbc:ID/#text'))
            if header or reference or date or contract_id:
                fields.append({'pointer': p, 'value': v})
        for p, v in walk(json.loads(r['gestion'])):
            if p.startswith('/REFERENCE/') and p.endswith('/IDWEB'):
                fields.append({'pointer': p, 'container': 'decoded gestion', 'value': v})
        uid, proc = scalar(n['cbc:ID']), scalar(n['cbc:ContractFolderID'])
        if not UUID.fullmatch(uid) or not UUID.fullmatch(proc):
            raise ValueError('invalid source UUID')
        out.append({'boampId': rid, 'recordPointer': '/records/' + str(i),
                    'url': 'https://www.boamp.fr/pages/avis/?q=idweb:' + rid,
                    'noticeUUID': uid, 'procedureUUID': proc, 'version': scalar(n['cbc:VersionID']),
                    'boampPublicationDate': r['dateparution'], 'fields': fields,
                    'publishedAwardTEDNumber': None})
    return {'path': 'data/boamp-raw.json.gz', 'sha256': sha(blob),
            'snapshotRetrievedAt': data.get('retrievedAt'), 'notices': out}


def plan(source):
    # References under NoticeDocumentReference are predecessors, NOT the award's
    # publication number. 00000/000000-2025 are placeholders, not publications.
    terms = [f'(notice-identifier="{n["noticeUUID"]}" OR procedure-identifier="{n["procedureUUID"]}")'
             for n in source['notices']]
    return [{'kind': 'search', 'boampId': 'cohort', 'method': 'POST', 'url': API,
             'requestBody': {'query': ' OR '.join(terms),
                             'fields': ['publication-number', 'notice-identifier', 'procedure-identifier', 'publication-date'],
                             'scope': 'ALL', 'limit': 10, 'page': 1, 'checkQuerySyntax': False,
                             'onlyLatestVersions': False}}]


def acquire(req, dest):
    """No redirects/retries; hard elapsed-time and streamed body limits."""
    cmd = ['curl', '--disable', '--silent', '--proto', '=https', '--max-redirs', '0',
           '--retry', '0', '--connect-timeout', '5', '--max-time', '15',
           '--max-filesize', str(LIMIT), '--request', req['method'],
           '--write-out', '%{stderr}%{http_code}', req['url']]
    if req['requestBody'] is not None:
        cmd += ['--header', 'Content-Type: application/json', '--data-binary', json.dumps(req['requestBody'])]
    meta = {'retrievedAt': dt.datetime.now(dt.timezone.utc).isoformat(), 'failure': None}
    start, count = time.monotonic(), 0
    with dest.open('xb') as out, dest.with_suffix('.status').open('xb') as err:
        os.chmod(dest, 0o600)
        os.chmod(err.name, 0o600)
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=err)
        sel = selectors.DefaultSelector()
        sel.register(proc.stdout, selectors.EVENT_READ)
        try:
            while True:
                remaining = 15 - (time.monotonic() - start)
                if remaining <= 0 or not sel.select(remaining):
                    meta['failure'] = 'timeout'
                    break
                chunk = os.read(proc.stdout.fileno(), 65536)
                if not chunk:
                    break
                if count + len(chunk) > LIMIT:
                    meta['failure'] = 'body-limit'
                    break
                out.write(chunk)
                count += len(chunk)
            if meta['failure']:
                proc.kill()
            try:
                code = proc.wait(timeout=max(.001, 15 - (time.monotonic() - start)))
            except subprocess.TimeoutExpired:
                proc.kill()
                code = proc.wait()
                meta['failure'] = 'timeout'
        finally:
            sel.close()
            proc.stdout.close()
            if proc.poll() is None:
                proc.kill()
                proc.wait()
    status = dest.with_suffix('.status').read_text().strip()
    meta.update(httpStatus=status if re.fullmatch(r'\d{3}', status) else None,
                bytes=count, bodySha256=sha(dest.read_bytes()), curlExit=code)
    if code or status != '200':
        meta['failure'] = meta['failure'] or 'http-or-transfer-failed'
    return meta


def search_evidence(blob):
    d = json.loads(blob)
    rows = d.get('notices', [])
    if not isinstance(rows, list):
        raise ValueError('search schema')
    keys = {'publication-number', 'notice-identifier', 'procedure-identifier', 'publication-date'}
    fields = [{'pointer': '/notices/' + str(i) + '/' + k, 'value': v}
              for i, row in enumerate(rows) for k, v in row.items()
              if k in keys and isinstance(v, (str, int))]
    return {'noticeCount': len(rows), 'totalNoticeCount': d.get('totalNoticeCount'),
            'timedOut': d.get('timedOut'), 'fields': fields}


def xml_evidence(blob, expected):
    if b'<!DOCTYPE' in blob.upper() or b'<!ENTITY' in blob.upper():
        raise ValueError('DTD not allowed')
    root = ET.fromstring(blob)
    fields = []
    def visit(e, p, parent_tag=None):
        tag = e.tag.rsplit('}', 1)[-1]
        # Paths use expanded namespace names and 1-based sibling indices.
        if e.text and e.text.strip():
            header = e in list(root) and tag in {'ID', 'VersionID', 'ContractFolderID', 'IssueDate'}
            allowed = header or tag in {'PublicationDate', 'NoticePublicationID'} or (
                parent_tag in {'ContractReference', 'NoticeDocumentReference', 'SettledContract'}
                and tag in {'ID', 'IssueDate', 'AwardDate'})
            if allowed:
                fields.append({'pointer': p, 'value': e.text.strip()})
        counts = {}
        for child in e:
            counts[child.tag] = counts.get(child.tag, 0) + 1
            visit(child, p + '/' + child.tag + '[' + str(counts[child.tag]) + ']', tag)
    visit(root, '/' + root.tag + '[1]')
    def direct(name):
        matches = [e for e in root if e.tag.rsplit('}', 1)[-1] == name]
        return (matches[0].text or '').strip() if len(matches) == 1 else None
    exact = (root.tag.rsplit('}', 1)[-1] == 'ContractAwardNotice' and
             direct('ID') == expected['noticeUUID'] and direct('VersionID') == expected['version'] and
             direct('ContractFolderID') == expected['procedureUUID'])
    return {'exactAwardVersion': exact, 'fields': fields,
            'crosswalkStatus': 'not-established', 'exactCrosswalkForReview': False}


def public_xml_identity(fields, expected):
    """Recheck notice identity from minimized direct XML-header scalars."""
    values = {key: [] for key in ('ID', 'VersionID', 'ContractFolderID')}
    roots = set()
    for field in fields:
        path = field.get('pointer', '')
        if path.count('/') != 2:
            continue
        root, tail = path[1:].split('/')
        match = re.fullmatch(r'(?:\{[^}]+\})?(ID|VersionID|ContractFolderID)\[[0-9]+\]', tail)
        if match:
            roots.add(root)
            values[match[1]].append(field.get('value'))
    return (len(roots) == 1 and next(iter(roots)).rsplit('}', 1)[-1] == 'ContractAwardNotice[1]' and
            all(len(v) == 1 for v in values.values()) and
            values['ID'][0] == expected['noticeUUID'] and
            values['VersionID'][0] == expected['version'] and
            values['ContractFolderID'][0] == expected['procedureUUID'])


def discoveries(source, requests):
    out = []
    for req in requests:
        if not req.get('searchExecuted') or 'evidence' not in req:
            continue
        rows = {}
        for f in req['evidence']['fields']:
            parts = f['pointer'].split('/')
            rows.setdefault(parts[2], {})[parts[3]] = f['value']
        for i, row in rows.items():
            for n in source['notices']:
                if row.get('procedure-identifier') != n['procedureUUID']:
                    continue
                exact = row.get('notice-identifier') == n['noticeUUID']
                out.append({'boampId': n['boampId'], 'publicationNumber': row['publication-number'],
                            'publicationDate': row.get('publication-date'),
                            'noticeUUID': row.get('notice-identifier'),
                            'procedureUUID': row.get('procedure-identifier'),
                            'searchPointer': '/notices/' + i,
                            'responseSha256': req['bodySha256'],
                            'relation': 'exact-award-notice-UUID' if exact else 'same-procedure-other-notice',
                            'expectedBOAMPVersion': n['version'] if exact else None,
                            'tedVersionVerified': False,
                            'xmlURL': f'https://ted.europa.eu/en/notice/{row["publication-number"]}/xml',
                            'xmlFetched': False, 'exactCrosswalkForReview': False})
    for hit in out:
        for req in requests:
            if req['kind'] == 'xml' and req.get('publicationNumber') == hit['publicationNumber']:
                hit['xmlFetched'] = not req.get('failure')
                hit['tedVersionVerified'] = req.get('evidence', {}).get('exactAwardVersion', False)
    return out


def process(source, entries, directory):
    if len(entries) > 12:
        raise ValueError('attempt ceiling exceeded')
    results = []
    byid = {n['boampId']: n for n in source['notices']}
    for e in entries:
        item = dict(e)
        item['searchExecuted'] = (e['kind'] == 'search' and
                                  not e['requestBody'].get('checkQuerySyntax', False) and
                                  not e.get('failure'))
        if not e.get('failure') and e['kind'] != 'documentation':
            if Path(e['file']).name != e['file']:
                raise ValueError('cache filename must be a basename')
            blob = (directory / e['file']).read_bytes()
            if len(blob) > LIMIT or sha(blob) != e['bodySha256']:
                raise ValueError('cache body mismatch')
            try:
                item['evidence'] = (search_evidence(blob) if e['kind'] == 'search'
                                    else xml_evidence(blob, byid[e['boampId']]))
            except (ValueError, ET.ParseError, KeyError):
                item['processingFailure'] = 'invalid-response-schema'
        item.pop('file', None)
        results.append(item)
    return {'schemaVersion': 1, 'source': source, 'plan': plan(source), 'requests': results,
            'discoveries': discoveries(source, results),
            'limits': {'attemptCeiling': 12, 'secondsPerRequest': 15, 'bytesPerBody': LIMIT,
                       'redirects': 0, 'retries': 0},
            'exactCrosswalkForReview': False,
            'conclusion': 'No explicit buyer + full notice reference + DECP identifier crosswalk established.'}


def fetch(source, directory, budget):
    if not 1 <= budget <= 12:
        raise ValueError('attempt budget must be 1..12')
    directory = directory.expanduser().resolve()
    if directory == ROOT or ROOT in directory.parents:
        raise ValueError('private directory must be outside repository')
    directory.mkdir(mode=0o700, parents=True, exist_ok=False)
    entries = []
    queue = plan(source)
    seen = set()
    while queue and len(entries) < budget:
        req = queue.pop(0)
        filename = str(len(entries) + 1) + '.body'
        e = {**req, **acquire(req, directory / filename), 'file': filename}
        entries.append(e)
        manifest = {'source': source, 'budget': budget, 'entries': entries}
        path = directory / 'manifest.json'
        path.write_text(json.dumps(manifest, indent=2) + '\n')
        os.chmod(path, 0o600)
        if req['kind'] == 'search' and not e['failure']:
            try:
                rows = json.loads((directory / filename).read_bytes()).get('notices', [])
                for row in rows:
                    pub = row.get('publication-number', '')
                    if isinstance(pub, str) and PUB.fullmatch(pub) and pub not in seen:
                        seen.add(pub)
                        matched = [n for n in source['notices']
                                   if row.get('notice-identifier') == n['noticeUUID'] and
                                   row.get('procedure-identifier') == n['procedureUUID']]
                        if len(matched) != 1:
                            continue
                        queue.append({'kind': 'xml', 'boampId': matched[0]['boampId'], 'method': 'GET',
                                      'url': f'https://ted.europa.eu/en/notice/{pub}/xml', 'requestBody': None,
                                      'publicationNumber': pub})
            except (ValueError, AttributeError):
                pass
    return process(source, entries, directory)


def fetch_xml_from(source, prior, directory, budget):
    """Separately accounted follow-up: at most five already-discovered awards.

    Never rerun a search or fetch a predecessor. The original 12 attempts remain
    visible alongside the five-attempt follow-up, rather than resetting history.
    """
    replay_public(prior)
    if prior['source'] != source or len(prior['requests']) != 12 or not 1 <= budget <= 5:
        raise ValueError('XML follow-up requires current source, initial 12-request ledger and budget 1..5')
    hits = [h for h in prior['discoveries'] if h['relation'] == 'exact-award-notice-UUID']
    if len(hits) != 5 or len({h['boampId'] for h in hits}) != 5 or len({h['publicationNumber'] for h in hits}) != 5:
        raise ValueError('Expected five unique exact award discoveries')
    directory = directory.expanduser().absolute()
    if any(p.is_symlink() for p in (directory, *directory.parents)) or directory.resolve().is_relative_to(ROOT):
        raise ValueError('Private follow-up must be outside repository, without symlinks')
    directory.mkdir(mode=0o700, parents=True, exist_ok=False)
    entries = []
    for hit in hits[:budget]:
        pub = hit['publicationNumber']
        if not PUB.fullmatch(pub):
            raise ValueError('Invalid TED publication number')
        req = {'kind': 'xml', 'boampId': hit['boampId'], 'method': 'GET',
               'url': f'https://ted.europa.eu/en/notice/{pub}/xml', 'requestBody': None,
               'publicationNumber': pub}
        filename = str(len(entries) + 1) + '.body'
        try:
            metadata = acquire(req, directory / filename)
        except OSError:
            metadata = {'failure': 'acquisition-failed', 'retrievedAt': dt.datetime.now(dt.timezone.utc).isoformat()}
        entries.append({**req, **metadata, 'file': filename})
        manifest = {'source': source, 'budget': budget, 'entries': entries,
                    'priorLedgerSha256': sha(json.dumps(prior, sort_keys=True, ensure_ascii=False).encode())}
        path = directory / 'manifest.json'
        path.write_text(json.dumps(manifest, indent=2) + '\n')
        os.chmod(path, 0o600)
    followup = process(source, entries, directory)
    results = prior['requests'] + followup['requests']
    return {**prior, 'requests': results, 'discoveries': discoveries(source, results),
            'limits': {**prior['limits'], 'attemptCeiling': 17},
            'requestAccounting': {'initialInvestigationAttempts': 12, 'followupXMLAttempts': len(entries),
                                  'followupXMLCeiling': 5, 'totalAttempts': len(results)},
            'priorDiscoveryLedgerSha256': sha(json.dumps(prior, sort_keys=True, ensure_ascii=False).encode())}


def replay_public(ledger):
    """Recompute identity discovery from public scalars, without raw/private files."""
    ceiling = ledger.get('limits', {}).get('attemptCeiling', 12)
    if ledger['schemaVersion'] != 1 or ceiling not in (12, 17) or len(ledger['requests']) > ceiling:
        raise ValueError('invalid public ledger')
    if ceiling == 17:
        accounting = ledger.get('requestAccounting', {})
        followup = accounting.get('followupXMLAttempts', -1)
        if (accounting.get('initialInvestigationAttempts') != 12 or
            accounting.get('followupXMLCeiling') != 5 or not 1 <= followup <= 5 or
            accounting.get('totalAttempts') != len(ledger['requests']) or
            len(ledger['requests']) != 12 + followup or
            any(r['kind'] != 'xml' for r in ledger['requests'][12:])):
            raise ValueError('invalid separately accounted XML follow-up')
    if tuple(n['boampId'] for n in ledger['source']['notices']) != TARGETS:
        raise ValueError('unexpected targets')
    byid = {n['boampId']: n for n in ledger['source']['notices']}
    for req in ledger['requests']:
        if req['kind'] == 'xml':
            pub = req.get('publicationNumber', '')
            if (req.get('boampId') not in byid or not PUB.fullmatch(pub) or
                req.get('url') != f'https://ted.europa.eu/en/notice/{pub}/xml' or
                req.get('method') != 'GET' or req.get('requestBody') is not None):
                raise ValueError('invalid exact XML request')
            if 'evidence' in req:
                evidence = req['evidence']
                exact = public_xml_identity(evidence['fields'], byid[req['boampId']])
                if (req.get('failure') or evidence.get('exactAwardVersion') != exact or
                    evidence.get('exactCrosswalkForReview') is not False):
                    raise ValueError('XML identity assertion does not match public header scalars')
        if req['kind'] == 'search':
            executed = not req['requestBody'].get('checkQuerySyntax', False) and not req.get('failure')
            if req.get('searchExecuted') != executed:
                raise ValueError('syntax validation is not executed search')
        if req['kind'] == 'search' and 'evidence' in req:
            for f in req['evidence']['fields']:
                if not re.fullmatch(r'/notices/[0-9]+/(publication-number|notice-identifier|procedure-identifier|publication-date)', f['pointer']):
                    raise ValueError('nonminimal search field')
    actual = discoveries(ledger['source'], ledger['requests'])
    if actual != ledger['discoveries'] or ledger['exactCrosswalkForReview']:
        raise ValueError('public replay mismatch or unsupported crosswalk')
    return ledger


def main():
    p = argparse.ArgumentParser(description=__doc__)
    mode = p.add_mutually_exclusive_group()
    mode.add_argument('--fetch', type=Path, metavar='NEW_PRIVATE_DIRECTORY')
    mode.add_argument('--cached', type=Path, metavar='PRIVATE_DIRECTORY')
    mode.add_argument('--replay-public', type=Path, metavar='MINIMIZED_JSON')
    p.add_argument('--budget', type=int, default=12, help='attempt budget; XML follow-up requires 1..5')
    p.add_argument('--xml-discoveries', type=Path, help='With --fetch: original public 12-request discovery ledger; fetch XML only')
    p.add_argument('--output', type=Path, help='explicit minimized JSON output; otherwise stdout')
    a = p.parse_args()
    if not 1 <= a.budget <= 12:
        p.error('budget must be 1..12')
    if a.xml_discoveries and (not a.fetch or a.budget > 5):
        p.error('--xml-discoveries requires --fetch and --budget 1..5')
    if a.replay_public:
        result = replay_public(json.loads(a.replay_public.read_text()))
    elif a.cached:
        d = a.cached.expanduser()
        m = json.loads((d / 'manifest.json').read_text())
        result = process(m['source'], m['entries'], d)
    else:
        source = inventory(ROOT / 'data/boamp-raw.json.gz')
        if a.xml_discoveries:
            result = fetch_xml_from(source, json.loads(a.xml_discoveries.read_text()), a.fetch, a.budget)
        else:
            result = fetch(source, a.fetch, a.budget) if a.fetch else process(source, [], Path('.'))
    text = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if a.output:
        a.output.write_text(text)
    else:
        print(text, end='')


if __name__ == '__main__':
    main()
