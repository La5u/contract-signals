"""Synthetic offline tests; no national file or network required."""
import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

try:
    import pyarrow as pa
    import pyarrow.parquet as pq
    import numpy
    import scipy
    AVAILABLE = True
except ImportError:
    AVAILABLE = False

ROOT=Path(__file__).resolve().parents[1]
if AVAILABLE:
    spec=importlib.util.spec_from_file_location("decp_national",ROOT/"tools/analyze-decp-national.py")
    national=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(national)


def fixture(cid="one",**changes):
    row={"uid":"buyer"+cid,"id":cid,"acheteur_id":"buyer","titulaire_id":"12345678900001",
         "titulaire_typeIdentifiant":"SIRET","nature":"Marché","objet":"Travaux","montant":1000.,
         "montant_rationalise":1000.,"montant_anomalie":None,"codeCPV":"45000000-7",
         "procedure":"Appel d'offres ouvert","dureeMois":12,"offresRecues":1,
         "dateNotification":"2024-01-01","datePublicationDonnees":"2024-01-11",
         "modification_id":0,"donneesActuelles":True,"typesPrix":"Définitif ferme",
         "sourceDataset":"source-a"}
    return dict(row,**changes)


@unittest.skipUnless(AVAILABLE,"pyarrow/numpy/scipy unavailable")
class NationalTests(unittest.TestCase):
    def model_fixture(self):
        rng = numpy.random.default_rng(17)
        rows, labels = [], []
        for buyer in range(41):
            for _ in range(210):
                label = int(rng.integers(2))
                log_amount = float(rng.normal(10, 1))
                probability = 1 / (1 + numpy.exp(-(-1 + .6*label + .2*(log_amount-10))))
                rows.append({"buyer_key": f"buyer-{buyer:02d}", "cpv2": "45", "year": "2024",
                             "amount": numpy.exp(log_amount),
                             "y": 0 if buyer == 0 else int(rng.random() < probability)})
                labels.append(label)
        return rows, numpy.asarray(labels)

    def test_zero_event_buyer_previously_penalized_now_pooled(self):
        rows, labels = self.model_fixture()
        # The imported legacy design retains >=20-row buyers regardless of events.
        legacy, _ = national.ct.fit_model(rows, labels, 0, True)
        self.assertEqual(legacy["status"], "regularized")
        with patch.object(national.ct, "design", national.national_design):
            fitted, _ = national.ct.fit_model(rows, labels, 0, True)
        self.assertEqual(fitted["status"], "ok")
        self.assertTrue(fitted["inference_usable"])
        self.assertIn("buyer-cluster sandwich", fitted["covariance"])
        self.assertEqual(fitted["buyer_clusters"], 41)
        self.assertEqual(fitted["spec"]["buyer_fe_levels"], 39)
        self.assertEqual(fitted["spec"]["pooled_level_counts"]["buyers"], 2)
        self.assertNotIn("buyer_key:buyer-00", fitted["spec"]["coefficient_names"])

    def test_lone_zero_event_other_level_merges_with_supported_reference(self):
        rows, labels = self.model_fixture()
        for r in rows[:10]:
            r["cpv2"] = "rare"
        x, names, spec = national.national_design(rows, labels, 0, False)
        self.assertNotIn("cpv2:__other__", names)
        self.assertEqual(spec["pooled_level_counts"]["cpv2"], 2)
        self.assertEqual(numpy.linalg.matrix_rank(x), x.shape[1])
        with patch.object(national.ct, "design", national.national_design):
            fitted, _ = national.ct.fit_model(rows, labels, 0, False)
        self.assertEqual(fitted["status"], "ok")

    def test_control_aliased_with_input_drops_control(self):
        rows, labels = self.model_fixture()
        for r, label in zip(rows, labels):
            r["year"] = str(2023 + label)
        x, names, spec = national.national_design(rows, labels, 0, False)
        self.assertIn("bin:1", names)
        self.assertFalse(any(name.startswith("year:") for name in names))
        self.assertEqual(spec["dropped_redundant_columns_count"], 1)
        self.assertEqual(numpy.linalg.matrix_rank(x), x.shape[1])

    def test_global_centering_preserves_bin_effect_and_cluster_ci(self):
        rows, labels = self.model_fixture()
        x, _, _ = national.national_design(rows, labels, 0, False)
        numpy.testing.assert_allclose(x[:,1:].mean(axis=0), 0, atol=1e-12)
        original, _ = national.ct.fit_model(rows, labels, 0, False)
        original_design, original_minimize = national.ct.design, national.ct.minimize
        centered, _ = national.national_fit_model(rows, labels, 0, False)
        self.assertIs(national.ct.design, original_design)
        self.assertIs(national.ct.minimize, original_minimize)
        self.assertEqual(original["status"], "ok")
        self.assertEqual(centered["status"], "ok")
        self.assertAlmostEqual(original["log_likelihood"], centered["log_likelihood"], places=6)
        self.assertAlmostEqual(original["bin_estimates"]["1"]["log_or"],
                               centered["bin_estimates"]["1"]["log_or"], places=6)
        numpy.testing.assert_allclose(original["bin_estimates"]["1"]["ci95"],
                                      centered["bin_estimates"]["1"]["ci95"], rtol=1e-6)

    def stage(self,records,parquet=False):
        db=sqlite3.connect(":memory:")
        self.addCleanup(db.close)
        table=pa.Table.from_pylist(records)
        if parquet:
            temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
            path=Path(temp.name)/"fixture.parquet"
            pq.write_table(table,path,row_group_size=2)
            inspection=national.stage(path,db)
        else:
            inspection=national.stage(table,db)
        return db,inspection

    def test_initial_unit_cross_source_duplicates_and_old_initial_state(self):
        records=[fixture(donneesActuelles=False),fixture(sourceDataset="source-b",donneesActuelles=True),
                 fixture(modification_id=1,montant=1200.,montant_rationalise=1200.),
                 fixture("only-mod",modification_id=2)]
        db,info=self.stage(records,True)
        rows,excluded,diag,coverage=national.eligible_rows(db)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["amount"],1000)
        self.assertEqual(rows[0]["decp_amount_increase_percent"],20)
        self.assertEqual(info["counts"]["duplicate_initial_snapshots_removed"],1)
        self.assertEqual(info["counts"]["modification_only_contract_groups"],1)

    def test_conflicts_never_pick_arbitrary_versions(self):
        records=[fixture("amount"),fixture("amount",montant=1001.,montant_rationalise=1001.),
                 fixture("cpv"),fixture("cpv",uid="different-uid",codeCPV="72000000-5"),
                 fixture("supplier"),fixture("supplier",titulaire_id="98765432100001"),
                 fixture("date"),fixture("date",dateNotification="2018-01-01"),
                 fixture("object",objet="first"),fixture("object",objet="second"),fixture("safe")]
        db,info=self.stage(records)
        self.assertEqual(info["counts"]["conflicting_initial_groups_excluded"],5)
        self.assertEqual(db.execute("SELECT cid FROM units").fetchall(),[("safe",)])

    def test_mapping_matches_site_and_mapa_excluded(self):
        self.assertEqual(national.procedure_family("Appel d'offres ouvert"),"formal_calls")
        self.assertEqual(national.procedure_family("Appel d'offres restreint"),"formal_calls")
        self.assertEqual(national.procedure_family("Procédure avec négociation"),"other_competitive")
        self.assertEqual(national.procedure_family("Dialogue compétitif"),"other_competitive")
        self.assertEqual(national.procedure_family("Procédure adaptée"),"adapted")
        self.assertIsNone(national.importer.direct("Procédure adaptée"))
        self.assertEqual(national.procedure_family("Appel d’offres ouvert"),"unknown")
        db,_=self.stage([fixture("mapa",procedure="Procédure adaptée"),fixture("open")])
        rows,excluded,_,coverage=national.eligible_rows(db)
        self.assertEqual(len(rows),1)
        self.assertEqual(excluded["not_explicitly_competitive"],1)
        self.assertEqual(coverage["adapted"]["usable_offer_count"],1)

    def test_date_amount_and_unversioned_exclusions(self):
        db,info=self.stage([fixture("start",dateNotification="2019-01-01"),
            fixture("end",dateNotification="2026-09-01"),fixture("later",dateNotification="2026-09-02"),
            fixture("bad",montant_anomalie="suspect"),fixture("unversioned",modification_id=None),
            fixture("zero",montant=0.,montant_rationalise=0.)])
        self.assertEqual(db.execute("SELECT COUNT(*) FROM units").fetchone()[0],2)
        for k in ("outside_date_window_groups_excluded","amount_anomaly_groups_excluded",
                  "unversioned_rows_excluded","missing_or_nonpositive_amount_groups_excluded"):
            self.assertEqual(info["counts"][k],1)

    def test_context_is_leave_one_out_and_includes_noncompetitive_contracts(self):
        records=[fixture(str(i),procedure="Procédure adaptée" if i<10 else "Appel d'offres ouvert",
                         datePublicationDonnees=f"2024-01-{i+2:02d}") for i in range(11)]
        db,_=self.stage(records)
        rows,_,_,_=national.eligible_rows(db)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["supplier_concentration_share"],1)
        self.assertEqual(rows[0]["buyer_relative_delay_days"],5.5)
        for values in ([1,2,3,4],[1,1,1,5,7],[2,3]):
            for rank in range(len(values)):
                self.assertEqual(national.loo_median(values,rank),float(numpy.median(values[:rank]+values[rank+1:])))

    def test_modification_conflict_not_zero_increase(self):
        db,_=self.stage([fixture(),fixture(modification_id=1,montant=1200.,montant_rationalise=1200.),
                        fixture(modification_id=1,montant=1300.,montant_rationalise=1300.)])
        rows,_,diag,_=national.eligible_rows(db)
        self.assertIsNone(rows[0]["decp_amount_increase_percent"])
        self.assertEqual(diag["modification_validation_conflicting_modification"],1)

    def test_aggregate_output_and_sanitized_model_have_no_ids(self):
        report={"bins":[{"n":30,"events":10,"or":1.4,"ci95":[1.1,1.8]}],
                "models":{"spec":{"coefficient_names":["buyer_key:12345678900001"],
                "pooled_levels":{"buyer_key":["12345678900001"]},"n":30}}}
        clean=national.sanitize_models(report)
        national.assert_aggregate_only(clean)
        self.assertNotIn("12345678900001",json.dumps(clean))
        with self.assertRaises(ValueError):national.assert_aggregate_only({"nested":{"uid":"leak"}})
        empty=national.analyze([])
        national.assert_aggregate_only(empty)
        self.assertEqual(empty["inputs"]["submission_period_days"]["n"],0)
        out=ROOT/"research/thresholds/france-national.json"
        if out.exists():national.assert_aggregate_only(json.loads(out.read_text()))


if __name__=="__main__":
    unittest.main()
