#!/usr/bin/env python3
"""Offline checks of already acquired BOAMP PDFs; no download or dataset edits.

Requires pypdf in the private environment. Documents and findings stay private.
This checks notice rendering against retained fields, not source truth or signing.
"""
import argparse
from datetime import date
from decimal import Decimal, InvalidOperation
import gzip
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
CACHE = Path.home() / '.cache/contract-signals/document-review'


def text(value):
    return value.get('#text') if isinstance(value, dict) else value


def many(value):
    return value if isinstance(value, list) else [] if value is None else [value]


def result_section(document, lot):
    """Require exactly one result section, not a general lot description."""
    headings = list(re.finditer(r'6\.1\s+Résultat\s*[–-]\s*Identifiants des lots\s*:\s*(LOT-\d+)', document))
    hits = [(h.end(), headings[i + 1].start() if i + 1 < len(headings) else len(document))
            for i, h in enumerate(headings) if h.group(1) == lot]
    if len(hits) != 1:
        raise ValueError('Missing or ambiguous lot result section')
    start, end = hits[0]
    # Stop before organizations/notice metadata on the final result.
    section = re.split(r'Section\s+[78]\s*[–-]', document[start:end])[0]
    return section


def single(pattern, value):
    hits = re.findall(pattern, value)
    if len(hits) > 1:
        raise ValueError('Ambiguous repeated document field')
    return hits[0].strip() if hits else None


def euro_number(value):
    if value is None:
        return None
    # This BOAMP rendering uses comma thousands, point decimals. Reject other
    # conventions instead of guessing a locale from the expected amount.
    if not re.fullmatch(r'(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?', value):
        raise ValueError('Unsupported monetary number formatting')
    try:
        number = Decimal(value.replace(',', ''))
    except InvalidOperation as exc:
        raise ValueError('Invalid monetary number') from exc
    if not number.is_finite() or number < 0:
        raise ValueError('Unusable monetary number')
    return number


def inspect(document, lot):
    section = result_section(document, lot)
    payable = single(r'Valeur du résultat\s*:\s*([\d,.]+)\s+Euro\b', section)
    ceiling = single(r'Valeur maximale de l’accord-cadre\s*:\s*([\d,.]+)\s+Euro\b', section)
    conclusion = single(r'Date de conclusion du marché\s*:\s*(\d{2}/\d{2}/\d{4})', section)
    if conclusion:
        d, m, y = map(int, conclusion.split('/'))
        conclusion = date(y, m, d).isoformat()
    offers = None
    # Electronic submissions are not total tenders; never use them as offers.
    if re.search(r'Type de soumissions reçues\s*:\s*Offres\s*\n', section):
        count = single(r'Nombre d’offres ou de demandes de participation reçues\s*:\s*(\d+)', section)
        offers = int(count) if count is not None else None
    return {'payable': euro_number(payable), 'framework_ceiling': euro_number(ceiling),
            'conclusion_date': conclusion, 'contract_reference': single(r'Identifiant du marché\s*:\s*([^\n]+)', section),
            'total_offers': offers, 'tax_basis': 'unresolved'}


def references(record, cid):
    notice = json.loads(record['donnees'])['EFORMS']['ContractAwardNotice']
    ext = notice['ext:UBLExtensions']['ext:UBLExtension']['ext:ExtensionContent']['efext:EformsExtension']
    contracts = [c for c in many(ext['efac:NoticeResult'].get('efac:SettledContract')) if text(c.get('cbc:ID')) == cid]
    if len(contracts) != 1:
        raise ValueError('Ambiguous retained contract reference')
    return text(notice['cbc:ID']), str(text(notice['cbc:VersionID'])), text(contracts[0]['efac:ContractReference']['cbc:ID'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review-dir', type=Path, default=CACHE)
    args = parser.parse_args()
    root = args.review_dir.resolve()
    if root == ROOT or ROOT in root.parents:
        parser.error('Evidence and findings must stay outside the repository')
    from pypdf import PdfReader
    plan = json.loads((root / 'plan.json').read_text())
    payload = {k: v for k, v in plan.items() if k != 'planSha256'}
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
    if hashlib.sha256(canonical).hexdigest() != plan['planSha256']:
        raise ValueError('Frozen review plan hash mismatch')
    for row in plan['rows']:
        snapshot = row['sourceSnapshot']
        if hashlib.sha256((ROOT / snapshot['path']).read_bytes()).hexdigest() != snapshot['sha256']:
            raise ValueError('Published snapshot differs from the frozen plan')
    raw_path = ROOT / 'data/boamp-raw.json.gz'
    raw_sha256 = hashlib.sha256(raw_path.read_bytes()).hexdigest()
    with gzip.open(raw_path, 'rt') as stream:
        raw = json.load(stream)
    manifest = json.loads((root / 'boamp-review/manifest.json').read_text())
    results = []
    for row in plan['rows']:
        if row['dataset'] != 'boamp':
            continue
        ids = row['matchingIds']
        nid = ids['noticeId']
        item = {'rowId': row['rowId'], 'stratum': row['stratum'], 'status': 'document_not_acquired', 'reviewer': 'assistant; not independent expert'}
        path = root / 'boamp-review' / (nid + '-official.pdf')
        if not path.exists():
            results.append(item)
            continue
        body = path.read_bytes()
        evidence = [e for e in manifest['requests'] if e['file'] == path.name and e.get('status') == 200]
        if len(evidence) != 1 or hashlib.sha256(body).hexdigest() != evidence[0]['sha256']:
            raise ValueError('Missing or hash-mismatched PDF acquisition evidence')
        candidates = [r for r in raw['records'] if r['idweb'] == nid]
        if len(candidates) != 1:
            raise ValueError('Ambiguous retained notice')
        uuid, version, reference = references(candidates[0], ids['contractId'])
        reader = PdfReader(path)
        pages = [p.extract_text() or '' for p in reader.pages]
        document = '\n'.join(pages)
        if f'Annonce n° {nid}' not in document or ids['contractFolderId'] not in document:
            raise ValueError('Notice/procedure mismatch')
        if not re.search(re.escape(uuid) + r'\s*-\s*' + re.escape(version) + r'\b', document):
            raise ValueError('Notice UUID/version mismatch')
        fields = inspect(document, ids['lotId'])
        if fields['contract_reference'] != reference:
            raise ValueError('Contract reference mismatch')
        amount = row['published']['amount']
        expected = Decimal(str(amount)) if amount is not None else None
        item.update(status='limited_notice_corroboration', evidence={k: evidence[0][k] for k in ['url', 'utc', 'sha256', 'bytes']},
                    noticeVersion=version, exactIdentityMatched=True,
                    pdfPages=[i + 1 for i, page in enumerate(pages) if ids['lotId'] in page],
                    fields=fields, payableMatchesPublished=fields['payable'] == expected,
                    conclusionMatchesPublished=fields['conclusion_date'] == row['published']['date'],
                    limits=['PDF renders the same notice, not independent underlying contract truth',
                            'Tax basis unresolved; no signature authenticity or payment verification'])
        results.append(item)
    out = root / 'boamp-document-results.json'
    out.write_text(json.dumps({'planSha256': plan['planSha256'], 'retainedRawSha256': raw_sha256, 'results': results}, default=str, indent=2) + '\n')
    out.chmod(0o600)
    print(json.dumps({'reviewed': sum(r['status'] == 'limited_notice_corroboration' for r in results),
                      'not_acquired': sum(r['status'] == 'document_not_acquired' for r in results),
                      'disagreements': sum(r.get('payableMatchesPublished') is False or r.get('conclusionMatchesPublished') is False for r in results)}))


if __name__ == '__main__':
    main()
