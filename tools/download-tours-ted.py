#!/usr/bin/env python3
"""Retrieve and verify the TED notices corresponding to the BOAMP cohort.

Searches are discovery only: the association is made from the UUID in the
 downloaded XML.  In particular, a candidate found while searching one BOAMP
 notice may belong to any member of the cohort.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/tours-notices/raw"
API = "https://api.ted.europa.eu/v3/notices/search"
FIELDS = ["publication-number", "notice-identifier", "procedure-identifier", "buyer-name", "publication-date"]
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


def text(value):
    return value.get("#text", "") if isinstance(value, dict) else (value or "")


def expected_uuid(record):
    data = json.loads(record["donnees"])
    for key in ("ContractNotice", "ContractAwardNotice", "ConcessionNotice"):
        obj = data.get("EFORMS", {}).get(key)
        if isinstance(obj, dict):
            value = text(obj.get("cbc:ID"))
            if UUID_RE.fullmatch(value):
                return value.lower()
    return None


def local(elem):
    return elem.tag.rsplit("}", 1)[-1]


def xml_notice_id(blob):
    root = ET.fromstring(blob)
    for notice in root.iter():
        if local(notice) not in ('ContractNotice', 'ContractAwardNotice', 'ConcessionNotice'): continue
        for elem in notice:
            if local(elem) == 'ID' and elem.attrib.get('schemeName') == 'notice-id':
                value = (elem.text or '').strip().lower()
                if UUID_RE.fullmatch(value): return value
    return None


def ted_publication_date(blob):
    root = ET.fromstring(blob)
    for elem in root.iter():
        if local(elem) == "PublicationDate" and (elem.text or "").strip():
            return elem.text.strip()
        # R2 legacy export has this value in the TED wrapper.
        if local(elem) == "DATE_PUB" and (elem.text or "").strip():
            value = elem.text.strip()
            if re.fullmatch(r"\d{8}", value):
                return f"{value[:4]}-{value[4:6]}-{value[6:]}"
    return None


def get_xml(publication, url, offline=False):
    started = dt.datetime.now(dt.timezone.utc).isoformat()
    path = RAW / f"ted-{publication}.xml"
    if offline:
        if not path.exists():
            return None, {"url": url, "retrieved_at": started, "error": "offline XML not saved"}
        blob = path.read_bytes()
        try:
            ET.fromstring(blob)
        except ET.ParseError as exc:
            return None, {"url": url, "retrieved_at": started, "error": f"XML parse: {exc}"}
        return blob, {"url": url, "retrieved_at": started, "bytes": len(blob), "from_cache": True}
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "tours-ted-retrieval/2.0 (public-data research)"})
        with urllib.request.urlopen(request, timeout=45) as response:
            blob = response.read()
            ctype = response.headers.get("content-type", "")
            status = response.status
        if status != 200 or not blob.strip() or "html" in ctype.lower() or not blob.lstrip().startswith(b"<?xml"):
            return None, {"url": url, "http_status": status, "content_type": ctype, "retrieved_at": started, "error": "not non-empty XML"}
        ET.fromstring(blob)
        return blob, {"url": url, "http_status": status, "content_type": ctype, "retrieved_at": started, "bytes": len(blob)}
    except (urllib.error.URLError, TimeoutError, OSError, ET.ParseError) as exc:
        return None, {"url": url, "retrieved_at": started, "error": f"request/XML: {exc}"}


def search(requested, offline):
    if offline:
        return None, None, "offline search response missing"
    body = json.dumps(requested).encode()
    request = urllib.request.Request(API, data=body, headers={"Content-Type": "application/json", "User-Agent": "tours-ted-retrieval/2.0"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.status, json.load(response), None
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        return None, None, str(exc)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline-search", action="store_true", help="use saved ted-api-search-*.json responses and saved XML only")
    args = parser.parse_args()
    records = json.loads((RAW / "api-records.json").read_text())
    expected = {r["idweb"]: expected_uuid(r) for r in records}
    uuid_to_idweb = {uuid: rid for rid, uuid in expected.items() if uuid}
    old_manifest = RAW / "ted-manifest.json"
    initial = RAW / "ted-manifest-initial.json"
    if old_manifest.exists() and not initial.exists():
        shutil.copyfile(old_manifest, initial)

    manifest = {"created_at": dt.datetime.now(dt.timezone.utc).isoformat(), "api_url": API,
                "search_mode": "offline-cache" if args.offline_search else "online",
                "entries": [], "downloads": [], "errors": []}
    fetched = set()
    verified = set()

    def examine(publication, url, discovery_idweb, discovery_date=None):
        if publication in fetched:
            return
        fetched.add(publication)
        blob, meta = get_xml(publication, url, args.offline_search)
        meta.update({"publication_number": publication, "discovery_idweb": discovery_idweb})
        if blob is None:
            manifest["errors"].append(meta)
            return
        actual = xml_notice_id(blob)
        meta.update({"actual_uuid": actual, "ted_publication_date": ted_publication_date(blob)})
        matched = uuid_to_idweb.get(actual)
        if not matched:
            # Do not write unrelated candidate XML files.
            meta["error"] = "root notice UUID not in global BOAMP cohort"
            manifest["errors"].append(meta)
            return
        meta.update({"matched_idweb": matched, "verified": True})
        path = RAW / f"ted-{publication}.xml"
        path.write_bytes(blob)
        meta["file"] = str(path.relative_to(ROOT))
        manifest["downloads"].append(meta)
        verified.add(matched)

    for record in records:
        rid = record["idweb"]
        date = dt.date.fromisoformat(record["dateparution"][:10])
        lo, hi = date - dt.timedelta(days=45), date + dt.timedelta(days=45)
        buyer = (record.get("nomacheteur") or "").strip()
        requested = {"query": f'buyer-name="{buyer}" AND publication-date>={lo:%Y%m%d} AND publication-date<={hi:%Y%m%d}', "fields": FIELDS, "page": 1, "limit": 100}
        cache = RAW / f"ted-api-search-{rid}.json"
        at = dt.datetime.now(dt.timezone.utc).isoformat()
        if args.offline_search:
            try:
                saved = json.loads(cache.read_text())
                status, payload = saved.get("http_status"), saved.get("response", {})
                requested, at = saved.get("request", requested), saved.get("retrieved_at", at)
            except (OSError, json.JSONDecodeError) as exc:
                manifest["errors"].append({"idweb": rid, "retrieved_at": at, "error": f"cached search: {exc}"})
                continue
        else:
            status, payload, error = search(requested, False)
            if error:
                manifest["errors"].append({"idweb": rid, "request": requested, "retrieved_at": at, "error": f"API request/JSON: {error}"})
                continue
            cache.write_text(json.dumps({"request": requested, "http_status": status, "retrieved_at": at, "response": payload}, ensure_ascii=False, indent=2) + "\n")
        notices = payload.get("notices", []) if status == 200 else []
        entry = {"idweb": rid, "expected_uuid": expected[rid], "buyer": buyer, "boamp_date": record["dateparution"], "request": requested, "http_status": status, "retrieved_at": at, "total": payload.get("totalNoticeCount"), "candidates": []}
        for notice in notices:
            publication = notice.get("publication-number")
            url = notice.get("links", {}).get("xml", {}).get("MUL")
            if publication and url:
                entry["candidates"].append(publication)
                examine(publication, url, rid, notice.get("publication-date"))
        manifest["entries"].append(entry)
        if not args.offline_search:
            time.sleep(0.15)

    # Cached discovery is deliberately exhausted before exact TED lookups.  Do
    # not use API names or dates as evidence of an association.
    if not args.offline_search:
        for record in records:
            rid, wanted = record["idweb"], expected[record["idweb"]]
            if rid in verified or not wanted:
                continue
            requested = {"query": f'notice-identifier="{wanted}" OR procedure-identifier="{record.get("contractfolderid", "")}"', "fields": FIELDS, "page": 1, "limit": 100}
            at = dt.datetime.now(dt.timezone.utc).isoformat()
            status, payload, error = search(requested, False)
            cache = RAW / f"ted-api-search-exact-{rid}.json"
            if error:
                manifest["errors"].append({"idweb": rid, "request": requested, "retrieved_at": at, "error": f"exact API request/JSON: {error}"})
                continue
            cache.write_text(json.dumps({"request": requested, "http_status": status, "retrieved_at": at, "response": payload}, ensure_ascii=False, indent=2) + "\n")
            for notice in payload.get("notices", []) if status == 200 else []:
                publication = notice.get("publication-number")
                url = notice.get("links", {}).get("xml", {}).get("MUL")
                if publication and url:
                    examine(publication, url, rid, notice.get("publication-date"))
            time.sleep(0.15)

    # 461026-2023 is linked to 25-20885 by the BOAMP's explicit reference.
    legacy_pub, legacy_url, linked = "461026-2023", "https://ted.europa.eu/en/notice/461026-2023/xml", "25-20885"
    boamp = next(r for r in records if r["idweb"] == linked)
    ref = json.loads(boamp["donnees"])["EFORMS"]["ContractAwardNotice"]["cac:TenderingProcess"]["cac:NoticeDocumentReference"]["cbc:ID"]
    if ref == legacy_pub:
        blob, meta = get_xml(legacy_pub, legacy_url, args.offline_search)
        if blob is not None:
            root = ET.fromstring(blob)
            doc_id = root.attrib.get("DOC_ID")
            publication_number = next((e.text.strip() for e in root.iter() if local(e) == "NO_DOC_OJS" and e.text), None)
            meta.update({"publication_number": legacy_pub, "matched_idweb": linked, "ted_publication_date": ted_publication_date(blob), "verified": doc_id == legacy_pub and publication_number == "2023/S 144-461026", "verified_reason": "BOAMP 25-20885 NoticeDocumentReference"})
            if meta["verified"]:
                path = RAW / f"ted-{legacy_pub}.xml"; path.write_bytes(blob); meta["file"] = str(path.relative_to(ROOT)); manifest["downloads"].append(meta)
            else:
                meta["error"] = "legacy publication number mismatch"; manifest["errors"].append(meta)
        else:
            manifest["errors"].append(meta)

    destination = 'ted-manifest-cache-validation.json' if args.offline_search else 'ted-manifest.json'
    (RAW / destination).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(f"verified downloads: {len(manifest['downloads'])}; errors: {len(manifest['errors'])}; matched idwebs: {len(verified)}")


if __name__ == "__main__":
    main()
