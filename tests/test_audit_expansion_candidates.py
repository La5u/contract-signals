"""Synthetic tests for conservative cross-source candidate matching and audit evidence."""
from collections import Counter
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('candidate_audit', ROOT / 'tools/audit-expansion-candidates.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

XML = b'''<r xmlns:e="urn:test"><e:NoticeResult>
<e:LotResult><e:SettledContract><e:ID>CON-0001</e:ID></e:SettledContract></e:LotResult>
<e:SettledContract><e:ID>CON-0001</e:ID><e:IssueDate>2025-02-03+02:00</e:IssueDate>
<e:ContractReference><e:ID> 001.A </e:ID></e:ContractReference></e:SettledContract>
</e:NoticeResult></r>'''


class AuditTests(unittest.TestCase):
    def test_preserve_identifier_scope(self):
        self.assertEqual(audit.normalized_ref('  a  B '), 'A B')
        self.assertNotEqual(audit.normalized_ref('001.A'), audit.normalized_ref('1A'))
        self.assertNotEqual(audit.normalized_ref('A.1'), audit.normalized_ref('A1'))

    def test_native_reference_not_local_id(self):
        self.assertEqual(audit.native_contracts(XML), {'CON-0001': ('001.A', '2025-02-03')})

    def test_conflicting_native_ids_fail_closed(self):
        duplicate = XML.replace(b'</e:NoticeResult>', b'<e:SettledContract><e:ID>CON-0001</e:ID><e:IssueDate>2025-02-03</e:IssueDate><e:ContractReference><e:ID>other</e:ID></e:ContractReference></e:SettledContract></e:NoticeResult>')
        with self.assertRaisesRegex(ValueError, 'Conflicting'):
            audit.native_contracts(duplicate)

    def test_duplicate_keys_count_not_deduplicate(self):
        rows = [{'buyerId': 'buyer', 'contractId': '001.A', 'date': '2025-02-03'}] * 2
        self.assertEqual(audit.seap_keys(rows), Counter({('buyer', '001.A', '2025-02-03'): 2}))

    def test_match_requires_buyer_reference_date_and_remains_candidate(self):
        rows = [dict(buyerId='buyer', contractId='001.A', date='2025-02-03'),
                dict(buyerId='other', contractId='001.A', date='2025-02-03'),
                dict(buyerId='buyer', contractId='001.A', date='2025-02-04'),
                dict(buyerId='buyer', contractId='1A', date='2025-02-03')]
        ted = [dict(id='ted-row', noticeId='1-2025', buyerId='buyer', contractId='CON-0001')]
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / '1-2025.xml.gz').write_bytes(gzip.compress(XML))
            result = audit.ted_overlap(rows, ted, Path(directory))
        self.assertEqual(result['seapRowsWithBuyerReferenceDateCandidate'], 1)
        self.assertEqual(result['tedRowsWithBuyerReferenceDateCandidate'], 1)
        self.assertIsNone(result['confirmedContractLinks'])
        self.assertTrue(result['nonMatchesAreNotProvenAdditionalContracts'])

    def test_missing_xml_not_silently_skipped(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                audit.ted_overlap([], [dict(noticeId='1-2025')], Path(directory))

    def test_published_aggregate_report_scope(self):
        report = json.loads((ROOT / 'data/expansion-candidate-audit.json').read_bytes())
        self.assertEqual(report['networkRequests'], 0)
        self.assertEqual(report['ukraine']['candidateSha256'], hashlib.sha256((ROOT / 'data/prozorro-expansion/contracts.json').read_bytes()).hexdigest())
        manifest = json.loads((ROOT / 'data/romania-seap-candidate-manifest.json').read_bytes())
        self.assertEqual(report['romania']['candidateSha256'], manifest['candidate']['sha256'])
        self.assertEqual(report['romania']['tedSnapshotSha256'], hashlib.sha256((ROOT / 'data/ted-romania.json').read_bytes()).hexdigest())
        self.assertTrue(all(report['ukraine']['replayByteIdentical'].values()))
        self.assertEqual(report['ukraine']['overlapWithPilot'], {'id': 0, 'procedureId': 0, 'contractInternalId': 0, 'buyerId': 0})
        self.assertIsNone(report['romania']['overlap']['confirmedContractLinks'])
        self.assertFalse(report['romania']['privacyCleared'])
        for key in ('ukraine', 'romania'):
            self.assertTrue(report[key]['recommendation'].startswith('Do not register'))


if __name__ == '__main__':
    unittest.main()
