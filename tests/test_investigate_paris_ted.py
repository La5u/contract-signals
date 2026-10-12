"""Synthetic parser/privacy/bounds tests and offline public-ledger replay."""
import gzip
import importlib.util
import json
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('paris_ted', ROOT / 'tools/investigate-paris-ted.py')
ted = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ted)


class ParisTEDTests(unittest.TestCase):
    def source(self):
        return {'notices': [{'boampId': rid, 'noticeUUID': f'12345678-1234-1234-1234-{i:012d}',
                             'procedureUUID': f'87654321-1234-1234-1234-{i:012d}', 'version': '01'}
                            for i, rid in enumerate(ted.TARGETS)]}

    def test_plan_executes_exact_queries_not_ft_or_syntax_only(self):
        requests = ted.plan(self.source())
        self.assertEqual(len(requests), 1)
        b = requests[0]['requestBody']
        self.assertFalse(b['checkQuerySyntax'])
        self.assertFalse(b['onlyLatestVersions'])
        self.assertEqual(b['scope'], 'ALL')
        self.assertNotIn('FT', b['query'])
        for n in self.source()['notices']:
            self.assertIn('notice-identifier="' + n['noticeUUID'] + '"', b['query'])
            self.assertIn('procedure-identifier="' + n['procedureUUID'] + '"', b['query'])

    def test_search_minimizes_contacts_links_and_titles(self):
        raw = json.dumps({'notices': [{'publication-number': '123456-2025',
            'notice-title': 'PRIVATE PERSON', 'contacts': 'private@example.invalid',
            'links': {'xml': 'https://evil.invalid'}, 'notice-identifier': 'x'}],
            'totalNoticeCount': 1, 'timedOut': False}).encode()
        e = ted.search_evidence(raw)
        self.assertEqual(e['noticeCount'], 1)
        self.assertNotIn('PRIVATE', json.dumps(e))
        self.assertNotIn('evil', json.dumps(e))
        self.assertNotIn('email', json.dumps(e))

    def test_xml_uuid_procedure_and_version_all_required(self):
        n = self.source()['notices'][0]
        xml = f'''<ContractAwardNotice xmlns="urn:award" xmlns:c="urn:cbc" xmlns:e="urn:ext">
          <c:ID schemeName="notice-id">{n['noticeUUID']}</c:ID>
          <c:VersionID>01</c:VersionID><c:ContractFolderID>{n['procedureUUID']}</c:ContractFolderID>
          <e:Contact><c:Name>PRIVATE NAME</c:Name><c:ID>PRIVATE ID</c:ID></e:Contact>
          <e:SettledContract><c:ID>CON-0001</c:ID><c:IssueDate>2025-02-14</c:IssueDate>
          <e:Contact><c:ID>PRIVATE NESTED ID</c:ID></e:Contact>
          <e:ContractReference><c:ID>2025S015900000 / 2025HA0001GR</c:ID></e:ContractReference>
          <e:NoticeDocumentReference><c:ID>723965-2024</c:ID></e:NoticeDocumentReference></e:SettledContract>
        </ContractAwardNotice>'''.encode()
        e = ted.xml_evidence(xml, n)
        self.assertTrue(e['exactAwardVersion'])
        self.assertFalse(e['exactCrosswalkForReview'])
        self.assertNotIn('PRIVATE', json.dumps(e))
        self.assertIn('2025S015900000 / 2025HA0001GR', json.dumps(e))
        self.assertFalse(ted.xml_evidence(xml.replace(b'>01<', b'>02<'), n)['exactAwardVersion'])
        duplicate = xml.replace(b'<c:VersionID>01</c:VersionID>', b'<c:VersionID>01</c:VersionID><c:VersionID>01</c:VersionID>')
        self.assertFalse(ted.xml_evidence(duplicate, n)['exactAwardVersion'])
        self.assertFalse(ted.xml_evidence(xml.replace(n['procedureUUID'].encode(), b'wrong'), n)['exactAwardVersion'])
        self.assertFalse(ted.xml_evidence(xml.replace(b'ContractAwardNotice', b'ContractNotice'), n)['exactAwardVersion'])
        with self.assertRaises(ValueError):
            ted.xml_evidence(b'<!DOCTYPE x><x/>', n)

    def test_synthetic_inventory_preserves_reference_format_and_citations(self):
        rows = []
        for n in self.source()['notices']:
            notice = {'cbc:ID': {'#text': n['noticeUUID']}, 'cbc:VersionID': '01',
                      'cbc:ContractFolderID': n['procedureUUID'], 'cbc:IssueDate': '2025-02-24',
                      'ext:result': {'efac:SettledContract': {
                          'cbc:ID': {'#text': 'CON-0001'},
                          'efac:ContractReference': {'cbc:ID': '20242024S05075'},
                          'cac:NoticeDocumentReference': {'cbc:ID': '723965-2024'}}},
                      'cac:Contact': {'cbc:Name': 'PRIVATE'}}
            rows.append({'idweb': n['boampId'], 'dateparution': '2025-02-26',
                         'gestion': json.dumps({'REFERENCE': {'ANNONCE_ANTERIEUR': {'IDWEB': '24-1'}}}),
                         'donnees': json.dumps({'EFORMS': {'ContractAwardNotice': notice}})})
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'raw.gz'
            p.write_bytes(gzip.compress(json.dumps({'records': rows}).encode()))
            s = ted.inventory(p)
        self.assertNotIn('PRIVATE', json.dumps(s))
        self.assertIn('CON-0001', json.dumps(s))
        self.assertIn('20242024S05075', json.dumps(s))
        self.assertTrue(all(n['publishedAwardTEDNumber'] is None for n in s['notices']))

    def test_fetch_budget_exclusive_private_and_no_arbitrary_xml_link(self):
        n = self.source()['notices'][0]
        raw = json.dumps({'notices': [{'publication-number': '126421-2025',
                         'notice-identifier': n['noticeUUID'], 'procedure-identifier': n['procedureUUID'],
                         'links': {'xml': 'https://evil.invalid'}}], 'totalNoticeCount': 1}).encode()
        def acquire(req, dest):
            dest.write_bytes(raw)
            return {'bodySha256': ted.sha(raw), 'failure': None, 'httpStatus': '200'}
        with tempfile.TemporaryDirectory() as d, patch.object(ted, 'acquire', side_effect=acquire) as mock:
            private = Path(d) / 'new'
            e = ted.fetch(self.source(), private, 1)
            self.assertEqual(mock.call_count, 1)
            self.assertEqual(len(e['requests']), 1)
            self.assertEqual(e['discoveries'][0]['xmlURL'], 'https://ted.europa.eu/en/notice/126421-2025/xml')
            self.assertFalse(e['discoveries'][0]['tedVersionVerified'])
            with self.assertRaises(FileExistsError):
                ted.fetch(self.source(), private, 1)
            self.assertEqual(mock.call_count, 1)
        with self.assertRaises(ValueError):
            ted.fetch(self.source(), ROOT / 'data/private', 1)

    def test_cache_hash_and_attempt_ceiling(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / '1.body').write_bytes(b'{}')
            req = {**ted.plan(self.source())[0], 'file': '1.body', 'bodySha256': 'bad'}
            with self.assertRaises(ValueError):
                ted.process(self.source(), [req], p)
            with self.assertRaises(ValueError):
                ted.process(self.source(), [req] * 13, p)

    def test_transport_stream_limit_and_curl_no_redirect_retry_flags(self):
        original = subprocess.Popen
        commands = []
        def local_process(cmd, **kwargs):
            commands.append(cmd)
            return original([sys.executable, '-c',
                             'import sys;sys.stdout.write("123456789");sys.stdout.flush();sys.stderr.write("200")'],
                            **kwargs)
        with tempfile.TemporaryDirectory() as d, patch.object(ted, 'LIMIT', 8), \
                patch.object(ted.subprocess, 'Popen', side_effect=local_process):
            meta = ted.acquire(ted.plan(self.source())[0], Path(d) / 'response.body')
            self.assertEqual(meta['failure'], 'body-limit')
            self.assertLessEqual(meta['bytes'], 8)
            self.assertEqual((Path(d) / 'response.body').stat().st_mode & 0o777, 0o600)
        cmd = commands[0]
        for flag, value in [('--retry', '0'), ('--max-redirs', '0'), ('--max-time', '15'),
                            ('--proto', '=https'), ('--max-filesize', '8')]:
            self.assertEqual(cmd[cmd.index(flag) + 1], value)
        self.assertNotIn('--location', cmd)
        self.assertEqual(cmd[1], '--disable')

    def test_xml_only_followup_is_bounded_and_preserves_prior_attempts(self):
        prior = json.loads((ROOT / 'data/paris-ted-link-evidence.json').read_text())
        source = prior['source']
        def failed(req, dest):
            self.assertEqual(req['kind'], 'xml')
            self.assertEqual(req['method'], 'GET')
            self.assertTrue(req['url'].startswith('https://ted.europa.eu/en/notice/'))
            self.assertIsNone(req['requestBody'])
            return {'failure': 'http-or-transfer-failed', 'httpStatus': '429'}
        with tempfile.TemporaryDirectory() as d, patch.object(ted, 'acquire', side_effect=failed) as acquire:
            directory = Path(d) / 'new'
            ledger = ted.fetch_xml_from(source, prior, directory, 5)
            self.assertEqual(acquire.call_count, 5)
            self.assertEqual(len(ledger['requests']), 17)
            self.assertEqual(ledger['requests'][:12], prior['requests'])
            self.assertEqual(ledger['requestAccounting']['followupXMLAttempts'], 5)
            self.assertEqual(ted.replay_public(ledger), ledger)
            with self.assertRaises(FileExistsError):
                ted.fetch_xml_from(source, prior, directory, 5)
            with self.assertRaises(ValueError):
                ted.fetch_xml_from(source, prior, Path(d) / 'bad', 6)

    def test_public_version_followup_preserves_failures_and_no_crosswalk(self):
        ledger = json.loads((ROOT / 'data/paris-ted-version-evidence.json').read_text())
        self.assertEqual(ted.replay_public(ledger), ledger)
        self.assertEqual(ledger['requestAccounting']['totalAttempts'], 17)
        followup = ledger['requests'][12:]
        self.assertEqual(sum(r.get('httpStatus') == '429' for r in followup), 2)
        self.assertEqual(sum(r.get('evidence', {}).get('exactAwardVersion', False) for r in followup), 3)
        self.assertFalse(ledger['exactCrosswalkForReview'])
        hits = [h for h in ledger['discoveries'] if h['relation'] == 'exact-award-notice-UUID']
        self.assertEqual(sum(h['tedVersionVerified'] for h in hits), 3)
        changed = json.loads(json.dumps(ledger))
        fields = changed['requests'][12]['evidence']['fields']
        header = next(f for f in fields if f['pointer'].count('/') == 2 and f['pointer'].endswith('}VersionID[1]'))
        header['value'] = '02'
        with self.assertRaises(ValueError):
            ted.replay_public(changed)
        ledger['requestAccounting']['followupXMLAttempts'] = 0
        with self.assertRaises(ValueError):
            ted.replay_public(ledger)

    def test_default_cli_is_offline(self):
        completed = subprocess.run([sys.executable, str(ROOT / 'tools/investigate-paris-ted.py')],
                                   capture_output=True, text=True, check=True, timeout=10)
        ledger = json.loads(completed.stdout)
        self.assertEqual(ledger['requests'], [])
        self.assertEqual(ledger['discoveries'], [])
        self.assertEqual(len(ledger['source']['notices']), 5)

    def test_replay_public_evidence_without_private_files(self):
        ledger = json.loads((ROOT / 'data/paris-ted-link-evidence.json').read_text())
        with patch.object(ted, 'acquire', side_effect=AssertionError('network forbidden')):
            self.assertEqual(ted.replay_public(ledger), ledger)
        self.assertEqual(len(ledger['requests']), 12)
        hits = [h for h in ledger['discoveries'] if h['relation'] == 'exact-award-notice-UUID']
        self.assertEqual(len(hits), 5)
        self.assertEqual({h['publicationNumber'] for h in hits},
                         {'126421-2025', '129139-2025', '218409-2025', '264382-2025', '277338-2025'})
        previous = [h for h in ledger['discoveries'] if h['publicationNumber'] == '723965-2024']
        self.assertEqual(previous[0]['relation'], 'same-procedure-other-notice')
        self.assertFalse(ledger['exactCrosswalkForReview'])
        self.assertTrue(all(not h['xmlFetched'] for h in hits))
        syntax = [r for r in ledger['requests'] if r['kind'] == 'search' and r['requestBody']['checkQuerySyntax']]
        self.assertEqual(len(syntax), 5)
        self.assertTrue(all(not r['searchExecuted'] for r in syntax))
        ledger['exactCrosswalkForReview'] = True
        with self.assertRaises(ValueError):
            ted.replay_public(ledger)


if __name__ == '__main__':
    unittest.main()
