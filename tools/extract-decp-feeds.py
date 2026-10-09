#!/usr/bin/env python3
"""Extract the buyer-feed rows of the eight French DECP cohort buyers from the national file.

The national consolidated DECP (data.gouv.fr dataset 608c055b35eb4e6ee20eb325, decp.info /
Colmo, Licence Ouverte 2.0) aggregates each buyer's own publication feed: Paris from
Atexo/Maximilien, Nantes from Atexo, Rennes from Mégalis, AWS buyer profiles (with a
scraped copy), and PES Marché accounting exports. It is a third-party consolidation,
not the buyers' files themselves.

Every row of a contract (source + uid + holder) whose initial notification (modification_id 0)
falls in 2024–2025 is kept, with its modification rows. Holder names are dropped: holders
stay identified by SIRET, as in the cohorts. Output: data/decp-feeds-raw.json.gz.
Needs the private cache written by tools/fetch-decp-national.py (pyarrow).
"""
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = Path.home() / '.cache/contract-signals/decp-national'
OUT = ROOT / 'data/decp-feeds-raw.json.gz'
BUYERS = ['21350238800019', '21440109300015', '21330063500017', '21380185500015', '21210231300013',
          '21370261600011', '21750001600019', '22070001700019']
FIELDS = ['uid', 'id', 'acheteur_id', 'titulaire_id', 'titulaire_typeIdentifiant', 'objet', 'montant', 'codeCPV',
          'procedure', 'dureeMois', 'offresRecues', 'dateNotification', 'datePublicationDonnees', 'formePrix',
          'typesPrix', 'nature', 'type', 'modalitesExecution', 'techniques', 'idAccordCadre', 'typeGroupementOperateurs',
          'modification_id', 'donneesActuelles', 'sourceDataset', 'sourceFile', 'montant_anomalie']
FROM, TO = '2024-01-01', '2025-12-31'


def contract_key(row):
    return (row['sourceDataset'], row['uid'], row['titulaire_id'])


def extract(rows):
    """Keep every row of contracts whose initial notification is in the window."""
    initial = {contract_key(r) for r in rows
               if r['modification_id'] in (0, None) and r['dateNotification'] and FROM <= r['dateNotification'] <= TO}
    return sorted((r for r in rows if contract_key(r) in initial),
                  key=lambda r: (r['acheteur_id'], r['sourceDataset'], r['uid'] or '', str(r['titulaire_id']),
                                 r['modification_id'] or 0, r['dateNotification'] or ''))


def plain(value):
    return value.isoformat() if hasattr(value, 'isoformat') else value


def main():
    import pyarrow.parquet as pq
    manifest = json.loads((CACHE / 'manifest.json').read_text())
    parquet = CACHE / 'decp.parquet'
    digest = hashlib.sha256(parquet.read_bytes()).hexdigest()
    if digest != manifest['sha256']:
        raise ValueError('National parquet does not match its manifest')
    table = pq.read_table(parquet, columns=FIELDS, filters=[('acheteur_id', 'in', BUYERS)])
    rows = [{k: plain(v) for k, v in r.items()} for r in table.to_pylist()]
    kept = extract(rows)
    payload = {'source': {k: manifest[k] for k in ['dataset_id', 'dataset_title', 'dataset_page', 'publisher', 'licence',
                                                  'resource_url', 'resource_last_modified', 'sha256', 'retrieved_at']},
               'about': 'Third-party consolidation of buyer publication feeds; holder names removed. See tools/extract-decp-feeds.py.',
               'buyers': BUYERS, 'window': [FROM, TO], 'fields': FIELDS, 'records': kept}
    OUT.write_bytes(gzip.compress((json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + '\n').encode(), mtime=0))
    print(f'{len(kept)} feed rows ({sum(r["modification_id"] in (0, None) for r in kept)} initial) from {len(rows)} buyer rows -> {OUT.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
