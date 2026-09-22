#!/usr/bin/env python3
"""SECOP II (Colombia) pilot importer — first international cohort.

Bounded, reproducible, static-first. Downloads a pre-announced cohort
(three buyers, one 24-month signature window) from the official Socrata
endpoint of datos.gov.co, keeps every raw paginated response as
provenance, and normalizes a self-contained extract for the static
explorer.

Rules inherited from the project charter:
- stdlib only; no build step; no runtime API calls from the site;
- original Spanish text is never translated or normalized;
- amounts stay in COP (never converted to euros);
- no French threshold is applied to Colombian rows: jurisdiction-specific
  indicators live in script.js and docs/score-colombia.md;
- no score-based selection: the cohort was announced before download.

Usage:
  python tools/import-colombia-secop2.py --download   # network snapshot
  python tools/import-colombia-secop2.py --offline    # re-normalize from raw
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(ROOT, "data", "colombia-secop2", "raw")
DATASET_URL = "https://www.datos.gov.co/resource/jbjy-vk9h.json"
METADATA_URL = "https://www.datos.gov.co/api/views/jbjy-vk9h"
LICENSE = "Creative Commons Attribution | Share Alike 4.0 International (CC BY-SA 4.0)"
ATTRIBUTION = "Agencia Nacional de Contratación Pública - Colombia Compra Eficiente, Bogotá D.C."
WINDOW_START = "2024-09-01"
WINDOW_END = "2026-09-01"  # exclusive
PAGE_SIZE = 1000
USER_AGENT = "contract-signals/0.1 (static transparency explorer; offline-first)"

# Cohort announced (2026-09-22) BEFORE any download, after volume-only
# count queries. One buyer per administrative level; volumes were the
# only criterion consulted. Usaquén shares the generic district NIT
# 899999061 with the other alcaldías locales, so it is matched by exact
# normalized entity name; the other two by NIT.
BUYERS = [
    {
        "key": "men",
        "level": "Nacional",
        "nit": "899999001",
        "name": "MINISTERIO DE EDUCACION NACION (MEN)",
        "match": {"field": "nit_entidad", "value": "899999001"},
    },
    {
        "key": "caldas",
        "level": "Departamental",
        "nit": "890801052",
        "name": "GOBERNACION DE CALDAS",
        "match": {"field": "nit_entidad", "value": "890801052"},
    },
    {
        "key": "usaquen",
        "level": "Municipal-local (Bogotá)",
        "nit": "899999061",
        "name": "ALCALDIA LOCAL DE USAQUEN",
        "match": {"field": "nombre_entidad", "value": "ALCALDIA LOCAL DE USAQUEN"},
        "note": "Generic shared district NIT; exact entity-name match, NIT kept as-is.",
    },
]

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")


def window_where() -> str:
    return f"fecha_de_firma >= '{WINDOW_START}' AND fecha_de_firma < '{WINDOW_END}'"


def buyer_where(buyer: dict) -> str:
    m = buyer["match"]
    return f"{window_where()} AND {m['field']} = '{m['value']}'"


def fetch_json(url: str, retries: int = 4, timeout: int = 60):
    last = None
    for attempt in range(1, retries + 1):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                if response.status != 200:
                    raise urllib.error.URLError(f"HTTP {response.status}")
                return response.status, json.loads(response.read().decode("utf-8"))
        except Exception as error:  # noqa: BLE001 - log and retry
            last = error
            time.sleep(2 * attempt)
    raise RuntimeError(f"failed after {retries} attempts: {url} ({last})")


def socrata_get(params: dict):
    query = urllib.parse.urlencode(params)
    return fetch_json(f"{DATASET_URL}?{query}")


# ---------------------------------------------------------------- download
def download() -> None:
    os.makedirs(RAW_DIR, exist_ok=True)
    started = dt.datetime.now(dt.timezone.utc).isoformat()
    manifest = {
        "dataset": DATASET_URL,
        "metadata": METADATA_URL,
        "license": LICENSE,
        "attribution": ATTRIBUTION,
        "window": {"startInclusive": WINDOW_START, "endExclusive": WINDOW_END,
                   "basis": "fecha_de_firma (signature date), per cohort announcement"},
        "cohortAnnouncedBeforeDownload": True,
        "retrievalStartedAt": started,
        "buyers": BUYERS,
        "pageSize": PAGE_SIZE,
        "pages": [],
    }
    grand_total = 0
    for buyer in BUYERS:
        where = buyer_where(buyer)
        status, counted = socrata_get({"$select": "count(1)", "$where": where})
        expected = int(counted[0]["count_1"])
        print(f"[{buyer['key']}] expected rows: {expected}")
        offset = 0
        downloaded = 0
        while True:
            params = {"$limit": PAGE_SIZE, "$offset": offset, "$where": where,
                      "$order": "id_contrato, proceso_de_compra"}
            status, rows = socrata_get(params)
            if status != 200 or not isinstance(rows, list):
                raise RuntimeError(f"unexpected response for {buyer['key']} at offset {offset}")
            if not rows:
                break
            path = os.path.join(RAW_DIR, f"page-{buyer['key']}-{offset // PAGE_SIZE:05d}.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(rows, handle, ensure_ascii=False, separators=(",", ":"))
            manifest["pages"].append({
                "buyer": buyer["key"], "offset": offset, "rows": len(rows),
                "file": os.path.relpath(path, ROOT),
                "url": f"{DATASET_URL}?{urllib.parse.urlencode(params)}",
            })
            downloaded += len(rows)
            offset += PAGE_SIZE
            if len(rows) < PAGE_SIZE:
                break
            time.sleep(1.0)
        if downloaded != expected:
            raise RuntimeError(f"[{buyer['key']}] downloaded {downloaded} != expected {expected}")
        grand_total += downloaded
        print(f"[{buyer['key']}] downloaded {downloaded} rows OK")
    manifest["retrievalFinishedAt"] = dt.datetime.now(dt.timezone.utc).isoformat()
    manifest["totalRows"] = grand_total
    with open(os.path.join(RAW_DIR, "manifest.json"), "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=1)
    print(f"total rows: {grand_total}; manifest written")


# ---------------------------------------------------------------- normalize
def unwrap_url(value):
    if isinstance(value, dict):
        return value.get("url") or value.get("description") or json.dumps(value, ensure_ascii=False)
    return value


def to_date(value):
    if isinstance(value, str) and DATE_RE.match(value):
        return value[:10]
    return None


def normalize_row(raw: dict, buyer: dict) -> dict:
    def num(key):
        value = raw.get(key)
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, str):
            cleaned = value.replace(",", "").strip()
            try:
                return float(cleaned) if cleaned else None
            except ValueError:
                return None
        return None

    objeto = raw.get("objeto_del_contrato") or raw.get("descripcion_del_proceso") \
        or raw.get("tipo_de_contrato") or raw.get("id_contrato") or buyer["name"]
    contrato = raw.get("id_contrato") or ""
    return {
        "id": f"secop2-{buyer['key']}-{contrato or raw.get('proceso_de_compra') or 'sans-id'}",
        "cohortId": "secop2-three-buyers-2024-2026",
        "dataFamily": "secop2",
        "dataStatus": "verified",
        "buyer": raw.get("nombre_entidad") or buyer["name"],
        "buyerNit": raw.get("nit_entidad"),
        "buyerLevel": buyer["level"],
        "buyerOrden": raw.get("orden"),
        "departamento": raw.get("departamento"),
        "ciudad": raw.get("ciudad"),
        "date": to_date(raw.get("fecha_de_firma")),
        "contractId": contrato or None,
        "processId": raw.get("proceso_de_compra") or None,
        "processUrl": unwrap_url(raw.get("urlproceso")),
        "supplier": raw.get("proveedor_adjudicado") or None,
        "supplierIds": ([{"identifierType": raw.get("tipodocproveedor") or "Documento",
                          "id": str(raw.get("documento_proveedor"))}]
                        if raw.get("documento_proveedor") not in (None, "") else []),
        "supplierGroup": raw.get("es_grupo"),
        "supplierSme": raw.get("es_pyme"),
        "description": objeto,
        "procedure": raw.get("modalidad_de_contratacion") or None,
        "procedureJustification": raw.get("justificacion_modalidad_de") or None,
        "contractStatus": raw.get("estado_contrato") or None,
        "contractType": raw.get("tipo_de_contrato") or None,
        "sector": raw.get("sector") or None,
        "spendingDestination": raw.get("destino_gasto") or None,
        "amount": num("valor_del_contrato"),
        "amountPaid": num("valor_pagado"),
        "amountInvoiced": num("valor_facturado"),
        "amountAmortized": num("valor_amortizado"),
        "amountPendingPayment": num("valor_pendiente_de_pago"),
        "amountPendingExecution": num("valor_pendiente_de_ejecucion"),
        "currency": "COP",
        "durationOriginal": raw.get("duraci_n_del_contrato") or None,
        "startDate": to_date(raw.get("fecha_de_inicio_del_contrato")),
        "endDate": to_date(raw.get("fecha_de_fin_del_contrato")),
        "lastUpdated": raw.get("ultima_actualizacion") or None,
        "postConflict": raw.get("espostconflicto"),
        "reversion": raw.get("reversion"),
        "liquidation": raw.get("liquidaci_n"),
        "source": DATASET_URL,
        "sourceLabel": "SECOP II — Contratos Electrónicos (datos.gov.co, JSON)",
        "amountBasis": "Valor del contrato declarado (COP); no convert, no sum with other currencies.",
        "dateNote": "fecha_de_firma within announced 24-month window; other dates kept separately.",
        "notes": ("Registro SECOP II: una fila = un contrato con su proceso y proveedor declarados. "
                  "Texto original conservado; sin indicadores heurísticos de jurisdicción francesa."),
    }


def join_verification(rows: list) -> dict:
    """Document the process–contract–supplier join quality on real rows."""
    total = len(rows)
    with_contract = sum(1 for r in rows if r["contractId"])
    with_process = sum(1 for r in rows if r["processId"])
    with_supplier_name = sum(1 for r in rows if r["supplier"])
    with_supplier_id = sum(1 for r in rows if r["supplierIds"])
    with_url = sum(1 for r in rows if r["processUrl"])
    with_amount = sum(1 for r in rows if r["amount"] is not None)
    ids = [r["id"] for r in rows]
    duplicate_ids = total - len(set(ids))
    return {
        "rows": total,
        "rowsWithContractId": with_contract,
        "rowsWithProcessId": with_process,
        "rowsWithSupplierName": with_supplier_name,
        "rowsWithSupplierIdentifier": with_supplier_id,
        "rowsWithProcessUrl": with_url,
        "rowsWithDeclaredAmount": with_amount,
        "duplicateExtractIds": duplicate_ids,
        "verdict": ("Each SECOP II row already carries its process, contract and supplier "
                    "declaration; the join is intra-row, so it does not depend on a second "
                    "source. Completeness is documented above, not assumed."),
        "notClaimed": ("No offers/proposals and no payment-reconciliation indicators are "
                       "claimed: this dataset alone does not provide an offers table, and "
                       "paid amounts are declarations, not audited payments."),
    }


def per_buyer_counts(rows: list) -> dict:
    counts = {}
    for row in rows:
        key = row["buyerLevel"]
        entry = counts.setdefault(key, {"rows": 0, "withAmount": 0, "withSupplierId": 0})
        entry["rows"] += 1
        entry["withAmount"] += 1 if row["amount"] is not None else 0
        entry["withSupplierId"] += 1 if row["supplierIds"] else 0
    return counts


def liquidation_counts(rows: list) -> dict:
    counts = {}
    for row in rows:
        key = row["liquidation"] if row["liquidation"] is not None else "unknown"
        counts[key] = counts.get(key, 0) + 1
    return counts


def offline() -> None:
    manifest_path = os.path.join(RAW_DIR, "manifest.json")
    if not os.path.exists(manifest_path):
        sys.exit("no raw snapshot found; run with --download first")
    with open(manifest_path, encoding="utf-8") as handle:
        manifest = json.load(handle)
    raw_rows = []
    for page in manifest["pages"]:
        with open(os.path.join(ROOT, page["file"]), encoding="utf-8") as handle:
            raw_rows.extend(json.load(handle))
    buyer_by_key = {b["key"]: b for b in manifest["buyers"]}
    rows = []
    for raw in raw_rows:
        buyer = next(b for b in manifest["buyers"]
                     if raw.get(b["match"]["field"]) == b["match"]["value"]
                     or (b["key"] == "usaquen" and b["match"]["field"] == "nombre_entidad"
                         and raw.get("nombre_entidad") == b["match"]["value"]))
        rows.append(normalize_row(raw, buyer))
    rows.sort(key=lambda r: (r["buyerLevel"], r["date"] or "", r["id"]))
    dataset_path = os.path.join(ROOT, "data", "colombia-secop2.json")
    with open(dataset_path, "w", encoding="utf-8") as handle:
        json.dump(rows, handle, ensure_ascii=False, separators=(",", ":"))
    coverage = {
        "source": DATASET_URL,
        "metadataUrl": METADATA_URL,
        "license": LICENSE,
        "attribution": ATTRIBUTION,
        "userAgent": USER_AGENT,
        "cohort": {
            "announcedBeforeDownload": True,
            "selectionBasis": ("Administrative-level diversity and documented volumes only "
                               "(count queries); no score, indicator or anomaly was consulted."),
            "window": {"field": "fecha_de_firma", "startInclusive": WINDOW_START,
                       "endExclusive": WINDOW_END},
            "buyers": BUYERS,
        },
        "retrieval": {"startedAt": manifest["retrievalStartedAt"],
                      "finishedAt": manifest["retrievalFinishedAt"],
                      "totalRawRows": manifest["totalRows"], "pageSize": PAGE_SIZE},
        "normalization": {
            "language": "Original Spanish preserved verbatim; no translation.",
            "currency": "COP only; no conversion, no cross-currency sums.",
            "duration": ("duraci_n_del_contrato kept as original free text at import; never rewritten. "
                         "The explorer parses it read-only for the duration check (docs/score-colombia.md)."),
            "identityCaveat": ("Bogotá alcaldías locales share the generic NIT 899999061; "
                               "Usaquén is matched by exact entity name and the shared NIT is "
                               "kept as-is. Entity names keep their original noise (//, *, etc.)."),
            "rowIdentity": "secop2-{buyerKey}-{id_contrato}; verified unique below.",
        },
        "counts": {
            "rawRows": len(raw_rows),
            "normalizedRows": len(rows),
            "perBuyer": per_buyer_counts(rows),
            "liquidation": liquidation_counts(rows),
        },
        "joinVerification": join_verification(rows),
        "indicators": {
            "status": "implemented",
            "since": "2026-09-22",
            "framework": "3.0",
            "method": "docs/score-colombia.md",
            "checks": ["secop2-plurality-award", "secop2-repeated-plurality",
                       "secop2-concentration", "secop2-long-duration"],
            "outOfScopeFrenchChecks": ["single-bid", "short-bidding-period",
                                       "amount-increase", "repeated-single-bid"],
            "note": ("Jurisdiction-specific eligibility and thresholds; the bare declared "
                     "modality (direct family ≈ 82 % of this cohort) and ordinary justifications "
                     "(professional services, interadministrative agreements, minimum-amount "
                     "rules) add no points. Amounts in COP stay visible and sort only. "
                     "No offers-based indicator: no offers table was imported."),
        },
        "limitations": [
            "Not exhaustive: only the three announced buyers in the 24-month window.",
            "SECOP II contract rows are declarations; amounts and statuses are not audited payments.",
            "No offers/proposals table was downloaded; no offer-count indicator exists for Colombia.",
            "No country ranking, no currency conversion, no comparison with French cohorts.",
            "Editorial thresholds of docs/score-colombia.md are not Colombian legal thresholds; "
            "a signal is not a finding of irregularity, and no flag proves regularity.",
        ],
        "reproduction": [
            "python tools/import-colombia-secop2.py --download",
            "python tools/import-colombia-secop2.py --offline",
            "node tests/colombia.cjs",
        ],
        "currentIndex": {"version": "3.0", "note": ("v3.0 framework with the jurisdiction-specific "
                          "SECOP II check set: docs/score-v3.md (French cohorts) and "
                          "docs/score-colombia.md (Colombia pilot).")},
    }
    with open(os.path.join(ROOT, "data", "colombia-secop2-coverage.json"), "w", encoding="utf-8") as handle:
        json.dump(coverage, handle, ensure_ascii=False, indent=1)
    print(f"normalized rows: {len(rows)}; extract and coverage written")
    print(json.dumps(coverage["counts"]["perBuyer"], ensure_ascii=False, indent=1))
    print(json.dumps(coverage["joinVerification"], ensure_ascii=False, indent=1)[:600])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true", help="network snapshot of the announced cohort")
    parser.add_argument("--offline", action="store_true", help="re-normalize from the raw snapshot")
    args = parser.parse_args()
    if args.download:
        download()
    if args.offline or not (args.download or args.offline):
        offline()


if __name__ == "__main__":
    main()
