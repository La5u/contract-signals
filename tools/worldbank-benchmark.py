#!/usr/bin/env python3
"""Local, unreviewed World Bank comparison candidates; no website integration."""
import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

API = 'https://search.worldbank.org/api/v2/procnotices'
SUPPORTED_CURRENCIES = frozenset(('USD', 'BDT', 'EUR', 'GBP', 'JPY', 'CNY', 'INR', 'KES', 'CHF', 'CAD', 'AUD', 'NZD', 'ZAR', 'NGN', 'PKR', 'LKR', 'NPR', 'UGX', 'TZS', 'RWF', 'ETB', 'GHS', 'XOF', 'XAF'))
CONTACT = r'Contact(?:\s+Information|\s+Details|\s+Person)?|Address|Telephone|Phone|Fax|E-?mail|Website|Disclaimer|Copyright' 


class PublicText(HTMLParser):
    """Flatten public markup as text, never executable HTML."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.hidden += 1
        if tag in ('br', 'div', 'p', 'tr', 'td', 'h4'):
            self.parts.append('\n')

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.hidden = max(0, self.hidden - 1)
        if tag in ('div', 'p', 'tr', 'td', 'h4'):
            self.parts.append('\n')

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def flatten(value):
    parser = PublicText()
    parser.feed(value if isinstance(value, str) else '')
    return '\n'.join(s.strip() for s in ''.join(parser.parts).splitlines() if s.strip())


def field(record, key):
    value = record.get(key)
    return value.strip() if isinstance(value, str) and value.strip() else None


def date(value, pattern):
    syntax = r'\d{2}-[A-Za-z]{3}-\d{4}' if pattern == '%d-%b-%Y' else r'\d{4}/\d{2}/\d{2}'
    if not isinstance(value, str) or not re.fullmatch(syntax, value):
        return None
    try:
        return datetime.strptime(value, pattern).date().isoformat()
    except (ValueError, TypeError):
        return None


def section(text, heading):
    # Stop at known headings, so absence of a value cannot borrow another field.
    headings = r'Contract\s*Signature\s*Date|Duration of Contract|Awarded Firm/Individual|Signed\s*Contract\s*price|Price|Scope of Contract|Notice Version No|' + CONTACT
    match = re.search(r'(?im)^\s*' + heading + r'\s*:?\s*', text)
    if not match:
        return None
    rest = text[match.end():]
    end = re.search(r'(?im)^\s*(?:' + headings + r')\s*:?\s*', rest)
    return rest[:end.start()] if end else rest


def price(text):
    signed = section(text, r'Signed\s*Contract\s*price')
    table = section(text, r'Price')
    if len(re.findall(r'(?im)^\s*(?:Signed\s*Contract\s*price|Price)\s*:?(?=\s|$)', text)) > 1:
        return None
    if signed is not None and table is not None:
        return None
    content = signed if signed is not None else table
    if content is None:
        return None
    content = content.replace('United States Dollars (United States Dollars)', 'USD')
    if signed is None:
        if not re.search(r'Currency\s*:\s*\n?Amount\s*:', content, re.I):
            return None
        content = re.sub(r'Currency\s*:\s*\n?Amount\s*:', '', content, flags=re.I)
    matches = re.findall(r'\b([A-Z]{3})\s*([0-9][0-9,]*(?:\.[0-9]+)?)\b', content)
    # Multiple numeric amounts (even equal amounts) are not a single known price.
    numbers = re.findall(r'\b[0-9][0-9,]*(?:\.[0-9]+)?\b', content)
    if len(matches) != 1 or len(numbers) != 1:
        return None
    currency, amount = matches[0]
    if currency not in SUPPORTED_CURRENCIES:
        return None
    if ',' in amount and not re.fullmatch(r'\d{1,3}(?:,\d{3})+(?:\.\d+)?', amount):
        return None
    try:
        return {'currency': currency, 'amount': str(Decimal(amount.replace(',', '')))}
    except InvalidOperation:
        return None


def normalize(record, url):
    text = flatten(record.get('notice_text'))
    signature = section(text, r'Contract\s*Signature\s*Date')
    dates = re.findall(r'\b\d{4}/\d{2}/\d{2}\b', signature or '')
    signing = date(dates[0], '%Y/%m/%d') if len(dates) == 1 and len(re.findall(r'(?im)^\s*Contract\s*Signature\s*Date\s*:?(?=\s|$)', text)) == 1 else None
    duration = section(text, r'Duration of Contract')
    duration_match = re.fullmatch(r'\s*(\d+(?:\.\d+)?)\s+(Day\(s\)|Month\(s\)|Year\(s\)|Days?|Months?|Years?|Weeks?|Week\(s\))\s*', duration or '', re.I)
    scope = section(text, r'Scope of Contract')
    if scope and (re.search(r'(?i)\b(?:' + CONTACT + r')\b|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|https?://|www\.', scope)):
        scope = None
    suppliers = section(text, r'Awarded Firm/Individual')
    ids = sorted(set(re.findall(r'\((\d+)\)', suppliers or '')))
    row = {key: field(record, key) for key in ('id', 'project_id', 'bid_reference_no', 'procurement_group')}
    row.update(method_code=field(record, 'procurement_method_code'),
               method_name=field(record, 'procurement_method_name'),
               notice_date=date(field(record, 'noticedate'), '%d-%b-%Y'),
               signing_date=signing, scope=scope.strip() if scope else None,
               source_country=field(record, 'project_ctry_name'),
               source_url=API + '?' + urlencode({'format': 'json', 'id': row['id']}) if row['id'] else None,
               response_url=url, public_source_url=None,
               supplier_platform_ids=ids,
               contract_duration={'raw_value': duration_match[1], 'unit': duration_match[2]} if duration_match else None,
               signed_contract_price=price(text),
               labels={'corruption': None, 'fraud': None, 'irregularity': None},
               review_status='unreviewed-comparison-candidate')
    row['evidence_availability'] = {key: row[key] is not None for key in ('method_code', 'signing_date', 'source_url', 'signed_contract_price', 'contract_duration')}
    row['validation_flags'] = [key + '-missing-or-malformed' for key in ('id', 'bid_reference_no', 'notice_date', 'signing_date') if row[key] is None]
    if row['signed_contract_price'] is None:
        row['validation_flags'].append('price-missing-malformed-or-unsupported-currency')
    row['duplicate_group_key'] = [row['project_id'], row['bid_reference_no'], signing]
    return row


def normalize_envelope(payload, project, url):
    if not isinstance(payload, dict) or 'procnotices' not in payload:
        raise ValueError('Missing procnotices envelope')
    records = payload['procnotices']
    if isinstance(records, dict):
        records = list(records.values())
    if not isinstance(records, list):
        raise ValueError('Invalid procnotices envelope')
    for record in records:
        if not isinstance(record, dict) or record.get('project_id') != project:
            raise ValueError('Returned project_id does not match query')
    return [normalize(r, url) for r in records if re.sub(r'\s+', '', field(r, 'notice_type') or '').lower() == 'contractaward']


def fetch_pool(projects, offsets, max_pages=5, opener=urlopen):
    if not 1 <= max_pages <= 5 or not offsets or len(offsets) > max_pages:
        raise ValueError('Use 1–5 pages per project, within max-pages')
    if any(type(o) is not int or o < 0 or o > 400 or o % 100 for o in offsets) or len(set(offsets)) != len(offsets):
        raise ValueError('Offsets must be distinct members of 0,100,200,300,400')
    rows, responses = [], []
    for project in dict.fromkeys(projects):
        if not re.fullmatch(r'P\d{6}', project):
            raise ValueError('Invalid project ID')
        for offset in offsets:
            url = API + '?' + urlencode({'format': 'json', 'project_id': project, 'rows': 100, 'os': offset})
            with opener(url, timeout=30) as response:
                raw = response.read(10_000_001)
            if len(raw) > 10_000_000:
                raise ValueError('Response exceeds size limit')
            retrieved = datetime.now(timezone.utc).isoformat()
            rows.extend(normalize_envelope(json.loads(raw), project, url))
            responses.append({'url': url, 'retrieved_at_utc': retrieved, 'sha256_raw_response': hashlib.sha256(raw).hexdigest()})
    groups = {}
    for index, row in enumerate(rows):
        key = tuple(row['duplicate_group_key'])
        # Unknown references/dates are not asserted to be the same contract.
        if all(key):
            groups.setdefault(key, []).append(index)
    return {'description': 'Unreviewed comparison candidates; row count is not a certified unique contract-event count. Source country is not a jurisdiction or outcome.',
            'row_count': len(rows), 'rows': rows, 'responses': responses,
            'duplicate_groups': [{'key': list(k), 'row_indices': v} for k, v in groups.items() if len(v) > 1]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fetch', action='store_true', help='Explicitly enable official API network requests')
    parser.add_argument('--project', action='append', required=True)
    parser.add_argument('--offset', type=int, action='append', help='Permitted: 0,100,200,300,400; default: 0')
    parser.add_argument('--max-pages', type=int, default=5)
    parser.add_argument('--output', type=Path, default=Path('/tmp/worldbank-comparison-pool.json'))
    args = parser.parse_args()
    if not args.fetch:
        parser.error('Network access requires --fetch')
    try:
        pool = fetch_pool(args.project, args.offset or [0], args.max_pages)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    args.output.write_text(json.dumps(pool, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
