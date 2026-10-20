import importlib.util
import gzip
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('ukraine_candidate_indicators', ROOT / 'tools/ukraine-candidate-indicators.py')
ci = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ci)

ROW = {'lotId': None, 'awardId': 'a1', 'contractId': 'C-1', 'offers': 2, 'disqualifiedBefore': 0, 'procedure': 'aboveThresholdUA',
       'cpv': '45000000', 'supplierIds': [{'id': '12345678', 'identifierType': 'EDRPOU'}]}


def tender(**kw):
    t = {'value': {'amount': 1000.0, 'currency': 'UAH'},
         'tenderPeriod': {'startDate': '2024-01-01T09:00:00+02:00', 'endDate': '2024-01-11T09:00:00+02:00'},
         'bids': [{'id': 'b1', 'status': 'active'}, {'id': 'b2', 'status': 'active'}],
         'awards': [{'id': 'a1', 'bid_id': 'b1', 'status': 'active', 'date': '2024-01-15T10:00:00+02:00', 'value': {'amount': 990.0, 'currency': 'UAH'}}],
         'contracts': [{'contractID': 'C-1', 'dateSigned': '2024-01-25T00:00:00+02:00'}], 'documents': []}
    t.update(kw)
    return t


def feats(t, contract=None, row=None):
    return ci.tender_features(row or ROW, t, contract)


def bid(i, amount=990, **kw):
    b = {'id': f'b{i}', 'status': 'active', 'date': f'2024-01-10T{9 + i:02d}:00:00+02:00',
         'value': {'amount': amount, 'currency': 'UAH'}, 'documents': [{'hash': f'h{i}-{n}'} for n in range(3)],
         'tenderers': [{'identifier': {'id': f'bidder{i}'},
                        'contactPoint': {'telephone': f'+380 (50) 123-45-{i:02d}', 'email': f'bidder{i}@example.invalid'},
                        'address': {'streetAddress': f'Street {i}', 'locality': 'Kyiv'}}]}
    b.update(kw)
    return b


def bidder(b):
    return b['tenderers'][0]


def kfeats(*bids, **kw):
    return ci.bid_features(ROW, tender(bids=list(bids), **kw))


class BidRigging(unittest.TestCase):
    def test_hidden_bids_and_missing_record_are_unknown(self):
        self.assertEqual(ci.bid_features(ROW, None), dict.fromkeys(ci.BID_CANDIDATES))
        t = tender(status='complete')
        del t['bids']
        self.assertEqual(ci.bid_features(ROW, t), dict.fromkeys(ci.BID_CANDIDATES))
        self.assertEqual(kfeats(), dict.fromkeys(ci.BID_CANDIDATES, False))
        self.assertEqual(kfeats(bid(1)), dict.fromkeys(ci.BID_CANDIDATES, False))
        b = bid(2)
        del b['tenderers']
        self.assertEqual(kfeats(bid(1), b), dict(dict.fromkeys(ci.BID_CANDIDATES), **{'K5 tight-bids': False}))

    def test_shared_contact_normalisation_and_unknown(self):
        key = 'K1 shared-contact'
        a, b = bid(1), bid(2)
        self.assertFalse(kfeats(a, b)[key])
        bidder(b)['contactPoint']['telephone'] = '0501234501'
        self.assertTrue(kfeats(a, b)[key])
        bidder(b)['contactPoint']['telephone'] = '123-45678'
        bidder(a)['contactPoint']['telephone'] = '12345678'
        self.assertFalse(kfeats(a, b)[key])  # short numbers cannot match
        bidder(b)['contactPoint']['email'] = '  BIDDER1@EXAMPLE.INVALID  '
        self.assertTrue(kfeats(a, b)[key])
        del bidder(b)['contactPoint']
        self.assertIsNone(kfeats(a, b)[key])
        c = bid(3)
        bidder(c)['contactPoint'] = dict(bidder(a)['contactPoint'])
        self.assertTrue(kfeats(a, b, c)[key])  # a known match overrides another missing contact

    def test_shared_address_normalisation_locality_and_unknown(self):
        key = 'K2 shared-address'
        a, b = bid(1), bid(2)
        self.assertFalse(kfeats(a, b)[key])
        bidder(a)['address'] = {'streetAddress': 'Вул. Хрещатик, 1-А', 'locality': 'м. Київ'}
        bidder(b)['address'] = {'streetAddress': 'ВУЛ ХРЕЩАТИК 1А', 'locality': 'М КИЇВ'}
        self.assertTrue(kfeats(a, b)[key])
        bidder(b)['address']['locality'] = 'Lviv'
        self.assertFalse(kfeats(a, b)[key])
        for x in (a, b):
            bidder(x)['address'] = {'streetAddress': ' . ', 'locality': 'Kyiv'}
        self.assertFalse(kfeats(a, b)[key])  # normalised empty streets are skipped
        del bidder(b)['address']['locality']
        self.assertIsNone(kfeats(a, b)[key])

    def test_shared_document_hashes_and_tender_exclusion(self):
        key = 'K3 shared-document'
        a, b = bid(1), bid(2)
        self.assertFalse(kfeats(a, b)[key])
        b['financialDocuments'] = [{'hash': a['documents'][0]['hash']}]
        self.assertTrue(kfeats(a, b)[key])
        self.assertFalse(kfeats(a, b, documents=[dict(a['documents'][0])])[key])
        b['financialDocuments'] = [{'title': 'same file name', 'url': 'same url'}]
        a['documents'].append(dict(b['financialDocuments'][0]))
        self.assertIsNone(kfeats(a, b)[key])  # never infer hashes from names or URLs
        b['eligibilityDocuments'] = [{'hash': a['documents'][0]['hash']}]
        self.assertTrue(kfeats(a, b)[key])
        self.assertFalse(kfeats(bid(1, documents=[]), bid(2, documents=[]))[key])

    def test_close_submission_timezones_and_strict_boundary(self):
        key = 'K4 close-submission'
        a = bid(1, date='2024-01-10T10:00:00+02:00')
        b = bid(2, date='2024-01-10T08:09:59Z')
        self.assertTrue(kfeats(a, b)[key])
        b['date'] = '2024-01-10T08:10:00+00:00'
        self.assertFalse(kfeats(a, b)[key])
        self.assertTrue(kfeats(b, a, bid(3, date='2024-01-10T08:00:01Z'))[key])
        for date in (None, 'bad', '2024-01-10T08:00:00'):
            with self.subTest(date=date):
                self.assertIsNone(kfeats(a, bid(2, date=date))[key])

    def test_tight_bids_population_cv_and_unknown(self):
        key = 'K5 tight-bids'
        self.assertTrue(kfeats(bid(1, 96.5), bid(2, 100), bid(3, 103.5))[key])  # population CV < 3%, sample CV > 3%
        self.assertFalse(kfeats(bid(1, 90), bid(2, 100), bid(3, 110))[key])
        self.assertFalse(kfeats(bid(1, 97), bid(2, 97), bid(3, 103), bid(4, 103))[key])  # exactly 3%
        self.assertFalse(kfeats(bid(1), bid(2))[key])
        self.assertIsNone(kfeats(bid(1), bid(2), bid(3, value={}))[key])
        self.assertIsNone(kfeats(bid(1, 0), bid(2, 0), bid(3, 0))[key])
        self.assertIsNone(kfeats(bid(1), bid(2), bid(3, float('nan')))[key])

    def test_close_runner_up_orders_values_and_inclusive_boundary(self):
        key = 'K6 close-runner-up'
        self.assertTrue(kfeats(bid(1, 150), bid(2, 101), bid(3, 100))[key])
        self.assertFalse(kfeats(bid(1, 100), bid(2, 101.01))[key])
        self.assertFalse(kfeats(bid(1))[key])
        self.assertIsNone(kfeats(bid(1), bid(2, value={}))[key])

    def test_all_bids_near_expected_requires_every_value_and_currency(self):
        key = 'K7 all-bids-near-expected'
        self.assertTrue(kfeats(bid(1, 970), bid(2, 1100))[key])
        self.assertFalse(kfeats(bid(1, 969.99), bid(2, 990))[key])
        self.assertFalse(kfeats(bid(1))[key])
        self.assertIsNone(kfeats(bid(1), bid(2, value={}))[key])
        self.assertIsNone(kfeats(bid(1), bid(2, value={'amount': 990, 'currency': 'EUR'}))[key])
        self.assertIsNone(kfeats(bid(1), bid(2), value={'amount': 1000})[key])

    def test_empty_cover_counts_all_document_lists_and_excludes_winner(self):
        key = 'K8 empty-cover-bid'
        self.assertFalse(kfeats(bid(1, documents=[]), bid(2))[key])
        self.assertTrue(kfeats(bid(1), bid(2, documents=[{}, {}]))[key])
        for field in ci.BID_DOCUMENTS[1:]:
            with self.subTest(field=field):
                self.assertFalse(kfeats(bid(1), bid(2, documents=[{}, {}], **{field: [{}]}))[key])
        b = bid(2)
        del b['documents']
        self.assertTrue(kfeats(bid(1), b)[key])  # omitted API lists are empty
        self.assertIsNone(kfeats(bid(1), bid(2), awards=[])[key])
        self.assertIsNone(kfeats(bid(1), bid(2, id=None))[key])

    def test_distinct_bidder_identifiers(self):
        a, b = bid(1, documents=[]), bid(2, documents=[])
        b['tenderers'] = a['tenderers']
        b['date'] = a['date']
        self.assertEqual(kfeats(a, b), dict.fromkeys(ci.BID_CANDIDATES, False))
        # Even a duplicate preceding the winning bid cannot become a cover bid.
        self.assertFalse(kfeats(b, a)['K8 empty-cover-bid'])
        b['tenderers'] = [{'identifier': {'id': 'bidder2'}}]
        self.assertIsNone(kfeats(a, b)['K1 shared-contact'])

    def test_bid_statuses_and_invalidation_before_opening(self):
        a, b = bid(1), bid(2, documents=[])
        for status in ('active', 'unsuccessful', 'invalid'):
            with self.subTest(status=status):
                b['status'] = status
                self.assertTrue(kfeats(a, b)['K8 empty-cover-bid'])
        for status in ('deleted', 'draft', 'pending'):
            with self.subTest(status=status):
                b['status'] = status
                self.assertFalse(kfeats(a, b)['K8 empty-cover-bid'])
        b['status'] = 'invalid'
        b['dateModified'] = '2024-01-10T10:00:00+02:00'
        self.assertFalse(kfeats(a, b)['K8 empty-cover-bid'])
        b['dateModified'] = '2024-01-12T10:00:00+02:00'
        self.assertTrue(kfeats(a, b)['K8 empty-cover-bid'])
        b['status'] = 'pending'
        for field in ('awards', 'qualifications'):
            with self.subTest(field=field):
                records = [{'bid_id': 'b2', 'status': 'unsuccessful'}]
                if field == 'awards':
                    records += tender()['awards']
                self.assertTrue(kfeats(a, b, **{field: records})['K8 empty-cover-bid'])

    def test_awarded_lot_filter_value_date_and_expected(self):
        a, b = bid(1, 10), bid(2, 100)
        a['lotValues'] = [{'relatedLot': 'L', 'value': {'amount': 99, 'currency': 'UAH'}, 'date': '2024-01-10T10:00:00+02:00'}]
        b['lotValues'] = [{'relatedLot': 'OTHER', 'value': {'amount': 5, 'currency': 'UAH'}},
                          {'relatedLot': 'L', 'value': {'amount': 99.5, 'currency': 'UAH'}, 'date': '2024-01-10T10:01:00+02:00'}]
        outsider = bid(3, documents=[])
        outsider['lotValues'] = [{'relatedLot': 'OTHER'}]
        bidder(outsider)['contactPoint'] = dict(bidder(a)['contactPoint'])
        bidder(outsider)['address'] = dict(bidder(a)['address'])
        outsider['documents'] = [dict(a['documents'][0])]
        lots = [{'id': 'OTHER', 'value': {'amount': 1000, 'currency': 'UAH'}}, {'id': 'L', 'value': {'amount': 100, 'currency': 'UAH'}}]
        t = tender(bids=[a, b, outsider], lots=lots, awards=[dict(tender()['awards'][0], lotID='L')])
        f = ci.bid_features(dict(ROW, lotId='OTHER'), t)  # award lot takes precedence over row
        self.assertEqual([f[k] for k in ci.BID_CANDIDATES], [False, False, False, True, False, True, True, False])
        del lots[1]['value']
        self.assertIsNone(ci.bid_features(ROW, t)['K7 all-bids-near-expected'])  # no tender fallback
        del a['lotValues'][0]['value']
        del b['lotValues'][1]['date']
        f = ci.bid_features(ROW, t)
        self.assertFalse(f['K6 close-runner-up'])  # bid value fallback only if lot value is absent
        self.assertFalse(f['K4 close-submission'])  # date fallback
        t['awards'][0].pop('lotID')
        self.assertEqual(ci.bid_features(ROW, t), dict.fromkeys(ci.BID_CANDIDATES))

    def test_lot_status_and_disqualification_scope(self):
        a, b = bid(1), bid(2, documents=[])
        a['lotValues'] = [{'relatedLot': 'L'}]
        b['lotValues'] = [{'relatedLot': 'L', 'status': 'draft'}]
        kw = {'lots': [{'id': 'L'}], 'awards': [dict(tender()['awards'][0], lotID='L')]}
        self.assertFalse(kfeats(a, b, **kw)['K8 empty-cover-bid'])
        b['lotValues'][0]['status'] = 'unsuccessful'
        self.assertTrue(kfeats(a, b, **kw)['K8 empty-cover-bid'])
        b['status'] = 'pending'
        del b['lotValues'][0]['status']
        kw['qualifications'] = [{'bid_id': 'b2', 'status': 'unsuccessful', 'lotID': 'OTHER'}]
        self.assertFalse(kfeats(a, b, **kw)['K8 empty-cover-bid'])
        kw['qualifications'][0]['lotID'] = 'L'
        self.assertTrue(kfeats(a, b, **kw)['K8 empty-cover-bid'])

    def test_tight_bids_use_lot_values_and_present_missing_values_are_unknown(self):
        bids = [bid(1, 10), bid(2, 100), bid(3, 1000)]
        for b in bids:
            b['lotValues'] = [{'relatedLot': 'L', 'value': {'amount': 99, 'currency': 'UAH'}}]
        t = tender(bids=bids, lots=[{'id': 'L', 'value': {'amount': 100, 'currency': 'UAH'}}],
                   awards=[dict(tender()['awards'][0], lotID='L')])
        self.assertTrue(ci.bid_features(ROW, t)['K5 tight-bids'])
        bids[2]['lotValues'][0]['value'] = None
        f = ci.bid_features(ROW, t)
        self.assertIsNone(f['K5 tight-bids'])
        self.assertIsNone(f['K6 close-runner-up'])
        self.assertIsNone(f['K7 all-bids-near-expected'])


class Award(unittest.TestCase):
    def test_only_qualified_bidder(self):
        t = tender(awards=[{'id': 'a0', 'bid_id': 'b2', 'status': 'unsuccessful'}] + tender()['awards'])
        self.assertTrue(feats(t)['C2 only-qualified-bidder'])
        self.assertFalse(feats(tender())['C2 only-qualified-bidder'])
        self.assertIsNone(feats(tender(bids=[]))['C2 only-qualified-bidder'])

    def test_late_document_window(self):
        doc = lambda d, of='tender': {'documentOf': of, 'datePublished': d, 'dateModified': d}
        self.assertTrue(feats(tender(documents=[doc('2024-01-09T10:00:00+02:00')]))['C6 late-document-change'])
        self.assertFalse(feats(tender(documents=[doc('2024-01-14T10:00:00+02:00')]))['C6 late-document-change'])   # after the deadline
        self.assertFalse(feats(tender(documents=[doc('2024-01-09T10:00:00+02:00', 'lot')]))['C6 late-document-change'])
        self.assertIsNone(feats(tender(documents=[{'documentOf': 'tender'}]))['C6 late-document-change'])

    def test_fast_signature_needs_order(self):
        early = tender(contracts=[{'contractID': 'C-1', 'dateSigned': '2024-01-17T00:00:00+02:00'}])
        before = tender(contracts=[{'contractID': 'C-1', 'dateSigned': '2024-01-14T00:00:00+02:00'}])
        self.assertTrue(feats(early)['C8 fast-signature'])
        self.assertFalse(feats(before)['C8 fast-signature'])
        self.assertFalse(feats(tender())['C8 fast-signature'])


class Price(unittest.TestCase):
    def test_small_drop_uses_lot_value_only(self):
        self.assertTrue(feats(tender())['C9 small-price-drop'])
        row = dict(ROW, lotId='L')
        t = tender(lots=[{'id': 'L'}], awards=[dict(tender()['awards'][0], lotID='L')])
        self.assertIsNone(feats(t, row=row)['C9 small-price-drop'])

    def test_threshold_by_category(self):
        self.assertTrue(feats(tender(value={'amount': 1_400_000, 'currency': 'UAH'}))['C10 just-below-threshold'])   # CPV 45: works
        self.assertFalse(feats(tender(value={'amount': 1_400_000, 'currency': 'UAH'}, mainProcurementCategory='goods'))['C10 just-below-threshold'])


class Execution(unittest.TestCase):
    def test_rationales_and_unknowns(self):
        c = {'status': 'active', 'changes': [{'status': 'active', 'rationaleTypes': ['durationExtension']}, {'status': 'cancelled', 'rationaleTypes': ['volumeCuts']}]}
        f = feats(tender(), c)
        self.assertEqual((f['C12 term-extension-amendment'], f['C13 quantity-cut-amendment'], f['C14 early-termination']), (True, False, False))
        f = feats(tender(), {'changes': [{'status': 'active'}]})
        self.assertIsNone(f['C11 price-change-amendment'])
        self.assertIsNone(f['C14 early-termination'])
        f = feats(tender(), {'status': 'terminated', 'amountPaid': {'amount': 50}, 'value': {'amount': 100}})
        self.assertTrue(f['C14 early-termination'])

    def test_row_features_without_tender(self):
        self.assertEqual(ci.row_features(ROW), {'C1 two-bidders': True, 'C3 two-plus-disqualified': False, 'C15 individual-supplier': False})


class Split(unittest.TestCase):
    def test_halves_are_stable(self):
        self.assertEqual(ci.half('33426253'), ci.half('33426253'))
        self.assertEqual({ci.half(str(i)) for i in range(20)}, {'learn', 'check'})


class Reporting(unittest.TestCase):
    def test_build_is_cache_only_and_outputs_statuses_without_source_data(self):
        a, b = bid(1), bid(2, documents=[])
        bidder(b)['contactPoint'] = dict(bidder(a)['contactPoint'])
        t = tender(bids=[a, b], contracts=[])
        cached = dict(ROW, id='cached', procedureId='t-cached', label='collusion', finality='confirmed', buyerId='buyer')
        missing = dict(cached, id='missing', procedureId='t-missing')
        fetcher = Mock()
        fetcher.fetch.side_effect = [{'status': 200, 'body': json.dumps({'data': t})}, None]
        factory = Mock(return_value=fetcher)
        vc = SimpleNamespace(bc=SimpleNamespace(Fetcher=factory, tender_url=lambda pid: pid), opener=object())
        cc = SimpleNamespace(contract_url=lambda cid: cid)
        with tempfile.TemporaryDirectory() as tmp:
            cohort = Path(tmp) / 'cohort.json.gz'
            with gzip.open(cohort, 'wt') as f:
                json.dump({'rows': [cached, missing]}, f)
            with patch.object(ci, 'load', side_effect=[vc, cc]):
                rows, cut = ci.build(cohort, tmp)
        self.assertEqual(cut, {})
        self.assertEqual(factory.call_args.kwargs, {'budget': 0, 'network': False, 'prior': 0, 'opener': vc.opener})
        self.assertEqual([call.args[0] for call in fetcher.fetch.call_args_list], ['t-cached', 't-missing'])
        self.assertEqual(set(rows[0]['checks']), set(ci.CANDIDATES))
        self.assertEqual(rows[0]['checks']['K1 shared-contact'], {'status': 'signal', 'points': None})
        self.assertTrue(all(rows[1]['checks'][k] == {'status': 'unknown', 'points': None} for k in ci.BID_CANDIDATES))
        self.assertEqual(rows[1]['checks']['C1 two-bidders']['status'], 'signal')
        self.assertEqual(rows[1]['checks']['C3 two-plus-disqualified']['status'], 'clear')
        self.assertEqual(rows[1]['checks']['C15 individual-supplier']['status'], 'clear')
        for checks in (r['checks'] for r in rows):
            self.assertTrue(all(set(check) == {'status', 'points'} for check in checks.values()))
        output = json.dumps(rows)
        for source in ('contactPoint', 'streetAddress', 'tenderers', 'hash', 'bidder1@example.invalid', 'Street 1', 'h1-0'):
            self.assertNotIn(source, output)

    def test_default_and_collusion_cli_include_k_candidates(self):
        for label in ('corruption', 'collusion'):
            with self.subTest(label=label), tempfile.TemporaryDirectory() as tmp:
                checks = {k: {'status': ci.status(v), 'points': None} for k, v in feats(tender(bids=[bid(1), bid(2)])).items()}
                checks['C4 short-tender-period'] = {'status': 'unknown', 'points': None}
                feature_rows = [{'id': 'p', 'procedure': 'aboveThresholdUA', 'label': label, 'finality': 'confirmed', 'buyerId': '1', 'checks': checks},
                                {'id': 'c', 'procedure': 'aboveThresholdUA', 'label': 'comparison', 'finality': None, 'buyerId': '2', 'checks': checks}]
                features_path, results_path = Path(tmp) / 'features.json', Path(tmp) / 'results.json'
                argv = ['--features', str(features_path), '--json', str(results_path)]
                if label == 'collusion':
                    argv += ['--cohort', 'synthetic-collusion.json.gz', '--positive-labels', 'collusion']
                stdout = io.StringIO()
                # Actual pp analysis, resampling, holdout and reporting, on synthetic rows only.
                with patch.object(ci, 'build', return_value=(feature_rows, {})) as build, redirect_stdout(stdout):
                    ci.main(argv)
                self.assertEqual(build.call_args.args[0], 'synthetic-collusion.json.gz' if label == 'collusion' else str(ci.COHORT))
                results = json.loads(results_path.read_text())['results']
                self.assertEqual([r['candidate'] for r in results], ci.CANDIDATES)
                for r in results:
                    self.assertEqual(r['all']['combined']['tenders'], int(checks[r['candidate']]['status'] != 'unknown'))
                    self.assertEqual(r['decision'], ci.pp.decide(r['all']))
                self.assertTrue(all(f'| {k} |' in stdout.getvalue() for k in ci.BID_CANDIDATES))
                self.assertEqual(json.loads(features_path.read_text()), feature_rows)


class MultiBid(unittest.TestCase):
    def test_keeps_rows_whose_single_offer_is_clear(self):
        import tempfile
        rows = [{'id': 'a', 'checks': {'ua-single-offer': {'status': 'clear'}}},
                {'id': 'b', 'checks': {'ua-single-offer': {'status': 'signal'}}},
                {'id': 'c', 'checks': {'ua-single-offer': {'status': 'unknown'}}}, {'id': 'd', 'checks': {}}]
        with tempfile.NamedTemporaryFile('w', suffix='.json') as f:
            json.dump(rows, f)
            f.flush()
            self.assertEqual(ci.multi_bid_ids(f.name), {'a'})


if __name__ == '__main__':
    unittest.main()
