"""tools/build-prozorro-documents.py: which document links reach the record panel."""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build_docs', ROOT / 'tools/build-prozorro-documents.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)
DOCS = build.DOCS


class BuildProzorroDocumentsTests(unittest.TestCase):
    def test_latest_version_without_signatures_registers_or_audit_files(self):
        docs = [{'id': 'a', 'title': 'v1.pdf', 'url': DOCS + '1?Signature=x', 'dateModified': '2026-01-01'},
                {'id': 'a', 'title': 'v2.pdf', 'url': DOCS + '2?Signature=y', 'dateModified': '2026-02-01'},
                {'id': 's', 'title': 'sign.p7s', 'url': DOCS + '3', 'format': 'application/pkcs7-signature'},
                {'id': 'r', 'title': 'edr.yaml', 'url': DOCS + '4', 'documentType': 'registerUSR'},
                {'id': 'y', 'title': 'audit_x.yaml', 'url': DOCS + '5'},
                {'id': 'n', 'title': 'no url'}]
        self.assertEqual(build.latest(docs), [['v2.pdf', '2?Signature=y']])

    def test_winner_bid_documents_only_for_the_active_award(self):
        tender = {'documents': [], 'bids': [{'id': 'b1', 'documents': [{'id': 'o', 'title': 'offer.pdf', 'url': DOCS + 'o'}]},
                                            {'id': 'b2', 'documents': [{'id': 'p', 'title': 'other.pdf', 'url': DOCS + 'p'}]}],
                  'awards': [{'id': 'w', 'status': 'active', 'bid_id': 'b1', 'lotID': 'L', 'suppliers': [{'name': 'Winner'}], 'documents': []},
                             {'id': 'r', 'status': 'unsuccessful', 'bid_id': 'b2', 'lotID': 'L', 'suppliers': [{'name': 'Loser'}],
                              'documents': [{'id': 'd', 'title': 'rejection.docx', 'url': DOCS + 'd'}]}]}
        e = build.entry(tender, '2026-10-18')
        self.assertEqual(e['a']['w']['b'], [['offer.pdf', 'o']])
        self.assertNotIn('b', e['a']['r'])
        self.assertEqual((e['a']['r']['n'], e['a']['r']['d']), ('Loser', [['rejection.docx', 'd']]))


if __name__ == '__main__':
    unittest.main()
