#!/usr/bin/env python3
"""Small anonymous access checks; no foreign procurement cohorts or personal samples saved.

Usage:
  python tools/check-international-access.py              # run every check, append to the log
  python tools/check-international-access.py Paraguay     # only checks whose label contains "Paraguay"
"""
import concurrent.futures
import json
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

CHECKS = [
 ('Colombia SECOP II dataset metadata','https://www.datos.gov.co/api/views/jbjy-vk9h'),
 ('Colombia SECOP II one-row API','https://www.datos.gov.co/resource/jbjy-vk9h.json?$limit=1'),
 ('Paraguay DNCP OCDS Swagger','https://www.contrataciones.gov.py/datos/api/v3/doc/swagger.json'),
 ('Brazil PNCP bounded page, 10 maximum requested','https://pncp.gov.br/api/consulta/v1/contratos?dataInicial=20250101&dataFinal=20250101&pagina=1&tamanhoPagina=10'),
 ('Moldova official open-data page','https://mtender.gov.md/public/open-data'),
 ('Ukraine Prozorro public tender index, one item','https://public.api.openprocurement.org/api/2.5/tenders?limit=1'),
 ('TED official XML for an already UUID-verified notice','https://ted.europa.eu/en/notice/8206-2025/xml'),
 ('Paraguay DNCP official data portal','https://www.contrataciones.gov.py/datos/'),
 ('Paraguay OCDS record by documented example OCID, no token','https://www.contrataciones.gov.py/datos/api/v3/doc/ocds/record/ocds-03ad3f-365292-1'),
 ('Paraguay OCDS search processes one row with date filter, no token','https://www.contrataciones.gov.py/datos/api/v3/doc/search/processes?page=1&items_per_page=1&fecha_desde=2026-01-01&fecha_hasta=2026-01-31&tipo_fecha=publicacion_llamado'),
 ('Paraguay OCDS parameters catalog, no token','https://www.contrataciones.gov.py/datos/api/v3/doc/parameters/parameters'),
]

def check(item):
    label,url=item
    result={'label':label,'url':url,'retrieved_utc':datetime.now(timezone.utc).isoformat(),'authentication':'no token or credentials sent'}
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'procurement-explorer-access-check/1.0'})
        with urllib.request.urlopen(req,timeout=25) as response:
            data=response.read(250001)
            result.update(http_status=response.status,response_type=response.headers.get('Content-Type'),bytes_read=len(data),truncated=len(data)>250000)
        if not result['truncated']:
            try:
                payload=json.loads(data)
                if isinstance(payload,list):
                    result['json_array_count']=len(payload)
                elif isinstance(payload,dict):
                    result['top_level_keys']=list(payload)
                    if 'licenseId' in payload: result['license_id']=payload['licenseId']
                    if 'security' in payload: result['global_security']=payload['security']
                    if 'paths' in payload: result['documented_path_count']=len(payload['paths'])
                    if 'name' in payload: result['dataset_name']=payload['name']
                    if 'license' in payload: result['license']=payload['license']
                    if 'publicationPolicy' in payload: result['publication_policy']=payload['publicationPolicy']
                    if 'version' in payload: result['ocds_version']=payload['version']
                    if 'publisher' in payload and isinstance(payload['publisher'],dict): result['publisher_name']=payload['publisher'].get('name')
                    if isinstance(payload.get('data'),list): result['data_array_count']=len(payload['data'])
                    if isinstance(payload.get('list'),list): result['list_count']=len(payload['list'])
                    for k in ('totalRegistros','totalPaginas','numeroPagina','paginasRestantes','empty','$count','count','total'):
                        if k in payload: result[k]=payload[k]
            except (ValueError,UnicodeError):
                pass
        result['sample_preserved']=False
    except urllib.error.HTTPError as exc:
        body=exc.read(400)
        result.update(http_status=exc.code,response_type=exc.headers.get('Content-Type'),error='HTTP error; access not established')
        try:
            result['error_body']=body.decode('utf-8','replace')
        except Exception:
            pass
    except (OSError,TimeoutError) as exc:
        result['error']=str(exc)
    return result

if __name__=='__main__':
    label_filter=sys.argv[1] if len(sys.argv)>1 else None
    selected=[c for c in CHECKS if label_filter is None or label_filter.lower() in c[0].lower()]
    if not selected:
        sys.exit(f'No checks match label substring {label_filter!r}')
    path=Path(__file__).resolve().parents[1]/'data/international-access-checks.json'
    report=json.loads(path.read_text()) if path.exists() else {'checks':[]}
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        report['checks'].extend(pool.map(check,selected))
    report['retrieved_utc_note']='Per-request start timestamps; small anonymous metadata/API checks, not bulk cohorts. HTML access does not establish API availability or a reuse licence. Failed attempts are retained.'
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report['checks'][-len(selected):],ensure_ascii=False,indent=2))
