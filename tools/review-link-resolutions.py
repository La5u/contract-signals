#!/usr/bin/env python3
"""Apply hash-bound review dispositions to heuristic leads, never contract facts."""
import argparse
from collections import Counter
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROWS = ('data/contracts.json', 'data/decp-history.json', 'data/decp-cities.json')
RAW = 'data/boamp-raw.json.gz'
LINKS = 'data/boamp-decp-links.json'
DECISIONS = 'data/boamp-decp-link-decisions.json'
TED = 'data/paris-ted-version-evidence.json'


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def pointer(value, path):
    if not isinstance(path, str) or not path.startswith('/'):
        raise ValueError('Invalid evidence pointer')
    for token in path[1:].split('/'):
        token = token.replace('~1', '/').replace('~0', '~')
        value = value[int(token)] if isinstance(value, list) else value[token]
    return value


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def build(root=ROOT, decisions=None):
    root = Path(root)
    loaded, hashes = {}, {}
    for name in (*ROWS, RAW, LINKS, DECISIONS, TED):
        blob = (root / name).read_bytes()
        hashes[name] = sha(blob)
        loaded[name] = json.loads(gzip.decompress(blob) if name.endswith('.gz') else blob)
    review = loaded[DECISIONS] if decisions is None else decisions
    if decisions is not None:
        hashes[DECISIONS] = sha(canonical(decisions))
    require(review.get('schemaVersion') == 1, 'Unknown review version')
    require(set(review['inputHashes']) == set((*ROWS, RAW)), 'Unexpected review inputs')
    for name, expected in review['inputHashes'].items():
        require(hashes[name] == expected, 'Stale review source: ' + name)
    artifact = loaded[LINKS]
    require(artifact.get('schemaVersion') == 1, 'Unknown link artifact')
    require({s['path']: s['sha256'] for s in artifact['sources']} ==
            {name: hashes[name] for name in (*ROWS, RAW)}, 'Stale heuristic links')
    indexes = {}
    for name in ROWS:
        for row in loaded[name]:
            require(row['id'] not in indexes, 'Nonunique public row identity')
            indexes[row['id']] = row
    bypair = {(l['boampId'], l['decpId']): l for l in artifact['links']}
    require(len(bypair) == len(artifact['links']), 'Duplicate heuristic pair')
    for link in bypair.values():
        require(link['boampId'] in indexes and link['decpId'] in indexes, 'Missing public endpoint')
        b, d = indexes[link['boampId']], indexes[link['decpId']]
        require(b.get('dataFamily') == 'boamp' and d.get('dataFamily') == 'decp' and
                link['boampUrl'] == b.get('source') and link['decpUrl'] == d.get('source'), 'Link endpoint mismatch')
    retired = {}
    for index, decision in enumerate(review['decisions']):
        key = decision['boampId'], decision['decpId']
        require(key in bypair and key not in retired, 'Missing or duplicate dismissed pair')
        link = bypair[key]
        require(link['status'] == 'candidate', 'Cannot dismiss a confirmed contract link by this protocol')
        require(decision['disposition'] == 'dismissed-notice-lot-candidate' and
                decision.get('replacementLinkConfirmed') is False, 'Unsupported disposition or inferred replacement')
        require(isinstance(decision['reason'], str) and 0 < len(decision['reason']) <= 2000, 'Invalid review reason')
        for idkey, hashkey in [('boampId', 'boampRowSha256'), ('decpId', 'decpRowSha256')]:
            require(sha(canonical(indexes[decision[idkey]])) == decision[hashkey], 'Stale reviewed row')
        require(bool(decision['evidence']), 'Review needs explicit evidence')
        for item in decision['evidence']:
            name = item['source']
            require(name in review['inputHashes'], 'Evidence outside hash-bound public inputs')
            value = loaded[name]
            if 'decode' in item:
                require(name == RAW and item['decode']['format'] == 'json-string', 'Invalid decoded evidence source')
                value = json.loads(pointer(value, item['decode']['path']))
            actual = pointer(value, item['path'])
            require(actual is None or isinstance(actual, (str, int, float, bool)), 'Scalar evidence required')
            require(actual == item['expected'], 'Review evidence changed at ' + item['path'])
        retired[key] = {**link, 'disposition': decision['disposition'], 'reason': decision['reason'],
                        'decisionPointer': '/decisions/' + str(index),
                        'replacementLinkConfirmed': False}
    active = [{**link, 'disposition': 'candidate' if link['status'] == 'candidate' else 'confirmed'}
              for key, link in bypair.items() if key not in retired]
    bc, dc = Counter(l['boampId'] for l in active), Counter(l['decpId'] for l in active)
    for link in active:
        warnings = [w for w in link['warnings'] if not w.startswith('multiple-')]
        if bc[link['boampId']] > 1:
            warnings.append('multiple-decp-matches')
        if dc[link['decpId']] > 1:
            warnings.append('multiple-boamp-matches')
        link['activeWarnings'] = warnings
    spec = importlib.util.spec_from_file_location('review_ted_versions', ROOT / 'tools/investigate-paris-ted.py')
    ted = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ted)
    version_ledger = ted.replay_public(loaded[TED])
    require(version_ledger['source'] == ted.inventory(root / RAW), 'TED evidence binds a different BOAMP source or header')
    notices = []
    for hit in version_ledger['discoveries']:
        if hit['relation'] != 'exact-award-notice-UUID':
            continue
        request = next((r for r in version_ledger['requests'] if r['kind'] == 'xml' and
                        r['publicationNumber'] == hit['publicationNumber']), None)
        notices.append({'boampNoticeId': hit['boampId'], 'publicationNumber': hit['publicationNumber'],
                        'noticeUUID': hit['noticeUUID'], 'procedureUUID': hit['procedureUUID'],
                        'version': hit['expectedBOAMPVersion'],
                        'status': 'verified-notice-version' if hit['tedVersionVerified'] else 'unverified-notice-version',
                        'url': 'https://ted.europa.eu/en/notice/-/detail/' + hit['publicationNumber'],
                        'httpStatus': request.get('httpStatus') if request else None,
                        'decpCrosswalkConfirmed': False})
    require(len(notices) == 5 and len({n['boampNoticeId'] for n in notices}) == 5, 'Nonunique TED notice resolution')
    return {'schemaVersion': 1, 'sourceHashes': hashes, 'reviewer': 'assistant-assisted',
            'scope': 'Candidate-lead dispositions and exact BOAMP/TED notice versions only. No DECP contract identity, amount, offer count or scoring correction.',
            'counts': {'heuristicPairs': len(bypair), 'activePairs': len(active), 'dismissedPairs': len(retired),
                       'confirmedDecpLinks': sum(l['status'] == 'confirmed' for l in active),
                       'ambiguousActivePairs': sum(any(w.startswith('multiple-') for w in l['activeWarnings']) for l in active),
                       'verifiedTedNoticeVersions': sum(n['status'] == 'verified-notice-version' for n in notices),
                       'unverifiedTedNoticeVersions': sum(n['status'] == 'unverified-notice-version' for n in notices)},
            'activePairs': active, 'dismissedPairs': list(retired.values()), 'tedNotices': notices,
            'correctionsLog': 'research/link-corrections-log.md'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'data/public-link-resolutions.json')
    args = parser.parse_args()
    result = build()
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result['counts'], sort_keys=True))


if __name__ == '__main__':
    main()
