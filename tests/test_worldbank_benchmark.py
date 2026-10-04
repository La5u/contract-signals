import importlib.util
import io
import json
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location('worldbank_benchmark', Path(__file__).resolve().parents[1] / 'tools/worldbank-benchmark.py')
wb = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(wb)


def record(html):
    return {'id': 'OP00104863', 'project_id': 'P168115', 'notice_type': 'Contract Award',
            'noticedate': '11-Nov-2020', 'bid_reference_no': 'REF-1',
            'procurement_method_code': 'CDS', 'procurement_method_name': 'Direct Selection',
            'project_ctry_name': 'Somalia', 'submission_date': '2020-11-11T00:00:00Z',
            'notice_text': html}


# Public layout patterns from the Somalia/Bangladesh notices; synthetic supplier.
SOMALIA = '''<b>Scope of Contract: </b><span>Consulting services</span><br/>
<b>Notice Version No: </b>0<br/>
<b>Contract Signature Date</b><br/>(YYYY/MM/DD)<br/>2020/09/16<br/>
<b>Duration of Contract</b><br/><br/>3.5 Year(s)<br/>
<b>Awarded Firm/Individual:</b><br/><b>SYNTHETIC SUPPLIER (510969)</b><br/>Country: Kenya<br/>
<b>Price: </b><br/><div>Currency: </div><div>Amount: </div>
<div>United States Dollars (United States Dollars)</div><div>500,510.00</div>'''
BANGLADESH = '''<b>Contract Signature Date</b><br/>(YYYY/MM/DD)<br/>2020/05/28<br/>
<b>Duration of Contract</b><br/><br/>20 Day(s)<br/>
<b>Awarded Firm/Individual:</b><br/><b>SYNTHETIC SUPPLIER (498003)</b><br/>
<div>Signed Contract price<br/>BDT 49,650,000.00</div>'''


class BenchmarkTests(unittest.TestCase):
    def test_official_layout_patterns(self):
        row = wb.normalize(record(SOMALIA), wb.API)
        self.assertEqual(row['signing_date'], '2020-09-16')
        self.assertEqual(row['notice_date'], '2020-11-11')
        self.assertEqual(row['signed_contract_price'], {'currency': 'USD', 'amount': '500510.00'})
        self.assertEqual(row['contract_duration'], {'raw_value': '3.5', 'unit': 'Year(s)'})
        self.assertEqual(row['scope'], 'Consulting services')
        self.assertEqual(row['supplier_platform_ids'], ['510969'])
        self.assertNotIn('SYNTHETIC', json.dumps(row))
        self.assertEqual(row['source_country'], 'Somalia')
        self.assertNotIn('jurisdiction', row)
        self.assertEqual(row['labels'], {'corruption': None, 'fraud': None, 'irregularity': None})
        self.assertEqual(row['review_status'], 'unreviewed-comparison-candidate')
        row = wb.normalize(record(BANGLADESH), wb.API)
        self.assertEqual(row['signed_contract_price'], {'currency': 'BDT', 'amount': '49650000.00'})
        self.assertEqual(row['signing_date'], '2020-05-28')
        self.assertEqual(row['supplier_platform_ids'], ['498003'])
        self.assertEqual(row['contract_duration']['unit'], 'Day(s)')

    def test_no_date_fallback_or_coercion(self):
        for html in ('', SOMALIA.replace('2020/09/16', '2020/02/30'), SOMALIA.replace('Contract Signature Date', 'Publication date')):
            row = wb.normalize(record(html), wb.API)
            self.assertIsNone(row['signing_date'])
        r = record('')
        r['noticedate'] = 123
        self.assertIsNone(wb.normalize(r, wb.API)['notice_date'])

    def test_ambiguous_price(self):
        for html in ('Price: <br/>USD 500510', 'Signed Contract price<br/>USD 500510 EUR 123',
                     'Signed Contract price<br/>USD 500510<br/>Signed Contract price<br/>USD 500510',
                     'Signed Contract price<br/>BDT 49,65,000'):
            self.assertIsNone(wb.normalize(record(html), wb.API)['signed_contract_price'])
        self.assertEqual(wb.price('Price:\nCurrency:\nAmount:\nUSD 500510')['amount'], '500510')

    def test_envelopes_and_project_filter(self):
        r = record(SOMALIA)
        self.assertEqual(len(wb.normalize_envelope({'procnotices': {'one': r}}, 'P168115', wb.API)), 1)
        other = dict(r, project_id='P173757', notice_type='Invitation')
        with self.assertRaises(ValueError):
            wb.normalize_envelope({'procnotices': [r, other]}, 'P168115', wb.API)
        self.assertEqual(wb.normalize_envelope({'procnotices': [dict(r, notice_type='Invitation')]}, 'P168115', wb.API), [])

    def test_bounded_fetch_provenance_and_versions(self):
        raw = json.dumps({'procnotices': [record(SOMALIA), dict(record(SOMALIA), id='OP00104864')]}).encode()
        calls = []
        def opener(url, timeout):
            calls.append(url)
            return io.BytesIO(raw)
        pool = wb.fetch_pool(['P168115'], [0], opener=opener)
        self.assertEqual(pool['row_count'], 2)
        self.assertEqual(pool['duplicate_groups'][0]['row_indices'], [0, 1])
        self.assertEqual(pool['responses'][0]['sha256_raw_response'], wb.hashlib.sha256(raw).hexdigest())
        self.assertIn('+00:00', pool['responses'][0]['retrieved_at_utc'])
        self.assertIn('project_id=P168115', calls[0])
        for offsets, maximum in (([1], 5), ([500], 5), ([0, 100], 1), ([0, 0], 5), ([0], 6)):
            with self.assertRaises(ValueError):
                wb.fetch_pool(['P168115'], offsets, maximum, opener)
        self.assertEqual(len(calls), 1)

    def test_review_regressions(self):
        for suffix in ('Contact Information<br/>Email: private@example.org', 'Copyright<br/>2024'):
            r = wb.normalize(record(SOMALIA + '<br/>' + suffix), 'page')
            self.assertEqual(r['signed_contract_price']['currency'], 'USD')
        for value in ('services private@example.org', 'services telephone 123', 'services https://example.org'):
            self.assertIsNone(wb.normalize(record('<b>Scope of Contract:</b>' + value), 'page')['scope'])
        self.assertIsNone(wb.normalize(record(BANGLADESH + '<br/>Contract Signature Date<br/>2020/05/28'), 'page')['signing_date'])
        self.assertIsNone(wb.normalize(record(BANGLADESH.replace('BDT', 'ZZZ')), 'page')['signed_contract_price'])
        r = wb.normalize(record(SOMALIA), 'page')
        self.assertEqual(r['source_url'], wb.API + '?format=json&id=OP00104863')
        self.assertEqual(r['response_url'], 'page')
        self.assertIsNone(r['public_source_url'])

    def test_hidden_markup_not_retained(self):
        self.assertEqual(wb.flatten('<script>secret</script><b>public</b>'), 'public')


if __name__ == '__main__':
    unittest.main()
