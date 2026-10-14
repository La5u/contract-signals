#!/usr/bin/env python3
"""Research only: SECOP I/II contracts of the entity-years named in Colombian conviction records.

Reads ~/.cache/contract-signals/colombia-leads/sol/out-1.jsonl (convictions with contracts: entity NIT,
number, signing year) and downloads, for each entity NIT and signing year >= 2010, every SECOP I contract
of that entity (datos.gov.co x6v4-i8gf, CC BY-SA 4.0) uploaded in that year or the next, with the fields the
checks need. Three requests at a time, paged, cached as colombia-secop1/<nit>-<year>.json.gz. Contractor
identifiers are kept only as a hash (for concentration); names of contractors and legal representatives
are not requested. --source secop2 (jbjy-vk9h, contracts signed 2016+) and --source secop1new (f789-7hwg,
SECOP I signatures of 2018+) download the same entity-years, mapped to the x6v4-i8gf field names, into
<nit>-<year>.<source>.json.gz.
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


SOURCES = {
    'secop1': (API, None),
    'secop2': ('https://www.datos.gov.co/resource/jbjy-vk9h.json', {
        'uid': 'id_contrato', 'nit_de_la_entidad': 'nit_entidad', 'nombre_de_la_entidad': 'nombre_entidad', 'tipo_de_proceso': 'modalidad_de_contratacion',
        'estado_del_proceso': 'estado_contrato', 'tipo_de_contrato': 'tipo_de_contrato', 'numero_de_proceso': 'proceso_de_compra',
        'numero_del_contrato': 'referencia_del_contrato', 'detalle_del_objeto_a_contratar': 'objeto_del_contrato', 'cuantia_contrato': 'valor_del_contrato',
        'tiempo_adiciones_en_dias': 'dias_adicionados', 'fecha_de_firma_del_contrato': 'fecha_de_firma', 'identificacion_del_contratista': 'documento_proveedor',
        'ruta_proceso_en_secop_i': 'urlproceso'}),
    'secop1new': ('https://www.datos.gov.co/resource/f789-7hwg.json', {
        'uid': 'uid', 'anno_firma_del_contrato': 'anno_firma_contrato', 'nit_de_la_entidad': 'nit_de_la_entidad', 'nombre_de_la_entidad': 'nombre_entidad',
        'tipo_de_proceso': 'modalidad_de_contratacion', 'estado_del_proceso': 'estado_del_proceso', 'tipo_de_contrato': 'tipo_de_contrato',
        'numero_de_constancia': 'numero_de_constancia', 'numero_de_proceso': 'numero_de_proceso', 'numero_del_contrato': 'numero_de_contrato',
        'detalle_del_objeto_a_contratar': 'detalle_del_objeto_a_contratar', 'cuantia_contrato': 'cuantia_contrato',
        'valor_total_de_adiciones': 'valor_total_de_adiciones', 'tiempo_adiciones_en_dias': 'tiempo_adiciones_en_dias',
        'tiempo_adiciones_en_meses': 'tiempo_adiciones_en_meses', 'plazo_de_ejec_del_contrato': 'plazo_de_ejec_del_contrato',
        'rango_de_ejec_del_contrato': 'rango_de_ejec_del_contrato', 'fecha_de_firma_del_contrato': 'fecha_de_firma_del_contrato',
        'identificacion_del_contratista': 'identificacion_del_contratista', 'ruta_proceso_en_secop_i': 'ruta_proceso_en_secop_i'}),
}


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


def fetch(pair, source='secop1'):
    nit, year = pair
    path = OUT / (f'{nit}-{year}.json.gz' if source == 'secop1' else f'{nit}-{year}.{source}.json.gz')
    if path.exists():
        return pair, 'cached'
    api, mapping = SOURCES[source]
    if source == 'secop1':
        select, where = FIELDS, f"nit_de_la_entidad='{nit}' and anno_cargue_secop in('{year}','{year + 1}')"
    elif source == 'secop2':
        select = sorted(set(mapping.values()))
        where = f"nit_entidad='{nit}' and fecha_de_firma between '{year}-01-01T00:00:00' and '{year}-12-31T23:59:59'"
    else:
        select, where = sorted(set(mapping.values())), f"nit_de_la_entidad='{nit}' and anno_firma_contrato='{year}'"
    rows, offset = [], 0
    while True:
        q = urllib.parse.urlencode({'$select': ','.join(select), '$where': where, '$limit': PAGE, '$offset': offset})
        req = urllib.request.Request(f'{api}?{q}', headers={'User-Agent': 'contract-signals-label-research/1.0'})
        with urllib.request.urlopen(req, timeout=600) as r:
            page = json.loads(r.read())
        if mapping:
            page = [{k: x.get(v) for k, v in mapping.items()} for x in page]
            for x in page:
                x.setdefault('anno_firma_del_contrato', (x.get('fecha_de_firma_del_contrato') or '')[:4] or None)
                if not x.get('anno_firma_del_contrato'):
                    x['anno_firma_del_contrato'] = (x.get('fecha_de_firma_del_contrato') or '')[:4]
                x['source_table'] = source
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
    import argparse
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--source', choices=sorted(SOURCES), default='secop1')
    args = p.parse_args()
    first = {'secop1': 2010, 'secop2': 2016, 'secop1new': 2018}[args.source]
    pairs = [pr for pr in entity_years() if pr[1] >= first]
    print(len(pairs), 'entity-years', args.source, flush=True)

    def safe(pair):
        try:
            return fetch(pair, args.source)
        except Exception as e:
            return pair, f'error {e}'

    with ThreadPoolExecutor(3) as pool:
        for pair, n in pool.map(safe, pairs):
            print(pair, n, flush=True)


if __name__ == '__main__':
    main()
