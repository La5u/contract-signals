import contextlib
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path

try:
    import duckdb
except ImportError:
    raise unittest.SkipTest('France checks need optional duckdb')

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('france_checks', ROOT / 'tools/france-label-checks.py')
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)


class DryRun(unittest.TestCase):
    def test_counts_inputs_without_labelled_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            con = duckdb.connect()
            con.execute('''CREATE TABLE d AS SELECT 'u' uid, 0 modification_id,
                1 offresRecues, 'open' procedure, 100.0 montant, DATE '2023-01-01' dateNotification,
                'Services' type, 12 dureeMois, 'buyer' acheteur_id, '12345678900001' titulaire_id,
                'SIRET' titulaire_typeIdentifiant, '12345678' codeCPV, NULL::VARCHAR idAccordCadre,
                'Solidaire' typeGroupementOperateurs, TRUE sousTraitanceDeclaree,
                DATE '2023-01-02' datePublicationDonnees, 10 titulaire_distance,
                'PME' titulaire_categorie, '62.01Z' titulaire_activite_code
                UNION ALL SELECT 'v', 1, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL,
                NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL''')
            con.execute("CREATE TABLE s AS SELECT '123456789' siren, DATE '2000-01-01' dateCreationUniteLegale, DATE '2024-01-01' dateDebut, 'C' etatAdministratifUniteLegale")
            con.execute(f"COPY d TO '{tmp / 'd.parquet'}' (FORMAT PARQUET)")
            con.execute(f"COPY s TO '{tmp / 's.parquet'}' (FORMAT PARQUET)")
            con.close()
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                checks.dry_run(tmp / 'd.parquet', tmp / 's.parquet', tmp / 'spill')
            result = out.getvalue()
            self.assertIn('DECP rows: 2; distinct UIDs: 2; initial-state rows: 1', result)
            self.assertIn('SUPPLIER-AGE | 1', result)
            self.assertIn('AMEND-COUNT | 1', result)
            self.assertIn('Modification rows: 1; notification dated: 0; publication dated: 0; either: 0', result)
            self.assertNotIn('hit rate', result.lower())


class Measures(unittest.TestCase):
    def test_amendments_shares_and_holders(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            con = duckdb.connect()
            con.execute("""CREATE TABLE d AS SELECT * FROM (VALUES
                ('u', 0, '12345678900001', '11111111100002', 100.0, DATE '2022-01-01', DATE '2022-01-02'),
                ('u', 0, '12345678900001', '11111111100001', 100.0, DATE '2022-01-01', DATE '2022-01-02'),
                ('v', 0, '12345678900001', '22222222200001', 300.0, DATE '2022-02-01', DATE '2022-02-02'),
                ('u', 1, '12345678900001', '11111111100001', 120.0, DATE '2022-06-01', NULL),
                ('u', 1, '12345678900001', '11111111100002', 120.0, DATE '2022-06-01', NULL),
                ('u', 2, '12345678900001', '11111111100001', 150.0, NULL, DATE '2023-01-01')
              ) t(uid, modification_id, acheteur_id, titulaire_id, montant, dateNotification, datePublicationDonnees)""")
            con.execute("""CREATE TABLE source AS SELECT *, 'SIRET' titulaire_typeIdentifiant,
              'Services' type, '12345678' codeCPV, 'Appel d offres ouvert' procedure,
              12 dureeMois, 2 offresRecues, NULL::VARCHAR idAccordCadre,
              'Pas de groupement' typeGroupementOperateurs, false sousTraitanceDeclaree,
              10 titulaire_distance, 'PME' titulaire_categorie FROM d""")
            con.execute('COPY source TO ? (FORMAT PARQUET)', [str(tmp / 'source.parquet')])
            con.close()
            checks.measures(tmp / 'source.parquet', tmp / 'out', tmp / 'spill')
            con = duckdb.connect()
            rows = con.execute('SELECT uid, titulaire_id, holders, amend_count_24m, amend_price_pct, buyer_share FROM read_parquet(?) ORDER BY uid', [str(tmp / 'out/measures.parquet')]).fetchall()
            self.assertEqual(rows, [('u', '11111111100001', 2, 2, 150.0, 0.25),
                                    ('v', '22222222200001', 1, 0, None, 0.75)])
            con.close()


if __name__ == '__main__':
    unittest.main()
