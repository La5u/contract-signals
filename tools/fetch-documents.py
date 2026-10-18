#!/usr/bin/env python3
"""Evidence documents for one flagged record, fetched politely into a private cache (never the repo).

  python tools/fetch-documents.py prozorro UA-2025-03-06-014215-a             # list documents (API only)
  python tools/fetch-documents.py prozorro UA-2025-03-06-014215-a --download  # also fetch files robots.txt allows
  python tools/fetch-documents.py prozorro --self-test

Every request goes through tools/polite_http.py (honest User-Agent, robots.txt obeyed, one request at a time per
host, 1 s apart, stop on 401/403). Output: ~/.cache/contract-signals/documents/<source>/<record>/ with the API
records, documents.json (one entry per document: where it sits in the record, title, declared format, URL, and
after --download its status, bytes, sha256, sniffed type) and requests.jsonl. A file robots.txt disallows is
listed with status robots-disallowed and its portal link, for a person to open; it is never fetched.
Refuses to run on battery unless --allow-battery. Bounded by --max-files and --max-bytes.

Sources: prozorro (Ukraine). One module per source; each has a self-test against a known-good record, so a broken
endpoint is reported as broken, not as "no documents".
"""
import argparse
import gzip
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from polite_http import CACHE, Disallowed, PoliteClient, Refused  # noqa: E402

OUT = CACHE / 'documents'


def on_battery():
    supplies = list(Path('/sys/class/power_supply').glob('*'))
    mains = [p for p in supplies if (p / 'type').exists() and (p / 'type').read_text().strip() == 'Mains']
    return bool(mains) and not any((p / 'online').read_text().strip() == '1' for p in mains if (p / 'online').exists())


def sniff(data):
    if data.startswith(b'%PDF'):
        return 'pdf'
    if data.startswith(b'PK\x03\x04'):
        return 'zip'  # also docx/xlsx
    if data.startswith(b'\xd0\xcf\x11\xe0'):
        return 'ole'  # doc/xls
    if data[:1] == b'\x30' and data[1:2] in (b'\x80', b'\x82', b'\x83', b'\x84'):
        return 'der'  # PKCS#7 signature (.p7s) or certificate
    if data.startswith((b'\xff\xd8\xff', b'\x89PNG')):
        return 'image'
    if data.lstrip()[:15].lower().startswith((b'<!doctype', b'<html')):
        return 'html'
    return 'unknown'


def save_gz(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gzip.compress((json.dumps(value, ensure_ascii=False, indent=1) + '\n').encode(), mtime=0))


# --- Prozorro -------------------------------------------------------------------------------------------------
class Prozorro:
    API = 'https://public-api.prozorro.gov.ua/api/2.5'
    DETAILS = 'https://prozorro.gov.ua/api/tenders/{}/details'
    PORTAL = 'https://prozorro.gov.ua/tender/{}'
    SELF_TEST = ('UA-2025-03-06-014215-a', '72efe32bfd434ab588a4a2c52b2b8748')
    PATTERN = r'UA-\d{4}-\d{2}-\d{2}-\d{6}-[a-z]'

    def __init__(self, client):
        self.client = client

    def resolve(self, public_id):
        """Public UA-… id → internal 32-hex id (the public API answers 404 to UA-… ids)."""
        internal = self.client.get(self.DETAILS.format(public_id)).json().get('id', '')
        if not re.fullmatch(r'[a-f0-9]{32}', internal):
            raise ValueError(f'No internal id for {public_id}')
        return internal

    def records(self, public_id):
        internal = self.resolve(public_id)
        response = self.client.get(f'{self.API}/tenders/{internal}')
        if response.status != 200:
            raise ValueError(f'Tender {internal}: HTTP {response.status}')
        tender = response.json()['data']
        if tender.get('tenderID') != public_id:
            raise ValueError(f'tenderID mismatch: {public_id} resolved to {tender.get("tenderID")}')
        records = {'tender': tender}
        # Contracting-module records hold the signed contract's own documents and amendments.
        for contract in tender.get('contracts') or []:
            got = self.client.get(f"{self.API}/contracts/{contract['id']}")
            records[f"contract-{contract['id']}"] = got.json()['data'] if got.status == 200 else {'httpStatus': got.status}
        return records

    @staticmethod
    def documents(records):
        """Every document object in the records, latest version per document id, with its JSON path."""
        found = {}

        def walk(value, path):
            if isinstance(value, dict):
                for key, item in value.items():
                    walk(item, f'{path}.{key}')
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if path.endswith('.documents') and isinstance(item, dict) and item.get('url'):
                        key = (path, item.get('id') or item['url'])  # versions of one document share its id
                        if key not in found or (item.get('dateModified') or '') > (found[key][1].get('dateModified') or ''):
                            found[key] = (f'{path}[{i}]', item)
                    walk(item, f'{path}[{i}]')

        for name, record in records.items():
            walk(record, name)
        return [{'path': path, 'id': d.get('id'), 'title': d.get('title'), 'format': d.get('format'),
                 'documentOf': d.get('documentOf'), 'documentType': d.get('documentType'),
                 'datePublished': d.get('datePublished'), 'dateModified': d.get('dateModified'),
                 'declaredHash': d.get('hash'), 'url': d['url']} for path, d in found.values()]

    def portal(self, public_id):
        return self.PORTAL.format(public_id)


SOURCES = {'prozorro': Prozorro}


def verify_hash(declared, data):
    if not declared or ':' not in declared:
        return None
    algorithm, value = declared.split(':', 1)
    return hashlib.new(algorithm, data).hexdigest() == value.lower() if algorithm in hashlib.algorithms_available else None


def run(source, record_id, download, max_files, max_bytes, client=None, out_root=OUT):
    folder = out_root / source / record_id
    client = client or PoliteClient(log_path=folder / 'requests.jsonl')
    module = SOURCES[source](client)
    records = module.records(record_id)
    for name, record in records.items():
        save_gz(folder / 'records' / f'{name}.json.gz', record)
    manifest_path = folder / 'documents.json'
    previous = {d['url']: d for d in json.loads(manifest_path.read_text())['documents']} if manifest_path.exists() else {}
    documents, spent, fetched = module.documents(records), 0, 0
    for doc in documents:
        old = previous.get(doc['url'], {})
        if old.get('status') == 'saved' and (folder / old['file']).exists():
            doc.update({k: old[k] for k in ('status', 'file', 'bytes', 'sha256', 'sniffed', 'hashMatches', 'finalHost', 'redirects')})
            continue
        doc['status'] = 'listed'
        if not download:
            continue
        if fetched >= max_files or spent >= max_bytes:
            doc['status'] = 'over-budget'
            continue
        try:
            response = client.get(doc['url'])
        except Disallowed:
            doc.update(status='robots-disallowed', openByHand=module.portal(record_id))
            continue
        except Refused as e:
            doc.update(status='refused', error=str(e))
            break  # a refusal is final for this run
        fetched += 1
        data = response.body
        if response.status != 200:
            doc.update(status=f'http-{response.status}')
            continue
        spent += len(data)
        digest = hashlib.sha256(data).hexdigest()
        name = re.sub(r'[^\w.\-]+', '_', doc['title'] or 'document')[-80:]
        file = Path('files') / f'{digest[:16]}-{name}'
        (folder / file).parent.mkdir(parents=True, exist_ok=True)
        (folder / file).write_bytes(data)
        doc.update(status='saved', file=str(file), bytes=len(data), sha256=digest, sniffed=sniff(data),
                   hashMatches=verify_hash(doc['declaredHash'], data), finalHost=response.url.split('/')[2],
                   redirects=len(response.hops))
    counts = {}
    for doc in documents:
        counts[doc['status']] = counts.get(doc['status'], 0) + 1
    manifest = {'source': source, 'record': record_id, 'at': datetime.now(timezone.utc).isoformat(),
                'portal': module.portal(record_id), 'counts': counts, 'documents': documents}
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + '\n')
    return manifest


def self_test(source, client=None):
    """Known-good record: resolution, record and a non-empty document list must all work."""
    module = SOURCES[source](client or PoliteClient())
    public_id, internal = module.SELF_TEST
    assert module.resolve(public_id) == internal, 'id resolution changed'
    documents = module.documents(module.records(public_id))
    assert documents, 'known-good record lists no documents: endpoint or parser broken'
    assert all(d['url'].startswith('https://') for d in documents), 'unexpected document URL'
    return len(documents)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('source', choices=sorted(SOURCES))
    parser.add_argument('records', nargs='*')
    parser.add_argument('--download', action='store_true')
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('--max-files', type=int, default=50)
    parser.add_argument('--max-bytes', type=int, default=200 * 1024 * 1024)
    parser.add_argument('--allow-battery', action='store_true')
    args = parser.parse_args()
    if on_battery() and not args.allow_battery:
        raise SystemExit('On battery: plug in or pass --allow-battery.')
    if args.self_test:
        print(f'{args.source} self-test passed: {self_test(args.source)} documents on the known-good record')
        return
    for record in args.records:
        if not re.fullmatch(SOURCES[args.source].PATTERN, record):
            raise SystemExit(f'Not a {args.source} record id: {record}')
        manifest = run(args.source, record, args.download, args.max_files, args.max_bytes)
        print(record, json.dumps(manifest['counts']), OUT / args.source / record)


if __name__ == '__main__':
    main()
