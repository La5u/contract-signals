import importlib.util
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'tools' / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


co = load('collect_labels_colombia', 'collect-labels-colombia.py')
ua = load('collect_labels_ukraine', 'collect-labels-ukraine.py')

CONTRACTS = [
    {'id': 'secop2-a-CO1.PCCNTR.1', 'contractId': 'CO1.PCCNTR.1', 'buyerNit': '111', 'buyer': 'B', 'date': '2025-01-01'},
    {'id': 'secop2-a-CO1.PCCNTR.2', 'contractId': 'CO1.PCCNTR.2', 'buyerNit': '111', 'buyer': 'B', 'date': '2025-01-02'},
    {'id': 'secop2-a-CO1.PCCNTR.3', 'contractId': 'CO1.PCCNTR.3', 'buyerNit': '111', 'buyer': 'B', 'date': '2025-01-03'},
]
SANCTIONS = [
    {'id_contrato': 'CO1.PCCNTR.1', 'id_proceso': 'P1', 'tipo_de_sancion': 'Multa', 'estado': 'Publicado', 'tipo': 'x',
     'numero_de_version': '2', 'fecha_evento': '2025-03-04T00:00:00.000', 'valor': '100',
     'nombre_proveedor_objeto_de': 'JUAN PEREZ', 'as_codigo_proveedor_objeto': '12345678'},
    {'id_contrato': 'CO1.PCCNTR.2', 'tipo_de_sancion': 'No Definido', 'fecha_evento': None},
    {'id_contrato': 'co1.pccntr.3', 'tipo_de_sancion': 'Multa'},          # not an exact match
    {'id_contrato': 'No definido', 'tipo_de_sancion': 'Multa'},
    {'id_contrato': 'CO1.PCCNTR.999', 'tipo_de_sancion': 'Clausula Penal'},
]


class ColombiaTests(unittest.TestCase):
    def test_exact_join_and_tristate(self):
        rows, diag, unmatched = co.join_sanctions(CONTRACTS, SANCTIONS)
        lab = {r['contractId']: r['labels']['contractual_sanction'] for r in rows}
        self.assertEqual(lab, {'CO1.PCCNTR.1': True, 'CO1.PCCNTR.2': None, 'CO1.PCCNTR.3': None})
        self.assertNotIn(False, lab.values())     # absence is never "clean"
        self.assertEqual(diag['records_matched_exact'], 2)
        self.assertEqual(unmatched['no_secop2_contract_identifier'], 2)   # 'co1...' lowercase and 'No definido'
        self.assertEqual(unmatched['contract_not_in_cohort'], 1)

    def test_no_personal_data_in_evidence(self):
        rows, _, _ = co.join_sanctions(CONTRACTS, SANCTIONS)
        text = json.dumps(rows)
        self.assertNotIn('JUAN', text)
        self.assertNotIn('12345678', text)

    def test_cohort_nits_and_names_in_soql(self):
        plan = dict(co.request_plan(['111', '222'], ["O'B"]))
        self.assertIn('%27111%27%2C%27222%27', plan['entity-codes'])
        self.assertIn("%27O%27%27B%27", plan['entity-codes'])   # quote doubled

    def test_view_parsing(self):
        v = co.parse_view(json.dumps({'id': 'x', 'name': 'N', 'license': {'name': 'CC'}, 'columns': [{'fieldName': 'a'}]}).encode())
        self.assertEqual((v['license'], v['columns']), ('CC', ['a']))


class FetcherTests(unittest.TestCase):
    def fetcher(self, opener, **kw):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        return co.Fetcher(self.tmp.name, opener=opener, sleep=lambda s: self.sleeps.append(s), min_interval=1.0, **kw)

    def setUp(self):
        self.sleeps = []

    def test_plan_mode_makes_no_request(self):
        calls = []
        f = self.fetcher(lambda u: calls.append(u) or (200, b'[]'), network=False)
        with self.assertRaises(FileNotFoundError):
            f.get('https://example.test/a')
        self.assertEqual(calls, [])

    def test_cache_resume_and_hash(self):
        calls = []
        f = self.fetcher(lambda u: calls.append(u) or (200, b'[1]'), network=True)
        a = f.get('https://example.test/a')
        b = f.get('https://example.test/a')
        self.assertEqual(len(calls), 1)
        self.assertTrue(b['cached'])
        self.assertEqual(a['sha256'], b['sha256'])
        self.assertEqual(len(a['sha256']), 64)

    def test_budget_is_hard(self):
        f = self.fetcher(lambda u: (200, b'[]'), network=True, budget=2)
        f.get('https://example.test/1')
        f.get('https://example.test/2')
        with self.assertRaises(co.BudgetExceeded):
            f.get('https://example.test/3')
        self.assertEqual(f.requests, 2)

    def test_backoff_on_429_then_success_counts_requests(self):
        seq = [429, 200]

        def opener(url):
            if seq.pop(0) == 429:
                raise urllib.error.HTTPError(url, 429, 'slow', {'Retry-After': '7'}, None)
            return 200, b'[]'
        f = self.fetcher(opener, network=True)
        f.get('https://example.test/x')
        self.assertEqual(f.requests, 2)
        self.assertIn(7.0, self.sleeps)

    def test_spacing_between_requests(self):
        f = self.fetcher(lambda u: (200, b'[]'), network=True)
        f.get('https://example.test/1')
        f.get('https://example.test/2')
        self.assertTrue(any(s > 0 for s in self.sleeps))


def monitoring(status, violation=None, types=(), mid='m'):
    m = {'monitoring_id': 'UA-M-1', 'id': mid, 'status': status, 'tender_id': 'T',
         'monitoringPeriod': {'startDate': '2025-01-01T00:00:00+02:00'},
         'dateCreated': '2025-01-01T00:00:00+02:00', 'posts': [{'author': 'Some Person'}],
         'conclusion': {} if violation is None else {'violationOccurred': violation, 'violationType': list(types),
                                                     'datePublished': '2025-02-01T00:00:00+02:00',
                                                     'auditFinding': 'free text about Ivan Ivanov'}}
    return ua.summarise_monitoring(m)


class UkraineTests(unittest.TestCase):
    def test_tristate_labels(self):
        self.assertEqual(ua.label_tender([])['audit_violation'], None)                       # unmonitored
        self.assertEqual(ua.label_tender([monitoring('active')])['audit_violation'], None)   # monitored, no conclusion
        self.assertEqual(ua.label_tender([monitoring('declined')])['audit_violation'], None)
        self.assertIs(ua.label_tender([monitoring('completed', False)])['audit_violation'], False)
        self.assertIs(ua.label_tender([monitoring('addressed', True, ['other'])])['audit_violation'], True)
        both = [monitoring('completed', False), monitoring('addressed', True, ['x'], 'n')]
        self.assertIs(ua.label_tender(both)['audit_violation'], True)

    def test_corruption_category_is_separate(self):
        lab = ua.label_tender([monitoring('addressed', True, ['other'])])
        self.assertIs(lab['audit_violation_corruption_category'], False)
        lab = ua.label_tender([monitoring('addressed', True, ['corruptionAwarded'])])
        self.assertIs(lab['audit_violation_corruption_category'], True)
        self.assertIsNone(ua.label_tender([])['audit_violation_corruption_category'])

    def test_exact_join_rows_and_no_free_text(self):
        contracts = [{'id': 'p-1', 'tenderID': 'UA-1', 'procedureId': 'T', 'tenderCreated': '2025-01-01'},
                     {'id': 'p-2', 'tenderID': 'UA-2', 'procedureId': 'U', 'tenderCreated': '2025-01-01'}]
        rows = ua.build_rows(contracts, {'T': [monitoring('completed', False)]})
        self.assertTrue(rows[0]['monitored'])
        self.assertIs(rows[0]['labels']['audit_violation'], False)
        self.assertFalse(rows[1]['monitored'])
        self.assertIsNone(rows[1]['labels']['audit_violation'])
        text = json.dumps(rows)
        self.assertNotIn('Ivan', text)
        self.assertNotIn('Some Person', text)
        self.assertEqual(rows[0]['dates'], ['2025-01-01', '2025-02-01'])

    def test_plan_mode_is_offline(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / 'c.json'
            data.write_text(json.dumps([{'id': 'p', 'tenderID': 'UA', 'procedureId': 'T', 'tenderCreated': '2025-01-01'}]))
            out = Path(tmp) / 'o.json'
            self.assertEqual(ua.main(['--contracts', str(data), '--cache', str(Path(tmp) / 'c'), '--output', str(out)]), 0)
            self.assertFalse(out.exists())     # plan writes nothing and never touches the network

    def test_feed_url_uses_minimal_fields(self):
        self.assertIn('opt_fields=tender_id%2Cstatus%2CdateCreated', ua.feed_url(0))


class OutputFileTests(unittest.TestCase):
    """The committed-style outputs, when present, keep tri-state and carry no personal data."""

    def test_outputs(self):
        for name in ('colombia', 'ukraine'):
            path = ROOT / 'research/labels' / f'{name}.json'
            if not path.exists():
                continue
            d = json.loads(path.read_text())
            self.assertTrue(d['provenance'] if name == 'colombia' else d['sources']['feed']['pages'])
            text = json.dumps(d['rows'])
            self.assertNotIn('masked-', text)
            self.assertNotIn('nombre_proveedor', text)
            self.assertNotIn('supplier', text)
            for r in d['rows']:
                for v in r['labels'].values():
                    self.assertIn(v, (True, False, None))
            if name == 'colombia':
                self.assertNotIn(False, [r['labels']['contractual_sanction'] for r in d['rows']])


if __name__ == '__main__':
    unittest.main()
