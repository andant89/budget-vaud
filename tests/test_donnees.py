"""Contrôles de cohérence des données publiées dans data/.

Lancer : python -m unittest discover tests
"""
import csv, unittest
from collections import defaultdict


def lire(nom):
    with open(f"data/{nom}", encoding="utf-8") as f:
        return list(csv.DictReader(f))


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


if __name__ == "__main__":
    unittest.main()
