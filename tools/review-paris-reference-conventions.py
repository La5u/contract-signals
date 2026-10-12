#!/usr/bin/env python3
"""Offline, read-only inventory. No identifier normalization or linkage promotion.

Print the repository snapshot evidence as JSON; live acquisitions in the companion
ledger are historical assertions and are deliberately not re-fetched here.
"""
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUYER = '21750001600019'


def load(root, name):
    body = (root / name).read_bytes()
    return json.loads(gzip.decompress(body) if name.endswith('.gz') else body)


def pointer(value, path):
    for token in path.strip('/').split('/'):
        token = token.replace('~1', '/').replace('~0', '~')
        value = value[int(token)] if isinstance(value, list) else value[token]
    return value


def scalar_hits(value, references, path=''):
    """Literal scalar equality only, not substring, year/suffix or UID parsing."""
    hits = []
    if isinstance(value, dict):
        for key, child in value.items():
            escaped = key.replace('~', '~0').replace('/', '~1')
            hits.extend(scalar_hits(child, references, path + '/' + escaped))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            hits.extend(scalar_hits(child, references, path + '/' + str(index)))
    elif isinstance(value, str) and value in references:
        hits.append({'pointer': path, 'value': value})
    return hits


def build(root=ROOT):
    files = ['data/decp-feeds-raw.json.gz', 'data/decp-history-raw.json.gz',
             'data/boamp-raw.json.gz', 'research/public-link-observations.json']
    feeds, history, notices, observations = [load(root, name) for name in files]
    pairs = []
    for pair in observations['pairs']:
        raw = pointer(notices, pair['rawNoticePointer'].split('#')[1])
        reference = pointer(json.loads(raw['donnees']), pair['decodedReferencePointer'])
        if reference != pair['publishedReference']:
            raise ValueError('Retained notice reference changed')
        row = {key: pair[key] for key in ['pair', 'boampId', 'decpId',
                                         'rawNoticePointer', 'decodedReferencePointer']}
        row.update(publishedReference=reference, decpContractId=pair['decpContractId'])
        if '21750001600019' in pair['decpId']:
            components = reference.split(' / ')
            row['literalReferenceComponents'] = components
            for label, source in [('feed', feeds), ('ministry', history)]:
                selected = [(i, r) for i, r in enumerate(source['records'])
                            if r.get('acheteur_id') == BUYER]
                row[label + 'ShortIdRows'] = [
                    {'pointer': '/records/' + str(i),
                     'fields': {k: r[k] for k in
                                (['id', 'acheteur_id', 'uid', 'sourceDataset', 'sourceFile']
                                 if label == 'feed' else ['id', 'acheteur_id', 'source'])}}
                    for i, r in selected if r.get('id') == pair['decpContractId']]
                row[label + 'ExactFullReferenceHits'] = [
                    hit for i, r in selected
                    for hit in scalar_hits(r, set(components), '/records/' + str(i))]
            row['linkageSufficient'] = False
            row['basis'] = 'No exact full-reference-to-DECP-ID crosswalk in retained rows; no stripping rule assumed.'
        else:
            row['linkageSufficient'] = False
            row['basis'] = 'Outside Paris convention scope; no new Nantes bridge investigated.'
        pairs.append(row)
    full_references = {component for pair in pairs
                       for component in pair.get('literalReferenceComponents', [])}
    # Separate notice-local sibling, not an automatic reassignment of candidate 2.
    sibling_pointer = observations['pairs'][0]['decodedReferencePointer'].replace(
        '/efac:SettledContract/0/', '/efac:SettledContract/1/')
    sibling_notice = pointer(notices, observations['pairs'][0]['rawNoticePointer'].split('#')[1])
    full_references.add(pointer(json.loads(sibling_notice['donnees']), sibling_pointer))
    return {
        'literalFullReferenceScan': {
            'references': sorted(full_references),
            'scope': 'Every scalar field of every retained row for the exact Paris buyer',
            'hits': {label: [hit for i, row in enumerate(source['records'])
                             if row.get('acheteur_id') == BUYER
                             for hit in scalar_hits(row, full_references, '/records/' + str(i))]
                     for label, source in [('feed', feeds), ('ministry', history)]}},
        'sourceHashes': {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                         for name in files},
        'snapshotTimes': {'feed': feeds['source']['retrieved_at'],
                          'ministry': history['retrievedAt'],
                          'boamp': notices['retrievedAt']},
        'feedProvenance': feeds['source'],
        'ministryQueries': [q for q in history['queries'] if q['buyerSiret'] == BUYER
                            and any(q['offset'] <= int(r['pointer'].split('/')[-1])
                                    < q['offset'] + q['count']
                                    for p in pairs for r in p.get('ministryShortIdRows', []))],
        'pairs': pairs,
        'automaticNormalizationAuthorized': False,
    }


if __name__ == '__main__':
    print(json.dumps(build(), ensure_ascii=False, indent=2))
