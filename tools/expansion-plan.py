#!/usr/bin/env python3
"""Print the expansion plan by default; --probe permits seven bounded metadata GETs.

No procurement-record downloads, retries, redirects, browser automation or rebuilds.
Every attempt is cached; failures are not automatically retried on subsequent runs.
"""
import argparse
import hashlib
import ipaddress
import json
from datetime import datetime, timezone
from pathlib import Path
import re
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / 'data/expansion-plan.json'
REPORT = ROOT / 'data/expansion-source-checks.json'
MAX_REQUESTS, MAX_BYTES, TIMEOUT, DELAY = 7, 131072, 12, 2


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def public_resource_url(value):
    if not isinstance(value, str):
        return None
    try:
        url = urlsplit(value)
        host = url.hostname or ''
        if url.scheme not in ('http', 'https') or not host or url.username or url.password or host == 'localhost' or host.endswith(('.local', '.localhost')):
            return None
        try:
            if not ipaddress.ip_address(host).is_global:
                return None
        except ValueError:
            pass  # Public-looking hostname; never automatically fetched.
        return value
    except ValueError:
        return None


def summary(body, content_type, truncated):
    """Retain metadata only, never page text or procurement record values."""
    if 'json' in content_type and not truncated:
        try:
            payload = json.loads(body)
            if not isinstance(payload, dict):
                return {'metadataParse': 'not recognized as catalogue JSON'}
            if payload.get('title'):
                datasets = [payload]
            elif isinstance(payload.get('result'), dict):
                datasets = payload['result'].get('results', [])
            else:
                datasets = payload.get('data', [])
            return {'datasets': [
                {'title': d.get('title'), 'page': d.get('page'),
                 'license': d.get('license') or d.get('license_id'),
                 'publisher': (d.get('organization') or {}).get('name'),
                 'resources': [{'title': r.get('title') or r.get('name'), 'format': r.get('format'),
                                'url': public_resource_url(r.get('url')), 'filesize': r.get('filesize')}
                               for r in (d.get('resources') or [])[:3] if isinstance(r, dict)]}
                for d in datasets[:3] if isinstance(d, dict)
            ]}
        except (ValueError, AttributeError):
            return {'metadataParse': 'not recognized as catalogue JSON'}
    text = body.decode('utf-8', errors='replace')
    title = re.search(r'<title[^>]*>(.*?)</title>', text, re.I | re.S)
    return {'pageTitle': re.sub(r'\s+', ' ', title.group(1)).strip()[:200] if title else None,
            'note': 'Landing-page availability is not evidence of a records API, licence or completeness.'}


def probe(plan):
    report = json.loads(REPORT.read_text()) if REPORT.exists() else {'schemaVersion': 1, 'checks': []}
    checks = report['checks']
    cached = {c['url'] for c in checks}
    sources = plan['metadataSources']
    if len(sources) > MAX_REQUESTS:
        raise ValueError('Metadata request budget exceeded in plan.')
    # Only the preregistered HTTPS host/path/query entries are allowed; no arbitrary URLs.
    allowed = {
        'https://www.base.gov.pt/Base4/pt/dados-abertos/',
        'https://dados.gov.pt/api/1/datasets/?q=contratos&page_size=3',
        'https://data.lkpp.go.id/',
        'https://sirup.lkpp.go.id/sirup/home',
        'https://zakupki.gov.ru/epz/main/public/home.html',
        'https://dados.gov.pt/api/1/datasets/contratos-publicos-portal-base-impic-contratos-de-2012-a-2026/',
        'https://data.lkpp.go.id/api/3/action/package_search?q=pengadaan&rows=3',
    }
    if any(s['url'] not in allowed for s in sources):
        raise ValueError('Unapproved metadata URL.')
    opener = urllib.request.build_opener(NoRedirect)
    pending = [s for s in sources if s['url'] not in cached]
    for index, source in enumerate(pending):
        if index:
            time.sleep(DELAY)
        check = {'id': source['id'], 'url': source['url'], 'country': source['country'],
                 'checkedAt': datetime.now(timezone.utc).isoformat()}
        try:
            request = urllib.request.Request(source['url'], headers={
                'User-Agent': 'contract-signals/metadata-feasibility (bounded research; no record crawl)',
                'Accept': 'application/json,text/html;q=0.9', 'Accept-Encoding': 'identity',
            })
            with opener.open(request, timeout=TIMEOUT) as response:
                check['status'] = response.status
                check['contentType'] = response.headers.get('Content-Type', '')
                body = response.read(MAX_BYTES + 1)
            truncated = len(body) > MAX_BYTES
            body = body[:MAX_BYTES]
            check.update({'bytesRead': len(body), 'truncated': truncated,
                          'capturedPrefixSha256': hashlib.sha256(body).hexdigest()})
            check.update(summary(body, check['contentType'], truncated))
        except urllib.error.HTTPError as error:
            check.update({'status': error.code, 'outcome': 'HTTP failure or redirect; not followed or retried'})
            error.close()
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            check.update({'status': None, 'outcome': 'Network failure; not retried', 'errorType': type(error).__name__})
        checks.append(check)
        # Cache attempts immediately, including refusals and transient failures.
        REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps(check, ensure_ascii=False))
        if check.get('status') in (401, 403, 429, 503):
            print('Refusal/rate-limit/overload: stopping this run; no bypass or retries.')
            break
    if not pending:
        print('All metadata attempts cached; no network requests made.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--probe', action='store_true', help='Explicitly allow bounded, cached metadata GETs only.')
    args = parser.parse_args()
    plan = json.loads(PLAN.read_text())
    if args.probe:
        probe(plan)
    else:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        print('\nPlan only: no network requests or data rebuilds. Use --probe for cached metadata checks.')


if __name__ == '__main__':
    main()
