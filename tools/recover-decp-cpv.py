#!/usr/bin/env python3
"""Conservative CPV candidates only; never rewrite datasets or calculate check digits."""
import argparse
from collections import Counter, defaultdict
import gzip
import json
from pathlib import Path
import re
import subprocess
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import sha  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CACHE = Path.home() / '.cache/contract-signals/decp-cpv'
URL = 'https://ted.europa.eu/documents/d/ted/cpv_2008_xml'
DATASETS = ('data/decp-cities.json', 'data/decp-history.json')
RETAINED = ('data/decp-cities-raw.json', 'data/decp-history-raw.json.gz',
            'data/decp-feeds-raw.json.gz', 'data/city-portals-raw.json.gz')
FULL = re.compile(r'[0-9]{8}-[0-9]\Z')
SHORT = re.compile(r'[0-9]{8}\Z')
LIMIT = 40 * 1024 * 1024


def row_hash(row):
    return sha(json.dumps(row, sort_keys=True, ensure_ascii=False,
                          separators=(',', ':'), allow_nan=False).encode())


def private_cache(path):
    path = Path(path).expanduser().absolute()
    if path.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError('Vocabulary cache must be outside the repository')
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('Symlinked cache paths are forbidden')
    return path


def fetch(cache):
    cache = private_cache(cache)
    cache.mkdir(parents=True, exist_ok=True, mode=0o700)
    cache.chmod(0o700)
    with urllib.request.urlopen(urllib.request.Request(
            URL, headers={'User-Agent': 'ContractSignals bounded CPV review'}), timeout=60) as r:
        blob = r.read(LIMIT + 1)
    if len(blob) > LIMIT:
        raise ValueError('Vocabulary download exceeds bound')
    # Validate before storing. The official archive uses Deflate64; system unzip supports it.
    path = cache / 'cpv_2008_xml.zip'
    if path.is_symlink():
        raise ValueError('Symlinked archive forbidden')
    path.write_bytes(blob)
    path.chmod(0o600)
    vocabulary(path)


def parse_vocabulary(blob):
    if b'<!DOCTYPE' in blob or b'<!ENTITY' in blob:
        raise ValueError('External declarations forbidden')
    root = ET.fromstring(blob)
    if root.tag != 'CPV_CODE':
        raise ValueError('Not the main CPV vocabulary')
    codes = [node.attrib.get('CODE', '') for node in root.findall('CPV')]
    if not codes or any(not FULL.fullmatch(c) for c in codes):
        raise ValueError('Vocabulary must contain exact full CPV codes')
    return sorted(set(codes))


def vocabulary(path):
    path = Path(path)
    with zipfile.ZipFile(path) as z:
        info = z.getinfo('cpv_2008.xml')
        if info.file_size > LIMIT:
            raise ValueError('Expanded vocabulary exceeds bound')
    proc = subprocess.run(['unzip', '-p', str(path), 'cpv_2008.xml'],
                          capture_output=True, check=True, timeout=60)
    if len(proc.stdout) > LIMIT:
        raise ValueError('Expanded vocabulary exceeds bound')
    return parse_vocabulary(proc.stdout), sha(proc.stdout)


def resolve(prefix, evidence, official=None):
    """Every observed full code must agree; absence is not a checksum inference."""
    codes = set(evidence.get(prefix, {}))
    if official is not None:
        published = {c for c in official if c[:8] == prefix}
        if not published:
            return None, 'nonexistent-in-vocabulary'
        codes |= published
    if not codes:
        return None, 'no-full-code-evidence'
    if len(codes) != 1:
        return None, 'ambiguous-full-codes'
    code = next(iter(codes))
    if prefix.startswith('000'):
        return None, 'placeholder-prefix'
    return code, 'safe-exact-prefix'


def build(root=ROOT, archive=None):
    root = Path(root)
    evidence = defaultdict(lambda: defaultdict(list))
    sources = []
    for rel in RETAINED:
        blob = (root / rel).read_bytes()
        payload = json.loads(gzip.decompress(blob) if rel.endswith('.gz') else blob)
        sources.append({'path': rel, 'sha256': sha(blob)})
        for n, row in enumerate(payload['records']):
            code = row.get('codecpv', row.get('codeCPV'))
            if isinstance(code, str) and FULL.fullmatch(code):
                evidence[code[:8]][code].append({'source': rel, 'rowIndex': n})
    official = None
    if archive is not None:
        official, xml_sha = vocabulary(archive)
        sources.append({'source': URL, 'sha256': sha(Path(archive).read_bytes()),
                        'member': 'cpv_2008.xml', 'memberSha256': xml_sha,
                        'fullCodes': len(official)})
        for code in official:
            evidence[code[:8]][code].append({'source': URL, 'member': 'cpv_2008.xml',
                                            'selector': f'CPV[@CODE="{code}"]'})
    candidates, validation = [], Counter()
    for rel in DATASETS:
        blob = (root / rel).read_bytes()
        sources.append({'path': rel, 'sha256': sha(blob)})
        for n, row in enumerate(json.loads(blob)):
            code = row.get('cpv')
            if not isinstance(code, str):
                validation['missing-or-nonstring'] += 1
                continue
            if SHORT.fullmatch(code):
                proposed, status = resolve(code, evidence, official)
                candidates.append({'dataset': rel, 'rowIndex': n, 'rowSha256': row_hash(row),
                                   'oldCpv': code, 'candidateCpv': proposed, 'status': status})
            elif FULL.fullmatch(code):
                validation['full-in-vocabulary' if official is not None and code in official
                           else 'full-not-in-vocabulary' if official is not None
                           else 'full-unvalidated'] += 1
            else:
                validation['malformed'] += 1
    prefixes = sorted({c['oldCpv'] for c in candidates})
    mappings = []
    for prefix in prefixes:
        code, status = resolve(prefix, evidence, official)
        mappings.append({'prefix': prefix, 'candidateCpv': code, 'status': status,
                         'observedFullCodes': dict(sorted(evidence.get(prefix, {}).items()))})
    support = Counter()
    for candidate in candidates:
        if candidate['candidateCpv']:
            refs = evidence[candidate['oldCpv']][candidate['candidateCpv']]
            support['retained-full-code-supported' if any(r['source'] in RETAINED for r in refs)
                    else 'official-vocabulary-only'] += 1
    return {'schemaVersion': 'decp-cpv-review-v1', 'officialVocabularyUsed': official is not None,
            'safeCandidateSupport': dict(sorted(support.items())),
            'targetCountsByDataset': dict(sorted(Counter(c['dataset'] for c in candidates).items())),
            'counts': dict(sorted(Counter(c['status'] for c in candidates).items())),
            'existingCodeValidation': dict(sorted(validation.items())), 'sources': sources,
            'prefixMappings': mappings, 'candidates': candidates}


def render(report):
    counts = report['counts']
    lines = ['# DECP CPV check-digit review', '',
             'Candidate-only review. No dataset, common helper, score or source field was changed.', '',
             '## Findings', '',
             f"Eight-digit targets: {sum(counts.values())}; safe candidates: {counts.get('safe-exact-prefix', 0)}.",
             f"Statuses: `{json.dumps(counts, sort_keys=True)}`.",
             f"Distinct exact prefixes: {len(report['prefixMappings'])}.",
             f"Targets by cohort: `{json.dumps(report['targetCountsByDataset'], sort_keys=True)}`.",
             f"Safe candidate support: `{json.dumps(report['safeCandidateSupport'], sort_keys=True)}`.",
             f"Existing codes: `{json.dumps(report['existingCodeValidation'], sort_keys=True)}`.", '',
             'The requested ~128 is not the current snapshot count: both normalized cohorts are scanned, '
             'including feed and portal rows. No arbitrary cutoff is used.', '',
             '## Method and sources', '',
             '`tools/decp_feeds.py:cpv_lookup` already maps a prefix only when all retained '
             'full-code observations agree, including initial alternatives. It is cohort-local; '
             'this tool instead inspects the four retained raw extracts and optionally the official '
             'main CPV 2008 vocabulary. Feed/portal extracts currently supply eight-digit codes, '
             'not check digits. Full-code syntax alone is not vocabulary validation.', '',
             'The official download is linked from https://ted.europa.eu/en/simap/cpv. '
             'Only `cpv_2008.xml` (main vocabulary) is read, never supplementary codes. '
             'Raw archive stays in a private external cache. No checksum algorithm, fuzzy match, '
             'description inference, nearest prefix, or truncation is used. All full-code evidence '
             'must agree exactly; ambiguous prefixes and prefixes absent from an available official '
             'vocabulary remain unresolved. Without the vocabulary, absence remains unknown rather '
             'than being labelled nonexistent.', '',
             '## Reproduce and integrate', '',
             '```sh', 'python tools/recover-decp-cpv.py --fetch --official --output research/decp-cpv-review.md',
             'python tools/recover-decp-cpv.py --official --output /tmp/decp-cpv-candidates.json --format json',
             'python -m unittest discover -s tests -p test_recover_decp_cpv.py', '```', '',
             'Offline runs omit `--fetch`; omit `--official` for retained-only review. '
             'The JSON below is the deterministic public-safe candidate artifact. It exports only '
             'CPV codes, relative source paths, row indices and hashes, never descriptions, names, '
             'supplier identifiers, feed UIDs or contract IDs. Indices are zero-based. Source hashes '
             'cover stored bytes (including gzip); row hashes cover canonical sorted-key UTF-8 JSON.', '',
             'Integration requires a separately reviewed change: verify dataset/source hashes and '
             'the row hash plus exact old CPV, then apply only `safe-exact-prefix` candidates. '
             'Preserve provenance and all conflicts; do not rewrite initial alternatives or raw '
             'evidence. Prefer passing a reviewed unique mapping to `feed_fields` when rebuilding '
             'feed/portal cohorts. Rebuild dependent context/coverage and run regression tests: '
             'adding digits can make rows eligible for CPV-based contexts. This tool never applies '
             'changes; existing invalid full codes are counted, not repaired.', '',
             '## Exact mappings, provenance and row candidates', '', '```json',
             json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), '```', '']
    return '\n'.join(lines)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fetch', action='store_true')
    p.add_argument('--official', action='store_true')
    p.add_argument('--cache', type=Path, default=CACHE)
    p.add_argument('--output', type=Path)
    p.add_argument('--format', choices=('json', 'markdown'), default='markdown')
    args = p.parse_args()
    cache = private_cache(args.cache)
    if args.fetch:
        fetch(cache)
    report = build(archive=cache / 'cpv_2008_xml.zip' if args.official else None)
    text = (json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + '\n'
            if args.format == 'json' else render(report))
    if args.output:
        args.output.write_text(text)
    else:
        print(text, end='')


if __name__ == '__main__':
    main()
