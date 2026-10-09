#!/usr/bin/env python3
"""Bounded exact-ID/source discovery for one frozen Dijon DECP conflict.

Default prints a plan without network. Responses remain private; no corrections.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request

BUYER = '21210231300013'
CONTRACT = '2023VDAO1642'
CACHE = Path.home() / '.cache/contract-signals/decp-conflict-dijon'
ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 2 * 1024 * 1024


def requests():
    ministry = 'https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/decp-2022-marches-valides/records'
    boamp = 'https://www.boamp.fr/api/explore/v2.1/catalog/datasets/boamp/records'
    searches = [
        ('ministry-exact', ministry, {'where': f"acheteur_id='{BUYER}' AND id='{CONTRACT}'", 'limit': 100}),
        ('boamp-contract-reference', boamp, {'where': f'search(donnees,"{CONTRACT}")', 'limit': 5}),
        ('boamp-project-discovery', boamp, {'where': 'search(objet,"Maison des Associations") AND search(nomacheteur,"Dijon")', 'limit': 10, 'order_by': 'dateparution asc'})
    ]
    return [{'label': label, 'url': base + '?' + urllib.parse.urlencode(params)} for label, base, params in searches]


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def private_write(path, content):
    with path.open('x') as stream:
        stream.write(json.dumps(content, ensure_ascii=False, indent=2) + '\n')
    path.chmod(0o600)


def fetch(root):
    if root == ROOT or ROOT in root.parents:
        raise ValueError('Raw responses must stay outside the served repository')
    root.mkdir(parents=True, mode=0o700, exist_ok=True)
    root.chmod(0o700)
    plan = {'buyerSiret': BUYER, 'contractId': CONTRACT, 'requests': requests(),
            'policy': {'maxRequests': 3, 'maxBytes': MAX_BYTES, 'timeoutSeconds': 15,
                       'spacingSeconds': 2, 'redirects': False, 'retries': 0},
            'caution': 'Project search is discovery only, never an identity match'}
    private_write(root / 'fetch-plan.json', plan)  # exclusive freeze; no repeat requests on rerun
    opener = urllib.request.build_opener(NoRedirect())
    entries = []
    for item in plan['requests']:
        if entries:
            time.sleep(2)
        entry = {**item, 'retrievedAt': datetime.now(timezone.utc).isoformat()}
        body = b''
        try:
            request = urllib.request.Request(item['url'], headers={'User-Agent': 'ContractSignals bounded accuracy review', 'Accept-Encoding': 'identity'})
            try:
                response = opener.open(request, timeout=15)
            except urllib.error.HTTPError as exc:
                response = exc
            with response:
                entry.update(status=response.code, contentType=response.headers.get('Content-Type'))
                body = response.read(MAX_BYTES + 1)
                if len(body) > MAX_BYTES:
                    entry['truncated'] = True
                    body = body[:MAX_BYTES]
        except Exception as exc:
            entry['error'] = type(exc).__name__
        filename = item['label'] + '.response'
        with (root / filename).open('xb') as stream:
            stream.write(body)
        (root / filename).chmod(0o600)
        entry.update(file=filename, bytes=len(body), sha256=hashlib.sha256(body).hexdigest())
        entries.append(entry)
        if entry.get('error') or entry.get('truncated') or entry.get('status') in (403, 429) or entry.get('status', 0) >= 500:
            break
    private_write(root / 'fetch-manifest.json', {'entries': entries, 'planned': len(plan['requests'])})
    print(json.dumps([{'label': e['label'], 'status': e.get('status'), 'bytes': e['bytes'], 'error': e.get('error')} for e in entries], indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fetch', action='store_true')
    parser.add_argument('--output-dir', type=Path, default=CACHE / 'official-discovery-20261008')
    args = parser.parse_args()
    if args.fetch:
        fetch(args.output_dir.resolve())
    else:
        print(json.dumps({'buyerSiret': BUYER, 'contractId': CONTRACT, 'requests': requests()}, indent=2))


if __name__ == '__main__':
    main()
