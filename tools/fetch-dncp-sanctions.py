#!/usr/bin/env python3
"""Minimised DNCP sanction snapshot for the suppliers of the Paraguay cohorts.

For every supplier RUC in data/paraguay-dncp*.json, reads /suppliers/{ruc} from the
DNCP API and keeps only: RUC, legal-entity type, and each sanction's type, status,
description and period. Contact details, addresses and raw responses are NOT kept.

  python tools/fetch-dncp-sanctions.py            # refresh data/dncp-sanctions.json
  python tools/fetch-dncp-sanctions.py --offline  # re-apply the snapshot to both extracts

Sanctions are context outside the index. A row is labelled only when a debarment
(INHABILITACION) period covers the award date; warnings, fines and other periods
are not attached to the contract.
"""
import argparse
import gzip
import importlib.util
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from personal_ids import mask  # noqa: E402
SNAPSHOT = ROOT / "data/dncp-sanctions.json"
EXTRACTS = [ROOT / "data/paraguay-dncp.json", ROOT / "data/paraguay-dncp-3buyers.json"]
spec = importlib.util.spec_from_file_location("dncp", ROOT / "tools/import-paraguay-dncp.py")
dncp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dncp)


def supplier_ids():
    """Real RUCs to query. The extracts hold persons' RUCs pseudonymised, so the RUCs are read
    back from the raw records and kept when their pseudonym is a published supplier."""
    wanted = {r["supplierIds"][0]["id"] for path in EXTRACTS for r in json.loads(path.read_text(encoding="utf-8")) if r["supplierIds"]}
    found = set()
    for raw in (ROOT / "data/paraguay-dncp/raw", ROOT / "data/paraguay-dncp-3buyers/raw"):
        for f in raw.rglob("*"):
            if f.is_file():
                data = gzip.decompress(f.read_bytes()) if f.suffix == ".gz" else f.read_bytes()
                found |= set(re.findall(r"PY-RUC-\d+-\d", data.decode("utf-8", "ignore")))
    published = {x for x in wanted if x.startswith("PY-RUC-")}  # company and non-numeric ids are published as is
    return sorted(published | {ruc for ruc in found if mask("RUC", ruc) in wanted})


def minimise(party_id, payload):
    found = [s for s in payload.get("list") or payload.get("suppliers") or ([payload["supplier"]] if "supplier" in payload else [])
             if s.get("id") == party_id]
    if len(found) != 1:
        return {"id": mask("RUC", party_id), "status": "no exact match", "sanctions": []}
    details = found[0].get("details") or {}
    return {"id": mask("RUC", party_id), "status": "available", "entityType": details.get("legalEntityTypeDetail"),
            "sanctions": [{"type": s.get("type"), "status": s.get("status"), "description": s.get("description"),
                           "start": ((s.get("period") or {}).get("startDate") or "")[:10] or None,
                           "end": ((s.get("period") or {}).get("endDate") or "")[:10] or None}
                          for s in details.get("sanctions") or []]}


def download():
    started = datetime.now(timezone.utc).isoformat()
    out = []
    for i, party_id in enumerate(supplier_ids(), 1):
        ruc = party_id.removeprefix("PY-RUC-")
        payload = dncp.get_json(dncp.BASE + "/search/suppliers?" + "identifier.id=" + quote(ruc) + "&items_per_page=5")
        out.append(minimise(party_id, payload))
        if i % 25 == 0:
            print(f"{i} suppliers", flush=True)
    snapshot = {"source": dncp.BASE + "/search/suppliers?identifier.id={ruc}", "license": "CC BY 4.0",
                "retrievedAt": started, "kept": "RUC (pseudonymised for natural persons, see tools/personal_ids.py), legal-entity type, sanction type/status/description/period only; no contacts, addresses or raw responses.",
                "suppliers": out}
    SNAPSHOT.write_text(json.dumps(snapshot, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(out)} suppliers, {sum(bool(s['sanctions']) for s in out)} with at least one sanction")


def apply():
    """Pseudonymise persons' RUCs in the snapshot (idempotent), then re-run both Paraguay
    imports offline; they read the snapshot themselves."""
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    snapshot["suppliers"] = [{**s, "id": mask("RUC", s["id"])} for s in snapshot["suppliers"]]
    snapshot["kept"] = snapshot["kept"].replace("RUC, legal-entity", "RUC (pseudonymised for natural persons, see tools/personal_ids.py), legal-entity") if "pseudonymised" not in snapshot["kept"] else snapshot["kept"]
    SNAPSHOT.write_text(json.dumps(snapshot, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for key in dncp.COHORTS:
        dncp.offline(dncp.COHORTS[key])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    if not args.offline:
        download()
    apply()
