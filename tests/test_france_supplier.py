import importlib.util
from pathlib import Path
import tempfile
import unittest

import duckdb

spec = importlib.util.spec_from_file_location('france_labels', Path(__file__).resolve().parents[1] / 'tools/france-label-checks.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SupplierMeasuresTest(unittest.TestCase):
    def test_supplier_measures(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            con = duckdb.connect()
            con.execute("""CREATE TABLE measures(uid VARCHAR, acheteur_id VARCHAR, titulaire_id VARCHAR,
                cpv_division VARCHAR, supplier_dependence DOUBLE)""")
            con.executemany('INSERT INTO measures VALUES (?, ?, ?, ?, ?)', [
                ('a', 'buyer1', '12345678900001', '45', .75),
                ('b', 'buyer1', '12345678900001', '45', .75),
                ('c', 'buyer2', '98765432100001', '45', 1.0),
                ('d', 'buyer2', '11111111100001', '45', .2),
            ])
            con.execute("""CREATE TABLE decp(uid VARCHAR, dateNotification DATE, titulaire_activite_code VARCHAR,
                titulaire_typeIdentifiant VARCHAR, titulaire_id VARCHAR, montant DOUBLE, modification_id INTEGER)""")
            con.executemany('INSERT INTO decp VALUES (?, ?, ?, ?, ?, ?, 0)', [
                ('a', '2020-01-01', '41.20A', 'SIRET', '12345678900001', 10),
                ('b', '2021-01-01', '41.20A', 'SIRET', '12345678900001', 20),
                ('c', '2020-01-01', '41.10A', 'SIRET', '98765432100001', 30),
                ('d', '2020-01-01', None, 'SIRET', '11111111100001', 40),
            ])
            con.execute("""CREATE TABLE sirene(siren VARCHAR, dateCreationUniteLegale DATE,
                etatAdministratifUniteLegale VARCHAR, dateDebut DATE)""")
            con.executemany('INSERT INTO sirene VALUES (?, ?, ?, ?)', [
                ('123456789', '2010-01-01', 'C', '2022-01-01'),
                ('987654321', '2019-01-01', 'A', '2019-01-01'),
            ])
            for table, path in [('measures', root / 'measures.parquet'), ('decp', root / 'decp.parquet'), ('sirene', root / 'sirene.parquet')]:
                con.execute(f'COPY {table} TO ? (FORMAT PARQUET)', [str(path)])
            con.close()
            module.supplier(root / 'decp.parquet', root / 'sirene.parquet', root, root / 'temp')
            con = duckdb.connect()
            rows = con.execute('SELECT * FROM read_parquet(?) ORDER BY uid', [str(root / 'measures-supplier.parquet')]).fetchall()
            self.assertEqual(rows[0], ('a', 120, 24, False, 82, .5, .75))
            self.assertEqual(rows[1][2:4], (12, False))
            self.assertIsNone(rows[1][-1])
            self.assertEqual(rows[2][2:4], (82, True))
            self.assertIsNone(rows[3][1])
            con.close()


if __name__ == '__main__':
    unittest.main()
