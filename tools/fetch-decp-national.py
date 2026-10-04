#!/usr/bin/env python3
"""Download the national consolidated DECP (tabular parquet) once, outside git.

Source: data.gouv.fr dataset 608c055b35eb4e6ee20eb325 "Données essentielles de la commande publique
consolidées (format tabulaire)" (decp.info / colibre.fr, Licence Ouverte 2.0), resource decp.parquet.
It consolidates the same arrêté 22 Dec 2022 data as the Ministry's JSON files from more sources, one row per
contract-version-holder, with offresRecues, procedure, dateNotification, datePublicationDonnees,
dureeMois, codeCPV, modification_id and montant.

The file is streamed to ~/.cache/contract-signals/decp-national/ with HTTP Range resume, hashed (SHA-256) and
checked against the SHA-1 published by data.gouv. A manifest is written next to it. Nothing is written inside the
repository. If the file already exists and matches the manifest nothing is downloaded again.
"""
import argparse
import hashlib
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DATASET = "608c055b35eb4e6ee20eb325"
API = f"https://www.data.gouv.fr/api/1/datasets/{DATASET}/"
RESOURCE_TITLE = "decp.parquet"
CACHE = Path.home() / ".cache/contract-signals/decp-national"
UA = {"User-Agent": "contract-signals-research/1.0 (offline calibration)"}


def get_json(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return json.load(r)


def pick_resource(meta, title=RESOURCE_TITLE):
    found = [r for r in meta.get("resources", []) if r.get("title") == title]
    if len(found) != 1:
        raise ValueError(f"expected exactly one resource titled {title}, found {len(found)}")
    return found[0]


def file_hashes(path, chunk=1 << 22):
    sha256, sha1 = hashlib.sha256(), hashlib.sha1()
    with open(path, "rb") as fh:
        while block := fh.read(chunk):
            sha256.update(block)
            sha1.update(block)
    return sha256.hexdigest(), sha1.hexdigest()


def download(url, dest, size, chunk=1 << 20):
    """Resumable streaming download into dest.part, renamed on completion."""
    part = Path(str(dest) + ".part")
    have = part.stat().st_size if part.exists() else 0
    if have > size:
        part.unlink()
        have = 0
    while have < size:
        req = urllib.request.Request(url, headers=dict(UA, Range=f"bytes={have}-"))
        with urllib.request.urlopen(req, timeout=120) as r:
            if have and r.status != 206:
                part.unlink()
                have = 0
                continue
            with open(part, "ab" if have else "wb") as out:
                while block := r.read(chunk):
                    out.write(block)
                    have += len(block)
                    print(f"\r{have / 1e6:.0f}/{size / 1e6:.0f} MB", end="", file=sys.stderr)
    print(file=sys.stderr)
    if part.stat().st_size != size:
        raise RuntimeError("size mismatch after download")
    part.rename(dest)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--cache", type=Path, default=CACHE)
    args = ap.parse_args(argv)
    args.cache.mkdir(parents=True, exist_ok=True)
    manifest_path = args.cache / "manifest.json"
    meta = get_json(API)
    res = pick_resource(meta)
    dest = args.cache / "decp.parquet"
    if dest.exists() and manifest_path.exists():
        old = json.loads(manifest_path.read_text())
        if old.get("resource_url") == res["url"] and dest.stat().st_size == res["filesize"]:
            print("already downloaded:", dest)
            return 0
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if not dest.exists() or dest.stat().st_size != res["filesize"]:
        download(res["url"], dest, res["filesize"])
    sha256, sha1 = file_hashes(dest)
    published = (res.get("checksum") or {}).get("value")
    if published and published != sha1:
        raise RuntimeError(f"SHA-1 {sha1} differs from published {published}; delete {dest} and retry")
    manifest = {"dataset_id": DATASET, "dataset_title": meta["title"], "dataset_page": meta.get("page"),
                "publisher": (meta.get("organization") or {}).get("name"), "licence": meta.get("license"),
                "resource_id": res["id"], "resource_title": res["title"], "resource_url": res["url"],
                "resource_last_modified": res.get("last_modified"), "size_bytes": dest.stat().st_size,
                "sha256": sha256, "sha1": sha1, "published_sha1": published, "retrieved_at": started,
                "schema_url": next((r["url"] for r in meta["resources"] if r.get("title") == "schema.json"), None)}
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
