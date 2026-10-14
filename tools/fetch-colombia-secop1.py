#!/usr/bin/env python3
"""Research only: SECOP I contracts of the entity-years named in Colombian conviction records.

Reads ~/.cache/contract-signals/colombia-leads/sol/out-1.jsonl (convictions with contracts: entity NIT,
number, signing year) and downloads, for each entity NIT and signing year >= 2010, every SECOP I contract
of that entity (datos.gov.co x6v4-i8gf, CC BY-SA 4.0) uploaded in that year or the next, with the fields the
checks need. Three requests at a time, paged, cached as colombia-secop1/<nit>-<year>.json.gz. Contractor
identifiers are kept only as a hash (for concentration); names of contractors and legal representatives
are not requested.
"""
import gzip
import hashlib
import json
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

LEADS = Path.home() / '.cache/contract-signals/colombia-leads/sol/out-1.jsonl'
OUT = Path.home() / '.cache/contract-signals/colombia-secop1'
API = 'https://www.datos.gov.co/resource/x6v4-i8gf.json'
FIELDS = ['uid', 'anno_cargue_secop', 'anno_firma_del_contrato', 'nit_de_la_entidad', 'nombre_de_la_entidad', 'tipo_de_proceso',
          'estado_del_proceso', 'tipo_de_contrato', 'numero_de_constancia', 'numero_de_proceso', 'numero_del_contrato',
          'detalle_del_objeto_a_contratar', 'cuantia_contrato', 'valor_total_de_adiciones', 'tiempo_adiciones_en_dias',
          'tiempo_adiciones_en_meses', 'plazo_de_ejec_del_contrato', 'rango_de_ejec_del_contrato', 'fecha_de_firma_del_contrato',
          'identificacion_del_contratista', 'ruta_proceso_en_secop_i']
PAGE = 50_000


def entity_years():
    pairs = set()
    for line in LEADS.read_text().splitlines():
        if not line.strip().startswith('{"lead'):
            continue
        r = json.loads(line)
        nit = ''.join(ch for ch in str(r.get('entity_nit') or '') if ch.isdigit())[:9]
        for c in r.get('contracts') or []:
            if nit and c.get('number') and (c.get('year') or 0) >= 2010:
                pairs.add((nit, int(c['year'])))
    return sorted(pairs)


def fetch(pair):
    nit, year = pair
    path = OUT / f'{nit}-{year}.json.gz'
    if path.exists():
        return pair, 'cached'
    rows, offset = [], 0
    where = f"nit_de_la_entidad='{nit}' and anno_cargue_secop in('{year}','{year + 1}')"
    while True:
        q = urllib.parse.urlencode({'$select': ','.join(FIELDS), '$where': where, '$limit': PAGE, '$offset': offset, '$order': 'uid'})
        req = urllib.request.Request(f'{API}?{q}', headers={'User-Agent': 'contract-signals-label-research/1.0'})
        with urllib.request.urlopen(req, timeout=600) as r:
            page = json.loads(r.read())
        for x in page:
            ident = x.pop('identificacion_del_contratista', None)
            x['contractor_hash'] = hashlib.sha256(ident.encode()).hexdigest()[:16] if ident else None
        rows += page
        if len(page) < PAGE:
            break
        offset += PAGE
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_bytes(gzip.compress(json.dumps(rows, ensure_ascii=False).encode()))
    tmp.replace(path)
    return pair, len(rows)


def main():
    pairs = entity_years()
    print(len(pairs), 'entity-years', flush=True)
    with ThreadPoolExecutor(3) as pool:
        for pair, n in pool.map(lambda p: _safe(p), pairs):
            print(pair, n, flush=True)


def _safe(pair):
    try:
        return fetch(pair)
    except Exception as e:
        return pair, f'error {e}'


if __name__ == '__main__':
    main()
