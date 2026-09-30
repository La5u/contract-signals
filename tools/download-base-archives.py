#!/usr/bin/env python3
"""Stream three frozen IMPIC/BASE archives to a private cache; never extract them.

Default: print the preregistered plan, no network. --download authorizes the three
exact URLs. Binary archives remain outside the repository and static website.
Failed/interrupted attempts are recorded and never automatically retried.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time
from datetime import datetime, timezone
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / 'data/portugal-base-download-plan.json'
REPORT = ROOT / 'data/portugal-base-downloads.json'
CACHE = Path(os.environ.get('XDG_CACHE_HOME', str(Path.home() / '.cache'))) / 'contract-signals' / 'base-archives'
MAX_ARCHIVE, MAX_TOTAL = 60 * 1024 * 1024, 160 * 1024 * 1024
URLS = {
    'https://dados.gov.pt/s/resources/contratos-publicos-portal-base-impic-contratos-de-2012-a-2026/20260927-090503-6deefa7c/contratos2024.zip',
    'https://dados.gov.pt/s/resources/contratos-publicos-portal-base-impic-contratos-de-2012-a-2026/20260927-090446-b57595cf/contratos2025.zip',
    'https://dados.gov.pt/s/resources/contratos-publicos-portal-base-impic-contratos-de-2012-a-2026/20260927-090427-eb50032c/contratos2026.zip',
}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def stamp():
    return datetime.now(timezone.utc).isoformat()


def save(report):
    temporary = REPORT.with_suffix('.tmp')
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(REPORT)


def download(plan):
    resources = plan['resources']
    if len(resources) != 3 or {r['url'] for r in resources} != URLS:
        raise ValueError('Only the three frozen archive URLs are approved.')
    if sum(r['expectedBytes'] for r in resources) > MAX_TOTAL:
        raise ValueError('Total download budget exceeded.')
    for resource in resources:
        if not 0 < resource['expectedBytes'] <= MAX_ARCHIVE or Path(resource['filename']).name != resource['filename']:
            raise ValueError('Invalid filename or archive size.')
    # A private cache must not accidentally sit inside the static web root.
    if CACHE.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError('Cache must remain outside the repository/static website.')
    CACHE.mkdir(parents=True, exist_ok=True, mode=0o700)
    CACHE.chmod(0o700)
    lock = CACHE / '.download-lock'
    lock.mkdir(mode=0o700)  # An existing lock requires manual interruption review.
    try:
        report = json.loads(REPORT.read_text()) if REPORT.exists() else {
            'schemaVersion': 1, 'sourcePlan': 'data/portugal-base-download-plan.json',
            'scope': 'Private downloaded archives only; no extraction, normalized records or redistribution approval.',
            'downloads': [],
        }
        attempts = {entry['url']: entry for entry in report['downloads']}
        if any(entry.get('status') != 'downloaded' for entry in attempts.values()):
            print('A previous incomplete/failed attempt is recorded; stop for manual review. No network requests.')
            return
        opener = urllib.request.build_opener(NoRedirect)
        downloaded_bytes = sum(entry.get('bytes', 0) for entry in attempts.values())
        requested = 0
        for resource in resources:
            if resource['url'] in attempts:
                print(f"Cached attempt skipped: {resource['filename']}")
                continue
            destination = CACHE / resource['filename']
            partial = destination.with_suffix('.zip.part')
            if destination.exists() or partial.exists():
                raise ValueError('Unrecorded cache file exists; manual review required, no overwrite.')
            if requested:
                time.sleep(2)
            entry = {**resource, 'startedAt': stamp(), 'status': 'started', 'storage': 'private cache outside repository'}
            report['downloads'].append(entry)
            save(report)  # A process interruption must not authorize an automatic retry.
            requested += 1
            try:
                request = urllib.request.Request(resource['url'], headers={
                    'User-Agent': 'contract-signals/bounded-base-archive-download',
                    'Accept-Encoding': 'identity',
                })
                digest, count, first = hashlib.sha256(), 0, True
                deadline = time.monotonic() + 300
                fd = os.open(partial, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, 'wb') as output, opener.open(request, timeout=30) as response:
                    entry['httpStatus'] = response.status
                    entry['contentType'] = response.headers.get('Content-Type', '')
                    length = response.headers.get('Content-Length')
                    if length and int(length) != resource['expectedBytes']:
                        raise ValueError('Content-Length differs from frozen catalogue metadata.')
                    while True:
                        if time.monotonic() > deadline:
                            raise TimeoutError('Archive exceeded the five-minute time budget.')
                        chunk = response.read(256 * 1024)
                        if not chunk:
                            break
                        if first and not chunk.startswith((b'PK\x03\x04', b'PK\x05\x06')):
                            raise ValueError('Response does not begin with a ZIP signature.')
                        first = False
                        count += len(chunk)
                        if count > resource['expectedBytes'] or count > MAX_ARCHIVE or downloaded_bytes + count > MAX_TOTAL:
                            raise ValueError('Stream exceeded frozen archive size or download budget.')
                        output.write(chunk)
                        digest.update(chunk)
                if count != resource['expectedBytes']:
                    raise ValueError('Downloaded byte count differs from frozen catalogue metadata.')
                partial.replace(destination)
                downloaded_bytes += count
                entry.update({'status': 'downloaded', 'bytes': count, 'sha256': digest.hexdigest(), 'finishedAt': stamp()})
                save(report)
                print(f"Downloaded {resource['filename']}: {count:,} bytes; SHA-256 {entry['sha256']}", flush=True)
            except Exception as error:
                partial.unlink(missing_ok=True)
                entry.update({'status': 'failed', 'finishedAt': stamp(), 'errorType': type(error).__name__})
                if isinstance(error, urllib.error.HTTPError):
                    entry['httpStatus'] = error.code
                    error.close()
                save(report)
                print(f"Stopped on {type(error).__name__}; no retry, redirect or remaining downloads.")
                raise
        print(f'Private cache: {CACHE}; archives not extracted or published.')
    finally:
        lock.rmdir()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download', action='store_true', help='Authorize only the three preregistered archive downloads.')
    args = parser.parse_args()
    plan = json.loads(PLAN.read_text())
    if args.download:
        download(plan)
    else:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        print('Plan only: no requests, extraction or imports. Use --download to fill the private cache.')


if __name__ == '__main__':
    main()
