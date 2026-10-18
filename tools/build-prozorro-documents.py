#!/usr/bin/env python3
"""Document links for the explorer's record panel, from tender records already downloaded (no network).

  python tools/build-prozorro-documents.py --contracts data/prozorro.json --raw data/prozorro/raw/records \
      --out data/prozorro-documents
  python tools/build-prozorro-documents.py --contracts data/prozorro-slice-2026-06-08/contracts.json \
      --cache ~/.cache/contract-signals/prozorro-national/slice-2026-06-08 --out data/prozorro-slice-2026-06-08/documents

Writes <out>/<first two hex of the internal tender id>.json: {internalId: {asOf, t: tender docs, a: {awardId: award}}}.
An award holds its lot (l), status (s), supplier name as published (n), decision documents (d) and, for the
active award only, the winning bid's documents (b). Each document is [title, url]; a public-docs URL is stored
without its constant prefix (DOCS). Latest version per document id; signatures (.p7s) and automatic register
extracts and audit files (.yaml) are left out. Links are published by Prozorro; a reader opens them by clicking (nothing is fetched here
or by the site). Signed URLs are a snapshot as of `asOf`.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

DOCS = 'https://public-docs.prozorro.gov.ua/get/'
API = 'https://public-api.prozorro.gov.ua/api/2.5'
AUTOMATIC = {'registerUSR', 'register', 'registerFin'}


def latest(documents):
    chosen = {}
    for d in documents or []:
        title = d.get('title') or ''
        if not d.get('url') or d.get('format') in ('application/pkcs7-signature', 'application/yaml') \
                or title.lower().endswith(('.p7s', '.yaml')) \
                or d.get('documentType') in AUTOMATIC:
            continue
        key = d.get('id') or d['url']
        if key not in chosen or (d.get('dateModified') or '') > (chosen[key].get('dateModified') or ''):
            chosen[key] = d
    ordered = sorted(chosen.values(), key=lambda d: (d.get('datePublished') or '', d.get('title') or ''))
    return [[d.get('title') or 'document', d['url'][len(DOCS):] if d['url'].startswith(DOCS) else d['url']] for d in ordered]


def entry(tender, as_of):
    bids = {b['id']: b for b in tender.get('bids') or []}
    awards = {}
    for a in tender.get('awards') or []:
        supplier = (a.get('suppliers') or [{}])[0]
        item = {'l': a.get('lotID'), 's': a.get('status'),
                'n': (supplier.get('identifier') or {}).get('legalName') or supplier.get('name'), 'd': latest(a.get('documents'))}
        if a.get('status') == 'active':
            item['b'] = latest((bids.get(a.get('bid_id')) or {}).get('documents'))
        awards[a['id']] = item
    return {'asOf': as_of, 't': latest(tender.get('documents')), 'a': awards}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--contracts', type=Path, required=True)
    parser.add_argument('--raw', type=Path, help='data/prozorro/raw/records (<tenderID>.json.gz, pilot)')
    parser.add_argument('--cache', type=Path, help='slice cache (<sha256(url)[:32]>.gz + .meta.json)')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    rows = json.loads(args.contracts.read_text())
    tenders = {r['procedureId']: r['tenderID'] for r in rows}
    shards = {}
    for internal, public in sorted(tenders.items()):
        if args.raw:
            record = json.loads(gzip.decompress((args.raw / f'{public}.json.gz').read_bytes()))
            manifest = json.loads((args.raw.parent / 'manifest.json').read_text())
            as_of = (manifest.get('retrievalStartedAt') or '')[:10]
        else:
            key = hashlib.sha256(f'{API}/tenders/{internal}'.encode()).hexdigest()[:32]
            record = json.loads(gzip.decompress((args.cache / f'{key}.gz').read_bytes()))
            as_of = json.loads((args.cache / f'{key}.meta.json').read_text())['retrieved_at'][:10]
        tender = record['data']
        if tender['id'] != internal or tender['tenderID'] != public:
            raise ValueError(f'Record identity mismatch: {public}')
        shards.setdefault(internal[:2], {})[internal] = entry(tender, as_of)
    args.out.mkdir(parents=True, exist_ok=True)
    for old in args.out.glob('*.json'):
        old.unlink()
    total = 0
    for shard, value in shards.items():
        text = json.dumps(value, ensure_ascii=False, separators=(',', ':'), sort_keys=True) + '\n'
        (args.out / f'{shard}.json').write_text(text)
        total += len(text.encode())
    print(f'{len(tenders)} tenders, {len(shards)} files, {total / 1e6:.1f} MB')


if __name__ == '__main__':
    main()
