#!/usr/bin/env python3
"""Supplemental diagnostic; offline default, exact published URLs private only.
No metadata fetches, OCR, redirects, retries, authentication or inferred linkage.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
PLAN = 'data/ukraine-amendment-document-plan.json'
EVIDENCE = 'data/ukraine-amendment-document-evidence.json'
MODULE = 'data/ukraine-amendment-evidence.json'
HOSTS = {'public-docs.prozorro.gov.ua', 'publisherdocservice.prozorro.gov.ua'}
LIMIT = 2 * 1024 * 1024
PRIVATE = Path.home() / '.cache/contract-signals/ukraine-amendment-documents/v1'


def canonical(x):
    return json.dumps(x, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()


def sha(x):
    return hashlib.sha256(x).hexdigest()


def require(ok, msg):
    if not ok:
        raise ValueError(msg)


def now():
    return datetime.now(timezone.utc).isoformat()


def allowed(url):
    u = urllib.parse.urlsplit(url)
    return (u.scheme == 'https' and u.hostname in HOSTS and not u.username and
            not u.password and u.port in (None, 443) and not u.fragment)


def date(value):
    require(isinstance(value, str) and len(value) <= 40, 'Invalid date')
    require(datetime.fromisoformat(value).tzinfo is not None, 'Date lacks timezone')
    return value


def load_source(root=ROOT):
    spec = importlib.util.spec_from_file_location('amount_audit', root / 'tools/audit-ukraine-amount-bases.py')
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    original, rows = helper.validate_plan(root, root / 'data/ukraine-public-audit-plan.json')
    blob = (root / MODULE).read_bytes()
    ledger = json.loads(blob)
    require(ledger['planSha256'] == original['planSha256'], 'Stale module plan')
    require(ledger['evidenceSha256'] == sha(canonical({k: v for k, v in ledger.items() if k != 'evidenceSha256'})), 'Stale module ledger')
    candidates = [b for b in original['selected'] if b['contractChangesAtSelection'] >= 3]
    require(len(candidates) == 1, 'Not a sole three-change sample')
    b = candidates[0]
    r = [r for r in ledger['requests'] if r['rowId'] == b['rowId']]
    require(len(r) == 1 and r[0]['binding'] == b and r[0]['httpStatus'] == 200 and r[0]['responseComplete'], 'Module binding failure')
    require(ledger['requestCount'] == 12 and not ledger['supplementaryRequests'], 'Slots already spent')
    return original, b, r[0], sha(blob)


def bind_module(obj, b):
    d = obj['data']
    for key, bk in [('id', 'contractInternalId'), ('contractID', 'contractId'), ('tender_id', 'tenderInternalId'), ('awardID', 'awardId')]:
        require(d.get(key) == b[bk], 'Module identity mismatch')
    require(d['buyer']['identifier']['id'] == b['buyerId'], 'Buyer identity mismatch')
    return d


def select(d, b):
    active = {c['id'] for c in d['changes'] if c.get('status') == 'active'}
    require(len(active) == 3 and len(d['changes']) == 3, 'Changed active-change inventory')
    docs = [(i, v) for i, v in enumerate(d.get('documents', [])) if v.get('documentOf') == 'change' and v.get('relatedItem') in active]
    # Rank all explicitly linked formats, not titles/dates or presumed PDF content.
    docs.sort(key=lambda iv: sha(canonical([b['rowId'], iv[1]['id']])))
    result, ids, urls = [], set(), set()
    for i, v in docs:
        require(re.fullmatch('[0-9a-f]{32}', v['id']) is not None, 'Invalid document identity')
        if v['id'] in ids or v['url'] in urls:
            continue
        ids.add(v['id']); urls.add(v['url'])
        result.append({'docId': v['id'], 'pointer': f'/data/documents/{i}',
                       'documentOf': v['documentOf'], 'relatedItem': v['relatedItem'],
                       'format': v.get('format'), 'datePublished': date(v['datePublished']),
                       'dateModified': date(v['dateModified']),
                       'urlSha256': sha(v['url'].encode()),
                       'selectionRankSha256': sha(canonical([b['rowId'], v['id']])),
                       'publisherHostAllowed': allowed(v['url'])})
        if len(result) == 2:
            break
    return result


def private_write(path, obj, mode=0o600):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    with os.fdopen(fd, 'wb') as f:
        f.write(canonical(obj) + b'\n')
    os.chmod(path, mode)


def freeze(cache, root=ROOT, private=PRIVATE):
    original, b, r, digest = load_source(root)
    raw = Path(cache).read_bytes()
    require(sha(raw) == r['responseSha256'] and len(raw) == r['responseBytes'], 'Raw module mismatch')
    d = bind_module(json.loads(raw), b)
    selected = select(d, b)
    plan = {'schemaVersion': 'ukraine-amendment-document-plan-v1', 'originalPlanSha256': original['planSha256'],
            'moduleLedgerSha256': digest, 'binding': b, 'moduleResponseSha256': sha(raw),
            'moduleResponseBytes': len(raw), 'moduleEndpoint': r['url'],
            'selectionTiming': 'Supplementary metadata selection after 28 requests; frozen before any document-body attempt, not original attachment preregistration.',
            'frozenAt': now(), 'priorRequests': 28, 'maximumAdditionalAttempts': 2,
            'selectionRule': 'Ascending SHA256 canonical JSON [rowId,docId], exact active-change linkage, unique IDs and exact URLs; all formats eligible; no host-based replacements.',
            'selected': selected, 'changes': [{k: c[k] for k in ('id', 'status', 'dateSigned', 'rationaleTypes')} for c in d['changes']],
            'exactContractReference': d['contractNumber'],
            'contractReferencePointer': '/data/contractNumber',
            'buyerLinkPointer': '/data/buyer/identifier/id',
            'urlOmission': 'Exact published URLs omitted, not substituted; private freeze only. Public API endpoint plus metadata pointers, document IDs and exact URL SHA256 identify selection.',
            'scope': 'Diagnostic only; not accuracy/legal benchmark. Rationale categories do not independently explain legal or financial basis.'}
    plan['planSha256'] = sha(canonical(plan))
    require(not (root / PLAN).exists(), 'Public selection already frozen')
    private = Path(private).expanduser().resolve()
    require(not private.is_relative_to(root.resolve()), 'Cache must be outside Git')
    private.mkdir(parents=True, mode=0o700, exist_ok=True); os.chmod(private, 0o700)
    private_write(private / 'plan.json', {'publicPlan': plan, 'rawModulePath': str(Path(cache).resolve()),
                  'urls': [d['documents'][int(s['pointer'].rsplit('/', 1)[1])]['url'] for s in selected]}, 0o400)
    (root / PLAN).write_text(json.dumps(plan, ensure_ascii=False, indent=2) + '\n')
    return plan


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def bounded_get(url, policy=allowed):
    require(policy(url), 'Unapproved published URL: no request')
    result = {'method': 'GET', 'startedAt': now(), 'httpStatus': None, 'responseComplete': False}
    data = bytearray()
    def deadline(*_):
        raise TimeoutError('deadline')
    old = signal.signal(signal.SIGALRM, deadline)
    signal.setitimer(signal.ITIMER_REAL, 15)
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        with opener.open(urllib.request.Request(url, headers={'Accept-Encoding': 'identity'}), timeout=15) as response:
            result['httpStatus'] = response.status
            while len(data) <= LIMIT:
                part = response.read(min(65536, LIMIT + 1 - len(data)))
                if not part:
                    result['responseComplete'] = True
                    break
                data.extend(part)
            result['outcome'] = 'oversized' if len(data) > LIMIT else 'downloaded' if response.status == 200 else 'http-failure'
    except urllib.error.HTTPError as e:
        result.update(httpStatus=e.code, outcome='http-failure')
        e.close()
    except Exception:
        result['outcome'] = 'transport-failure'  # Never expose exception URLs/signatures.
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0); signal.signal(signal.SIGALRM, old)
    result.update(finishedAt=now(), responseBytes=len(data), responseSha256=sha(data), recognizedPDF=bytes(data).startswith(b'%PDF-'))
    return result, bytes(data)


def verify_v1(root=ROOT):
    original, b, r, digest = load_source(root)
    plan = json.loads((root / PLAN).read_text())
    require(plan['planSha256'] == sha(canonical({k: v for k, v in plan.items() if k != 'planSha256'})), 'Supplemental plan changed')
    require(plan['moduleLedgerSha256'] == digest and plan['binding'] == b and plan['moduleResponseSha256'] == r['responseSha256'], 'Stale supplemental source')
    scalars = {x['pointer']: x['value'] for x in r['extract']['scalars']}
    require(len(plan['selected']) == 2 and len({s['docId'] for s in plan['selected']}) == 2 and
            len({s['urlSha256'] for s in plan['selected']}) == 2, 'Selection inventory mismatch')
    for i, change in enumerate(plan['changes']):
        require(change['status'] == 'active' and scalars[f'/data/changes/{i}/id'] == change['id'] and
                scalars[f'/data/changes/{i}/status'] == change['status'], 'Stale active change')
        date(change['dateSigned'])
    for s in plan['selected']:
        require(scalars[s['pointer'] + '/id'] == s['docId'] and
                scalars[s['pointer'] + '/format'] == s['format'], 'Stale document ID/pointer')
        require(s['documentOf'] == 'change' and s['relatedItem'] in {c['id'] for c in plan['changes']}, 'Change linkage mismatch')
        require(s['selectionRankSha256'] == sha(canonical([b['rowId'], s['docId']])), 'Selection rank mismatch')
        date(s['datePublished']); date(s['dateModified'])
    ev = json.loads((root / EVIDENCE).read_text())
    require(ev['planSha256'] == plan['planSha256'] and ev['evidenceSha256'] == sha(canonical({k:v for k,v in ev.items() if k != 'evidenceSha256'})), 'Stale document evidence')
    require(len(ev['requests']) <= 2 and ev['additionalRequestCount'] == len(ev['requests']), 'Attempt budget mismatch')
    return {'additionalRequestCount': ev['additionalRequestCount'], 'overallRequestCount': 28 + len(ev['requests']), 'legalBasis': 'unknown', 'independentFinancialBasis': 'unknown', 'blockers': ev['blockers']}


PLAN_V2 = 'data/ukraine-amendment-document-plan-v2.json'
EVIDENCE_V2 = 'data/ukraine-amendment-document-evidence-v2.json'
PRIVATE_V2 = PRIVATE.parent / 'v2'


def allowed_v2(url, binding, doc_id):
    # Only the exact frozen URL may be passed by the caller; this is the
    # additional native-API path guard, not a URL generator.
    try:
        u = urllib.parse.urlsplit(url)
        if u.scheme != 'https' or u.username is not None or u.password is not None or u.fragment or u.port not in (None, 443):
            return False
        if u.hostname in HOSTS:
            return True
        return (u.hostname == 'public-api.prozorro.gov.ua' and
                u.path == f"/api/2.5/contracts/{binding['contractInternalId']}/documents/{doc_id}")
    except (ValueError, TypeError):
        return False


def save_evidence_v2(ev, root=ROOT):
    ev.pop('evidenceSha256', None)
    ev['evidenceSha256'] = sha(canonical(ev))
    target = root / EVIDENCE_V2
    tmp = target.with_suffix('.tmp')
    tmp.write_text(json.dumps(ev, ensure_ascii=False, indent=2) + '\n')
    tmp.replace(target)


def freeze_v2(cache, root=ROOT, private=PRIVATE_V2):
    verify_v1(root)
    original, b, r, digest = load_source(root)
    raw = Path(cache).read_bytes()
    require(sha(raw) == r['responseSha256'] and len(raw) == r['responseBytes'], 'Raw module mismatch')
    d = bind_module(json.loads(raw), b)
    old = json.loads((root / PLAN).read_text())
    selected = select(d, b)
    require(selected == old['selected'], 'Historical selection differs')
    urls = [d['documents'][int(s['pointer'].rsplit('/', 1)[1])]['url'] for s in selected]
    require(all(allowed_v2(u, b, s['docId']) for u, s in zip(urls, selected)), 'Published path differs: document exact official path before freezing; never guess')
    plan = {k: v for k, v in old.items() if k not in ('planSha256', 'frozenAt', 'schemaVersion')}
    plan.update(schemaVersion='ukraine-amendment-document-plan-v2', frozenAt=now(),
                historicalPlanSha256=old['planSha256'],
                historicalEvidenceSha256=json.loads((root / EVIDENCE).read_text())['evidenceSha256'],
                policyCorrection='v1 unnecessarily excluded the same official publisher public-api.prozorro.gov.ua. Zero attempts remain historical; missing PDF tools and policy rejection do not establish host inaccessibility.',
                requestPolicy={'maximumAttempts': 2, 'deadlineSeconds': 15, 'maximumBytes': LIMIT,
                               'spacingSeconds': 1, 'redirects': False, 'retries': 0,
                               'stopOnAnyFailure': True, 'authentication': False,
                               'nativeAPIPath': '/api/2.5/contracts/{FULL frozen contractInternalId}/documents/{docId}',
                               'exactPublishedQueryAsIs': True})
    plan['selected'] = [{**s, 'publisherHostAllowed': True, 'publishedPathPolicy': 'exact native API contract/document path'} for s in selected]
    plan['planSha256'] = sha(canonical(plan))
    require(not (root / PLAN_V2).exists() and not (root / EVIDENCE_V2).exists(), 'v2 already frozen')
    private = Path(private).expanduser().resolve()
    require(not private.is_relative_to(root.resolve()), 'Cache must be outside Git')
    private.mkdir(mode=0o700, parents=True, exist_ok=False)
    private_write(private / 'plan.json', {'publicPlan': plan, 'rawModulePath': str(Path(cache).resolve()), 'urls': urls}, 0o400)
    (root / PLAN_V2).write_text(json.dumps(plan, ensure_ascii=False, indent=2) + '\n')
    ev = {'schemaVersion': 'ukraine-amendment-document-evidence-v2', 'planSha256': plan['planSha256'],
          'additionalRequestCount': 0, 'requests': [], 'facts': [],
          'documents': [{**s, 'outcome': 'not-attempted', 'httpStatus': None, 'responseSha256': None,
                         'responseBytes': None, 'recognizedPDF': None, 'extractionMethod': 'none', 'facts': []} for s in plan['selected']],
          'blockers': [], 'legalBasis': 'unknown', 'independentFinancialBasis': 'unknown'}
    save_evidence_v2(ev, root)
    return plan


def verify(root=ROOT, version=2):
    if version == 1:
        return verify_v1(root)
    historical = verify_v1(root)
    require(historical['additionalRequestCount'] == 0, 'Historical slots spent')
    old = json.loads((root / PLAN).read_text())
    plan = json.loads((root / PLAN_V2).read_text())
    ev = json.loads((root / EVIDENCE_V2).read_text())
    require(plan['planSha256'] == sha(canonical({k: v for k, v in plan.items() if k != 'planSha256'})), 'v2 plan changed')
    require(plan['historicalPlanSha256'] == old['planSha256'] and plan['historicalEvidenceSha256'] == json.loads((root / EVIDENCE).read_text())['evidenceSha256'], 'Historical binding changed')
    for key in old:
        if key not in ('schemaVersion', 'frozenAt', 'planSha256', 'selected'):
            require(plan[key] == old[key], 'v2 source binding changed')
    require(plan['requestPolicy'] == {'maximumAttempts': 2, 'deadlineSeconds': 15, 'maximumBytes': LIMIT,
                                     'spacingSeconds': 1, 'redirects': False, 'retries': 0,
                                     'stopOnAnyFailure': True, 'authentication': False,
                                     'nativeAPIPath': '/api/2.5/contracts/{FULL frozen contractInternalId}/documents/{docId}',
                                     'exactPublishedQueryAsIs': True}, 'v2 policy changed')
    date(plan['frozenAt'])
    require(len(plan['selected']) == 2, 'v2 inventory mismatch')
    for s, prior in zip(plan['selected'], old['selected']):
        require({k: s[k] for k in prior if k != 'publisherHostAllowed'} == {k: v for k, v in prior.items() if k != 'publisherHostAllowed'}, 'v2 selection/order changed')
    require(ev['planSha256'] == plan['planSha256'] and ev['evidenceSha256'] == sha(canonical({k: v for k, v in ev.items() if k != 'evidenceSha256'})), 'v2 evidence changed')
    require(ev['additionalRequestCount'] == len(ev['requests']) <= 2, 'Attempt budget mismatch')
    require(len(ev['documents']) == 2, 'Document ledger mismatch')
    for i, (doc, selected) in enumerate(zip(ev['documents'], plan['selected'])):
        require(all(doc[k] == v for k, v in selected.items()), 'Document selection mismatch')
        if i < len(ev['requests']):
            req = ev['requests'][i]
            require(all(doc[k] == req[k] for k in ('outcome', 'httpStatus', 'responseSha256', 'responseBytes', 'recognizedPDF')), 'Document outcome mismatch')
        else:
            require(doc['outcome'] in ('not-attempted', 'not-attempted-global-failure') and all(doc[k] is None for k in ('httpStatus', 'responseBytes', 'responseSha256', 'recognizedPDF')), 'Unattempted document has body/status')
            if ev['requests']:
                require(doc['outcome'] == 'not-attempted-global-failure', 'Missing global stop outcome')
    for i, req in enumerate(ev['requests']):
        require(req['docId'] == plan['selected'][i]['docId'] and req['urlSha256'] == plan['selected'][i]['urlSha256'], 'Request order/binding mismatch')
        require(req['method'] == 'GET' and datetime.fromisoformat(date(req['startedAt'])) >= datetime.fromisoformat(plan['frozenAt']), 'Request preceded freeze')
        require(0 <= req['responseBytes'] <= LIMIT + 1, 'Response byte bound violated')
        require(datetime.fromisoformat(date(req['finishedAt'])) >= datetime.fromisoformat(req['startedAt']), 'Invalid request duration')
        if i:
            prior = ev['requests'][i - 1]
            require(prior['outcome'] == 'downloaded' and prior['responseComplete'] and prior['httpStatus'] == 200, 'Request after global failure')
            require((datetime.fromisoformat(req['startedAt']) - datetime.fromisoformat(prior['finishedAt'])).total_seconds() >= 1, 'Spacing violated')
    return {'additionalRequestCount': len(ev['requests']), 'overallRequestCount': 28 + len(ev['requests']),
            'legalBasis': ev['legalBasis'], 'independentFinancialBasis': ev['independentFinancialBasis'], 'blockers': ev['blockers']}


def extract_binder(raw, reference):
    # Minimized output: no page text, names, addresses or unrelated scalars.
    import io
    try:
        import pypdf
        pages = [p.extract_text() or '' for p in pypdf.PdfReader(io.BytesIO(raw)).pages]
        method = 'installed-local-pypdf'
    except ImportError:
        try:
            import fitz
        except ImportError:
            return 'none', [], 'No installed local pypdf/PyMuPDF; no installation, OCR or upload.'
        with fitz.open(stream=raw, filetype='pdf') as doc:
            pages = [page.get_text() for page in doc]
        method = 'installed-local-PyMuPDF'
    facts = [{'kind': 'exact-contract-reference', 'value': reference, 'page': i + 1}
             for i, text in enumerate(pages) if re.search(r'(?<![\w/])' + re.escape(reference) + r'(?![\w/])', text)]
    return method, facts, None


def attempt_v2(root=ROOT, private=PRIVATE_V2):
    verify(root)
    plan = json.loads((root / PLAN_V2).read_text())
    ev = json.loads((root / EVIDENCE_V2).read_text())
    private = Path(private).resolve()
    require(not private.is_relative_to(root.resolve()), 'Cache must be outside Git')
    require(private.stat().st_mode & 0o777 == 0o700 and (private / 'plan.json').stat().st_mode & 0o777 == 0o400, 'Private modes changed')
    frozen = json.loads((private / 'plan.json').read_text())
    require(frozen['publicPlan'] == plan, 'Private freeze mismatch')
    raw = Path(frozen['rawModulePath']).read_bytes()
    require(sha(raw) == plan['moduleResponseSha256'] and len(raw) == plan['moduleResponseBytes'], 'Private module changed')
    d = bind_module(json.loads(raw), plan['binding'])
    for s, url in zip(plan['selected'], frozen['urls']):
        published = d['documents'][int(s['pointer'].rsplit('/', 1)[1])]
        require(url == published['url'] and sha(url.encode()) == s['urlSha256'] and published['id'] == s['docId'], 'Private published URL changed')
        require(allowed_v2(url, plan['binding'], s['docId']), 'URL rejected')
    require(len(frozen['urls']) == 2 and not ev['requests'], 'No rerun/retry allowed')
    # Exclusive durable guard: even interruption cannot silently spend slots again.
    private_write(private / 'attempt-ledger.json', {'startedAt': now(), 'planSha256': plan['planSha256'], 'state': 'sequence-reserved-no-replay'})
    for i, (s, url) in enumerate(zip(plan['selected'], frozen['urls'])):
        if i:
            time.sleep(1)
        req, body = bounded_get(url, policy=lambda u: u == url and allowed_v2(u, plan['binding'], s['docId']))
        req.update(docId=s['docId'], urlSha256=s['urlSha256'])
        ev['requests'].append(req); ev['additionalRequestCount'] = len(ev['requests'])
        doc = ev['documents'][i]
        doc.update({k: req[k] for k in ('outcome', 'httpStatus', 'responseSha256', 'responseBytes', 'recognizedPDF')})
        if body:
            fd = os.open(private / f'document-{i + 1}.bin', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'wb') as f:
                f.write(body)
        failed = req['outcome'] != 'downloaded' or not req['responseComplete'] or req['httpStatus'] != 200
        if not failed and req['recognizedPDF']:
            try:
                method, facts, blocker = extract_binder(body, plan['exactContractReference'])
                doc.update(extractionMethod=method, facts=facts)
                if blocker:
                    ev['blockers'].append(blocker)
                    failed = True
            except Exception:
                ev['blockers'].append('Local PDF extraction failed; no content or exception details published.')
                failed = True
        save_evidence_v2(ev, root)
        private_write(private / f'request-{i + 1}.json', req)
        if failed:
            ev['blockers'].append(f"Global stop after document {i + 1}: {req['outcome']}, HTTP {req['httpStatus']}; no redirects, retries or replacements.")
            for remaining in ev['documents'][i + 1:]:
                remaining['outcome'] = 'not-attempted-global-failure'
            save_evidence_v2(ev, root)
            break
    verify(root)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', type=int, choices=(1, 2), default=2)
    parser.add_argument('--freeze-from-cache', type=Path)
    parser.add_argument('--attempt-frozen', action='store_true')
    args = parser.parse_args()
    require(not (args.freeze_from_cache and args.attempt_frozen), 'Freeze and attempt are separate operations')
    if args.version == 2:
        if args.freeze_from_cache:
            freeze_v2(args.freeze_from_cache)
        if args.attempt_frozen:
            attempt_v2()
        print(json.dumps(verify(), indent=2))
        return
    require(not args.attempt_frozen, 'Historical v1 has no live CLI')
    if args.freeze_from_cache:
        plan = freeze(args.freeze_from_cache)
        # This inspection intentionally has no live CLI: unapproved URLs cannot be fetched.
        ev = {'schemaVersion': 'ukraine-amendment-document-evidence-v1', 'planSha256': plan['planSha256'],
              'additionalRequestCount': 0, 'requests': [], 'facts': [],
              'documents': [{**s, 'outcome': 'not-attempted-host-policy', 'httpStatus': None,
                             'responseSha256': None, 'responseBytes': None, 'recognizedPDF': None,
                             'extractionMethod': 'none', 'facts': []} for s in plan['selected']],
              'blockers': ['Exact published selected URLs are outside the permitted publisher hosts; no redirect or URL derivation permitted.',
                           'pdftotext not installed locally; no installation, OCR or upload attempted.'],
              'legalBasis': 'unknown', 'independentFinancialBasis': 'unknown',
              'referenceEvidence': {'value': plan['exactContractReference'], 'pointer': '/data/contractNumber', 'sourceSha256': plan['moduleResponseSha256'], 'kind': 'module-metadata-not-document-body'}}
        ev['evidenceSha256'] = sha(canonical(ev))
        (ROOT / EVIDENCE).write_text(json.dumps(ev, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(verify_v1(), indent=2))


if __name__ == '__main__':
    main()
