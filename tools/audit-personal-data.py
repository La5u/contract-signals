#!/usr/bin/env python3
"""Report aggregate schema/field-presence indicators without printing data values.

Run from the repository root: python tools/audit-personal-data.py
The scan is heuristic: a field name is not proof that every value is personal data.
"""

from collections import Counter
import gzip
import json
from pathlib import Path
import re
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
DATASETS = {
    "colombia-secop2": ["data/colombia-secop2.json", "data/colombia-secop2/raw"],
    "paraguay-dncp": ["data/paraguay-dncp.json", "data/paraguay-dncp-3buyers.json", "data/paraguay-dncp/raw", "data/paraguay-dncp-3buyers/raw"],
    "ukraine-prozorro": ["data/prozorro.json", "data/prozorro/raw"],
    "ted-portugal": ["data/ted-portugal.json", "data/ted-portugal/raw"],
    "ted-romania": ["data/ted-romania.json", "data/ted-romania/raw"],
}
SENSITIVE = re.compile(r"person|contact|email|phone|tel|telefono|name|nombre|party|parties|direcci|address|domicil|identif|document|cedula|c[eé]dula|nit|ruc|tax|bank|banco|account|cuenta|represent|supervisor|ordenador|signatory|natural|individual", re.I)
PLACEHOLDERS = {"no definido", "no aplica", "no disponible", "n/a", "na", "null", "none", "sin informacion"}


def is_nonempty(value):
    return value not in (None, "", [], {}) and not (isinstance(value, str) and not value.strip())


def is_meaningful(value):
    """Exclude empty values and known placeholder labels, without retaining values."""
    if not is_nonempty(value):
        return False
    if isinstance(value, str):
        normalized = unicodedata.normalize("NFKD", value.strip().casefold())
        normalized = "".join(char for char in normalized if not unicodedata.combining(char))
        return normalized not in PLACEHOLDERS
    return True


def load(path):
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as stream:
        text = stream.read()
    if not text.lstrip().startswith(("{", "[")):
        return None  # TED XML gzip snapshots are intentionally not parsed here.
    return json.loads(text)


def walk(value, counts, totals, meaningful):
    if isinstance(value, dict):
        for key, child in value.items():
            if isinstance(key, str) and SENSITIVE.search(key):
                counts[key] += 1
                if is_nonempty(child):
                    totals[key] += 1
                if is_meaningful(child):
                    meaningful[key] += 1
            walk(child, counts, totals, meaningful)
    elif isinstance(value, list):
        for child in value:
            walk(child, counts, totals, meaningful)


def main():
    print("Aggregate only; no field values are printed. Counts are occurrences across scanned JSON objects, not people.")
    for label, sources in DATASETS.items():
        counts, populated, meaningful = Counter(), Counter(), Counter()
        files = []
        for source in sources:
            path = ROOT / source
            files.extend([path] if path.is_file() else sorted(p for p in path.rglob("*") if p.is_file() and p.suffix in {".json", ".gz"}) if path.is_dir() else [])
        rows = parsed = 0
        for path in files:
            try:
                data = load(path)
                if data is None:
                    continue
                parsed += 1
                rows += len(data) if isinstance(data, list) else 1
                walk(data, counts, populated, meaningful)
            except (OSError, ValueError, EOFError) as exc:
                print(f"WARN {label}: skipped unreadable file ({type(exc).__name__})")
        print(f"\n{label}: {parsed} JSON files scanned; top-level row/object count {rows}")
        for key in sorted(counts, key=str.casefold):
            print(f"  {key}: field occurrences={counts[key]}, nonempty={populated[key]}, meaningful={meaningful[key]}")


if __name__ == "__main__":
    main()
