import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("import_decp", Path(__file__).parents[1] / "tools/import-decp-cities.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def row(cid, mod_id="CDL", amount=100, mod_amount="CDL", pub="2024-02-01", mod_date="CDL"):
    return {"acheteur_id": mod.BUYERS[0][0], "id": cid, "idmodification": mod_id,
            "objet": "objet", "montant": amount, "offresrecues": "1", "datenotification": pub,
            "datepublicationdonnees": "2024-03-01", "dureemois": 12, "codecpv": "12345678-9",
            "procedure": "Appel d'offres ouvert", "typesprix": "Définitif ferme", "formeprix": "Ordinaire",
            "nature": "Marché", "idaccordcadre": "CDL", "modalitesexecution": "Bons de commande",
            "techniques": "Sans objet", "montantmodification": mod_amount,
            "dureemoismodification": 15, "datenotificationmodificationmodification": mod_date,
            "datepublicationdonneesmodificationmodification": "2024-04-01",
            "idtitulairemodification": "CDL", "typeidentifianttitulairemodification": "CDL",
            "titulaire_id_1": "12345678900011", "titulaire_typeidentifiant_1": "SIRET",
            "titulaire_id_2": "CDL", "titulaire_typeidentifiant_2": "CDL",
            "titulaire_id_3": "CDL", "titulaire_typeidentifiant_3": "CDL"}


class ImporterRegression(unittest.TestCase):
    def normalize(self, records):
        return mod.normalize({"records": records}, Path("."), {"counts": {}})

    def test_competitive_dialogue_is_competitive_not_direct(self):
        self.assertIs(mod.direct("Dialogue compétitif"), False)
        self.assertIsNone(mod.direct("Procédure adaptée"))
        result = self.normalize([dict(row("C-dialogue"), procedure="Dialogue compétitif")])[0]
        self.assertIs(result["directAward"], False)

    def test_modified_only_row_retained(self):
        rows = self.normalize([row("C1", "1", 100, 130, mod_date="2024-04-02")])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["contractId"], "C1")
        self.assertEqual(rows[0]["amount"], 100)
        self.assertEqual(rows[0]["history"][1]["amount"], 130)

    def test_differing_initial_fields_become_linked_possible_duplicates(self):
        # Same holder, object and date but a different initial amount: kept as two
        # linked records, flagged as possibly one contract; no value chosen or summed.
        records = [row("C2", amount=100), row("C2", "1", amount=200, mod_amount=250, mod_date="2024-04-02")]
        result = self.normalize(records)
        self.assertEqual(sorted(r["amount"] for r in result), [100, 200])
        ids = [r["id"] for r in result]
        self.assertEqual(len(set(ids)), 2)
        for r in result:
            self.assertEqual(r["procedureGroup"]["members"], ids)
            self.assertEqual(r["possibleDuplicateOf"], [i for i in ids if i != r["id"]])
            self.assertEqual(r["initialConflicts"], [])
            self.assertEqual(len(r["sourceRowVariants"]), 1)
        self.assertEqual([len(r["history"]) for r in sorted(result, key=lambda r: r["amount"])], [1, 2])

    def test_unrelated_contracts_sharing_id_are_not_flagged_duplicates(self):
        records = [row("C5"), dict(row("C5", amount=300), objet="autre", titulaire_id_1="98765432100011")]
        result = self.normalize(records)
        self.assertEqual(len(result), 2)
        self.assertTrue(all("possibleDuplicateOf" not in r for r in result))
        self.assertEqual({r["procedureGroup"]["kind"] for r in result}, {"shared-identifier"})

    def test_joint_contract_rows_merge_holders(self):
        joint = dict(row("C6"), typegroupementoperateurs="Conjoint")
        other = dict(joint, titulaire_id_1="98765432100011")
        [result] = self.normalize([joint, other])
        self.assertEqual([s["id"] for s in result["supplierIds"]], ["12345678900011", "98765432100011"])
        self.assertEqual(result["initialConflicts"], [])
        self.assertNotIn("procedureGroup", result)
        # Without a declared joint grouping the same rows are two contracts.
        self.assertEqual(len(self.normalize([row("C7"), dict(row("C7"), titulaire_id_1="98765432100011")])), 2)

    def test_identical_rows_deduplicated(self):
        result = self.normalize([row("C3"), row("C3")])
        self.assertEqual(len(result), 1)
        self.assertEqual(len(result[0]["sourceRowVariants"]), 1)

    def test_modification_conflict_is_explicit(self):
        records = [row("C4", "1", mod_amount=130, mod_date="2024-04-02"),
                   row("C4", "1", mod_amount=140, mod_date="2024-04-02")]
        conflicts = self.normalize(records)[0]["modificationConflicts"]
        self.assertEqual(conflicts, [{"id": "1", "fields": ["amount"]}])


if __name__ == "__main__":
    unittest.main()
