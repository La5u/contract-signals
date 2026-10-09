#!/usr/bin/env python3
"""Snapshot the buyers' own open-data lists of concluded contracts (Nantes, Bordeaux).

Sources (Licence Ouverte 2.0), found on data.gouv.fr on 2026-10-08:
- Ville de Nantes, "Marchés publics conclus en 2024 / 2025" (data.nantesmetropole.fr);
- Bordeaux Métropole datahub, "Marchés publics de Bordeaux Métropole et des communes
  mutualisées — depuis 2024", restricted to the Ville de Bordeaux (SIRET 21330063500017).
Rennes (ends 2022, no amounts, ODbL) and the other cohort buyers publish no current list.

Rows are normalised to the buyer-feed row shape used by tools/decp_feeds.py; company names
are dropped (holders stay identified by SIRET). Known publisher error, corrected here:
the Nantes 2024 file gives buyer SIRET 59840109300015, absent from the company register;
its rows are the Ville de Nantes' own services and the dataset is titled "Ville de Nantes",
so the City's SIRET 21440109300015 is used and the published value kept in `publishedBuyerId`.

  python tools/extract-city-portals.py --fetch   # three bounded downloads into the private cache
  python tools/extract-city-portals.py           # rebuild data/city-portals-raw.json.gz offline
"""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import time
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
CACHE = Path.home() / '.cache/contract-signals/city-portals-20261008'
OUT = ROOT / 'data/city-portals-raw.json.gz'
NANTES, BORDEAUX, NANTES_TYPO = '21440109300015', '21330063500017', '59840109300015'
SOURCES = {
    'nantes-2024': ('https://data.nantesmetropole.fr/api/explore/v2.1/catalog/datasets/244400404_marches-publics-conclus-2024-nantes/exports/json',
                    'https://www.data.gouv.fr/datasets/marches-publics-conclus-en-2024-par-la-ville-de-nantes'),
    'nantes-2025': ('https://data.nantesmetropole.fr/api/explore/v2.1/catalog/datasets/244400404_marches-publics-conclus-2025-nantes/exports/json',
                    'https://www.data.gouv.fr/datasets/marches-publics-conclus-en-2025-par-la-ville-de-nantes'),
    'bordeaux-ville': ('https://datahub.bordeaux-metropole.fr/api/explore/v2.1/catalog/datasets/met_marches_publics_2024/exports/json?'
                       + urllib.parse.urlencode({'where': f'acheteur_id="{BORDEAUX}"'}),
                       'https://www.data.gouv.fr/datasets/marches-publics-de-bordeaux-metropole-et-des-communes-mutulalisees-depuis-2024'),
}


def cpv(value):
    first = str(value or '').split(',')[0].strip()
    return first or None


def nantes(rows, year):
    out = []
    for x in rows:
        if year == 2024:
            buyer, cid, holder, amount, kind = str(x.get('identifiant_de_l_acheteur')), x.get('identifiant_du_marche'), x.get('identifiant_du_titulaire'), x.get('montant_eur'), x.get('type_identifiant_du_titulaire')
            date, objet, code, procedure, duration, price = x.get('date_de_notification'), x.get('objet'), x.get('codes_cpv'), x.get('procedure_de_passation'), x.get('duree'), x.get('forme_du_prix')
        else:
            buyer, cid, holder, amount, kind = str(x.get('siret_acheteur')), x.get('reference_interne_du_contrat'), x.get('siret_de_l_attributaire'), x.get('montant_du_contrat_attribue'), x.get('type_identifiant')
            date, objet, code, procedure, duration, price = x.get('date_de_notification'), x.get('objet_du_marche'), x.get('cpv_principal'), x.get('procedure_de_passation'), x.get('duree_maximale_du_marche'), x.get('forme_du_prix')
        row = {'acheteur_id': NANTES if buyer == NANTES_TYPO else buyer, 'id': str(cid), 'titulaire_id': str(holder) if holder else None,
               'titulaire_typeIdentifiant': kind, 'montant': amount, 'dateNotification': date, 'objet': objet, 'codeCPV': cpv(code),
               'procedure': procedure, 'dureeMois': duration if isinstance(duration, int) else None, 'formePrix': price, 'offresRecues': None,
               'sourceDataset': 'portal_nantes'}
        if buyer == NANTES_TYPO:
            row['publishedBuyerId'] = buyer
        out.append(row)
    return out


def bordeaux(rows):
    out = []
    for x in rows:
        holders = json.loads(x['titulaires']) if x.get('titulaires') else []
        for h in holders or [{}]:
            out.append({'acheteur_id': x['acheteur_id'], 'id': str(x['id']), 'titulaire_id': str(h['id']) if h.get('id') else None,
                        'titulaire_typeIdentifiant': h.get('typeIdentifiant'), 'montant': x.get('montant'), 'dateNotification': x.get('datenotification'),
                        'datePublicationDonnees': x.get('datepublicationdonnees'), 'objet': x.get('objet'), 'codeCPV': cpv(x.get('codecpv')),
                        'procedure': x.get('procedure'), 'dureeMois': x.get('dureemois'), 'formePrix': x.get('formeprix'),
                        'offresRecues': x.get('offresrecues'), 'idAccordCadre': x.get('idaccordcadre'), 'sourceDataset': 'portal_bordeaux'})
    return out


def fetch():
    CACHE.mkdir(parents=True, exist_ok=True, mode=0o700)
    manifest = []
    for label, (url, _) in SOURCES.items():
        if manifest:
            time.sleep(2)
        with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'ContractSignals bounded source review'}), timeout=60) as r:
            body = r.read(20 * 1024 * 1024 + 1)
        if len(body) > 20 * 1024 * 1024:
            raise ValueError(f'{label}: response above 20 MiB')
        (CACHE / f'{label}.json').write_bytes(body)
        manifest.append({'label': label, 'url': url, 'retrievedAt': datetime.now(timezone.utc).isoformat(), 'bytes': len(body),
                         'sha256': hashlib.sha256(body).hexdigest(), 'records': len(json.loads(body))})
    (CACHE / 'manifest.json').write_text(json.dumps(manifest, indent=1) + '\n')


def build():
    manifest = {m['label']: m for m in json.loads((CACHE / 'manifest.json').read_text())}
    records = []
    for label in SOURCES:
        body = (CACHE / f'{label}.json').read_bytes()
        if hashlib.sha256(body).hexdigest() != manifest[label]['sha256']:
            raise ValueError(f'{label}: cached file does not match its manifest')
        rows = json.loads(body)
        records += bordeaux(rows) if label.startswith('bordeaux') else nantes(rows, int(label[-4:]))
    for n, r in enumerate(records):
        r.update({'uid': f"{r['sourceDataset']}:{r['id']}:{r['titulaire_id']}:{r['montant']}:{n}", 'modification_id': 0})
    payload = {'sources': [{**manifest[k], 'dataset_page': SOURCES[k][1], 'licence': 'Licence Ouverte 2.0'} for k in SOURCES],
               'about': __doc__.strip(), 'records': records}
    OUT.write_bytes(gzip.compress((json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + '\n').encode(), mtime=0))
    print(f'{len(records)} portal rows -> {OUT.relative_to(ROOT)}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--fetch', action='store_true')
    args = parser.parse_args()
    if args.fetch:
        fetch()
    build()
