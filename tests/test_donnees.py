"""Contrôles de cohérence des données publiées dans data/.

Lancer : python -m unittest discover tests
"""
import csv, unittest
from collections import defaultdict


def lire(nom):
    with open(f"data/{nom}", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class TestControlesCroises(unittest.TestCase):
    def test_tous_les_controles_croises_passent(self):
        lignes = lire("controles.csv")
        self.assertGreater(len(lignes), 100)
        echecs = [l for l in lignes if l["ok"] != "1" and l["bloquant"] == "1"]
        self.assertEqual(echecs, [], "contrôles en échec : voir data/controles.csv")

    def test_chaque_brochure_a_ses_controles(self):
        types = {}
        for l in lire("controles.csv"):
            types.setdefault(l["brochure"], set()).add(l["controle"].split(" ")[0])
        for b, t in types.items():
            for attendu in ("charges", "revenus", "nature", "effectifs", "investissements,", "annexe"):
                self.assertIn(attendu, t, f"brochure {b} : contrôle « {attendu} » manquant")


class TestAnnexes(unittest.TestCase):
    def test_six_institutions_chaque_annee(self):
        par_annee = {}
        for l in lire("annexes_totaux.csv"):
            par_annee.setdefault((l["type"], l["annee"]), set()).add(l["institution"])
        for k, v in par_annee.items():
            self.assertEqual(v, {"CHUV", "UNIL", "HEP", "HEIG-VD", "ECAL", "HESAV"}, k)


class TestRapprochement(unittest.TestCase):
    def test_chaque_serie_retombe_sur_le_resultat_officiel(self):
        lignes = lire("lignes_large.csv")
        series = [c for c in lignes[0] if c.startswith(("budget_", "comptes_"))]
        officiel = {f"{r['type']}_{r['annee']}": float(r["resultat_officiel"]) for r in lire("resultats.csv")}
        for s in series:
            res = sum(float(l[s]) * (1 if l["type"] == "revenu" else -1) for l in lignes)
            self.assertAlmostEqual(res, officiel[s], delta=2, msg=f"{s} : {res:,.0f} au lieu de {officiel[s]:,.0f}")

    def test_format_long_et_large_concordent(self):
        large = defaultdict(float)
        for l in lire("lignes_large.csv"):
            for c, v in l.items():
                if c.startswith(("budget_", "comptes_")): large[c] += float(v)
        long_ = defaultdict(float)
        for l in lire("lignes.csv"):
            long_[f"{l['serie']}_{l['annee']}"] += float(l["montant"])
        for k in large:
            self.assertAlmostEqual(large[k], long_[k], delta=1, msg=k)

    def test_chaque_service_a_un_departement(self):
        for s in lire("services.csv"):
            self.assertTrue(s["departement"], s["service"])

    def test_pas_de_doublon(self):
        cles = [(l["service"], l["rubrique"]) for l in lire("lignes_large.csv")]
        self.assertEqual(len(cles), len(set(cles)))


class TestAmendements2027(unittest.TestCase):
    """Annexe 1 du communiqué du 7 octobre 2026 (initiative des 12 %)."""

    @classmethod
    def setUpClass(cls):
        cls.a = lire("amendements_2027.csv")

    def test_totaux_officiels(self):
        self.assertEqual(sum(int(r["mesure"]) for r in self.a), 100_453_200)
        self.assertEqual(sum(int(r["recettes_bns_extraordinaire"]) for r in self.a), -100_453_200)

    def test_descriptions_et_libelles(self):
        for r in self.a:
            self.assertTrue(r["description"].strip(), r)
            self.assertLessEqual(len(r["service_publie"]), 25, r["service_publie"])

    def test_compensation_complete(self):
        self.assertEqual(sum(int(r["effet_sur_resultat"]) for r in self.a), 0)

    def test_effet_de_l_initiative(self):
        effet = {r["rubrique"]: int(r["effet_sur_resultat"]) for r in self.a if r["categorie"] == "effet de l'initiative"}
        self.assertEqual(effet, {"4000": -189_000_000, "4001": -83_000_000})

    def test_numeros_complets_et_ordonnes(self):
        nums = [int(r["amendement"]) for r in self.a]
        self.assertEqual(nums, sorted(nums))
        self.assertEqual(set(nums), set(range(1, 60)))

    def test_rattachement_aux_lignes_du_projet(self):
        projet = {(l["service"], l["rubrique"]): float(l["budget_2027"]) for l in lire("lignes_large.csv")}
        for r in self.a:
            if r["rattachement"] == "ligne du projet 2027":
                k = (r["service"], r["rubrique"])
                self.assertIn(k, projet)
                self.assertAlmostEqual(float(r["budget_2027_projet"]), projet[k], delta=1)
                self.assertGreaterEqual(float(r["budget_2027_amende"]), 0, k)

    def test_lignes_non_rattachees_connues(self):
        autres = sorted((r["amendement"], r["service"], r["rubrique"]) for r in self.a if r["rattachement"] != "ligne du projet 2027")
        # Mesures transversales centralisées à la Chancellerie, et part du CHUV (pas de service 038 dans les brochures)
        self.assertEqual(autres, [("2", "050", "3010"), ("2", "050", "3634"), ("3", "050", "3110"),
                                  ("40", "038", "3634"), ("5", "050", "3132"), ("6", "050", "3030")])


if __name__ == "__main__":
    unittest.main()
