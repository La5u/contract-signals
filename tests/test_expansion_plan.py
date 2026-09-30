"""Small, offline checks for the metadata-only expansion helper."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('expansion_plan', ROOT / 'tools/expansion-plan.py')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


class ExpansionPlanTests(unittest.TestCase):
    def test_default_is_network_free(self):
        with patch('sys.argv', ['expansion-plan.py']), patch.object(helper.urllib.request, 'build_opener') as network:
            with contextlib.redirect_stdout(io.StringIO()) as output:
                helper.main()
            network.assert_not_called()
        self.assertIn('no network requests', output.getvalue())

    def test_udata_and_ckan_summaries(self):
        dataset = {'title': 'Official data', 'license': 'other-pd', 'organization': {'name': 'Publisher'},
                   'resources': [{'title': 'Example', 'format': 'csv', 'url': 'https://example.org/file.csv'}]}
        result = helper.summary(json.dumps(dataset).encode(), 'application/json', False)
        self.assertEqual(result['datasets'][0]['license'], 'other-pd')
        ckan = helper.summary(json.dumps({'result': {'results': [{'title': 'Aggregate', 'license_id': ''}]}}).encode(), 'application/json', False)
        self.assertEqual(ckan['datasets'][0]['title'], 'Aggregate')
        self.assertEqual(ckan['datasets'][0]['license'], '')
        self.assertNotIn('body', result)

    def test_resource_destinations_are_not_fetched_and_private_urls_are_excluded(self):
        for url in ['http://192.168.1.1/file', 'http://127.0.0.1/file', 'http://[::1]/', 'https://localhost/', 'https://host.local/', 'https://user:pass@example.org/file', 'javascript:alert(1)']:
            self.assertIsNone(helper.public_resource_url(url))
        self.assertEqual(helper.public_resource_url('https://example.org/file'), 'https://example.org/file')

    def test_cached_probe_is_network_free(self):
        plan = json.loads(helper.PLAN.read_text())
        with patch.object(helper, 'REPORT') as report, patch.object(helper.urllib.request, 'build_opener') as opener:
            report.exists.return_value = True
            report.read_text.return_value = json.dumps({'schemaVersion': 1, 'checks': [{'url': s['url']} for s in plan['metadataSources']]})
            with contextlib.redirect_stdout(io.StringIO()) as output:
                helper.probe(plan)
            opener.return_value.open.assert_not_called()
            report.write_text.assert_not_called()
        self.assertIn('no network requests', output.getvalue())

    def test_truncated_metadata_is_not_claimed_parsed(self):
        result = helper.summary(b'{"data":[', 'application/json', True)
        self.assertNotIn('datasets', result)
        self.assertIn('not evidence', result['note'])


if __name__ == '__main__':
    unittest.main()
