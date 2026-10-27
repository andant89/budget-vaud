"""Extrait la liste des amendements au projet de budget 2027 (initiative des 12 %).

Entrée  : sources/txt/amendements-2027.txt (pdftotext -layout de l'annexe 1 du
          communiqué du Conseil d'État du 7 octobre 2026), data/lignes_large.csv
Sortie  : data/amendements_2027.csv, et la clé « amend » de site/data.json
          (à lancer après merge.py, qui produit lignes_large.csv et data.json)

Le tableau source fusionne verticalement la cellule « N° amendement » quand un
amendement porte sur plusieurs rubriques. pdftotext place alors le numéro soit sur
la ligne du milieu du groupe, soit sur une ligne à part entre deux lignes. Chaque
groupe est donc centré sur son numéro : connaissant le début du groupe, sa fin s'en
déduit. Le script vérifie que ce découpage est cohérent et que les totaux
retombent sur le « Total des amendements » de la brochure.
"""
import csv, json, os, re, sys

SOURCE = "sources/txt/amendements-2027.txt"
SORTIE = "data/amendements_2027.csv"
URL = ("https://www.vd.ch/fileadmin/user_upload/accueil/fichiers_pdf/2026_octobre_actus/"
       "261007_Annexe_1_Liste_des_amendements_pour_compenser_l_intiative_12_.pdf")
COMMUNIQUE = ("https://www.vd.ch/actualites/communiques-de-presse-de-letat-de-vaud/detail/"
              "communique/mise-en-oeuvre-de-linitiative-des-12")
STATUT = "proposé par le Conseil d'État (7 octobre 2026), avant le vote du Grand Conseil"

AMT = r"(?:-|-?\s*\d{1,3}(?:'\d{3})*)"
ROW = re.compile(
    r"^\s*(?:(?P<num>\d{1,2})\s+)?(?P<dnum>\d)\s+(?P<dpt>[A-Z]+)\s+(?P<svc>\d{3})\s+(?P<lib>\S.*?)"
    r"(?:\s{2,}(?P<desc>\S.*?))?\s{2,}(?P<rub>[34]\d{3})\s+(?P<a>%s)\s+(?P<b>%s)\s*$" % (AMT, AMT))
SEUL = re.compile(r"^\s*(\d{1,2})\s*$")
TOTAL = re.compile(r"Total des amendements\s+(%s)\s+(%s)\s*$" % (AMT, AMT))
SUITE = re.compile(r"^\s{40,}(\S.*?)\s*$")


def montant(x):
    x = x.replace("'", "").replace(" ", "")
    return 0 if x == "-" else int(x)


def lire_source():
    """Lignes du tableau, numéros d'amendement avec leur position, total officiel.

    Une description trop longue est coupée par pdftotext : un morceau au-dessus de
    la ligne chiffrée (dont la description est alors vide), la suite en dessous.
    """
    rows, ancres, total, attente, ouverte = [], [], None, [], False
    for i, l in enumerate(open(SOURCE, encoding="utf-8").read().splitlines()):
        m = ROW.match(l)
        if m:
            d = m.groupdict()
            ouverte = not d["desc"]
            d["haut"] = d["bas"] = i
            if attente:
                d["haut"] = attente[0][0]
            d["desc"] = d["desc"] or " ".join(t for _, t in attente)
            attente = []
            rows.append(d)
            if d["num"]:
                ancres.append((i, int(d["num"])))
            continue
        m = SEUL.match(l)
        if m and rows:
            ancres.append((i, int(m.group(1))))
            ouverte = False
            continue
        m = TOTAL.search(l)
        if m:
            total = (montant(m.group(1)), montant(m.group(2)))
            break
        m = SUITE.match(l)
        if m and rows and ouverte:
            rows[-1]["desc"] += " " + m.group(1)
            rows[-1]["bas"] = i
            ouverte = False
        elif m and rows:
            attente.append((i, m.group(1)))
    # Quand le libellé du service n'est suivi que d'une espace, il absorbe la description :
    # on le recoupe à l'aide des libellés vus ailleurs dans le tableau.
    connus = sorted({r["lib"] for r in rows if r["desc"]}, key=len, reverse=True)
    for r in rows:
        if not r["desc"]:
            for lib in connus:
                if r["lib"].startswith(lib + " "):
                    r["lib"], r["desc"] = lib, r["lib"][len(lib) + 1:]
                    break
    return rows, ancres, total


def main():
    rows, ancres, total = lire_source()
    # Chaque groupe est centré verticalement sur son numéro (en lignes de texte) :
    # on retient la fin de groupe dont le centre est le plus proche du numéro.
    nums = [None] * len(rows)
    debut = 0
    for k, (ligne, num) in enumerate(ancres):
        if num != k + 1:
            sys.exit(f"Numéro d'amendement {num} trouvé, {k + 1} attendu")
        suivant = ancres[k + 1][0] if k + 1 < len(ancres) else float("inf")
        fins = [j for j in range(debut, len(rows)) if rows[j]["bas"] >= ligne and rows[j]["haut"] < suivant]
        if k + 1 == len(ancres):
            fins = [len(rows) - 1]
        ecart = lambda j: abs((rows[debut]["haut"] + rows[j]["bas"]) / 2 - ligne)
        fin = min(fins, key=ecart) if fins else None
        if fin is None or ecart(fin) > 1:
            sys.exit(f"Amendement {num} : impossible de délimiter le groupe autour de la ligne {ligne + 1}")
        for j in range(debut, fin + 1):
            nums[j] = num
        debut = fin + 1
    if total is None:
        sys.exit("Ligne « Total des amendements » introuvable")

    # Contexte : lignes du projet de budget 2027 et services connus
    lignes, depts = {}, {}
    for r in csv.DictReader(open("data/lignes_large.csv", encoding="utf-8")):
        lignes[(r["service"], r["rubrique"])] = float(r["budget_2027"] or 0)
        depts[r["service"]] = r["departement"]

    # Effet cumulé de tous les amendements qui touchent une même ligne
    # (hors mesures transversales centralisées à la Chancellerie, qui portent sur tout l'État)
    cumul = {}
    for r in rows:
        k = (r["svc"], r["rub"])
        if r["svc"] == "050" and r["desc"].lower().startswith("mesure transversale"):
            continue
        a, b = montant(r["a"]), montant(r["b"])
        cumul[k] = cumul.get(k, 0) + (-a if r["rub"][0] == "3" else a + b)
    ALIAS = {"OJMP": "OJV-MP"}

    out = []
    for r, num in zip(rows, nums):
        a, b = montant(r["a"]), montant(r["b"])
        rub, svc, desc = r["rub"], r["svc"], re.sub(r"\s+", " ", r["desc"]).strip()
        charge = rub[0] == "3"
        if b:
            categorie = {"4000": "effet de l'initiative", "4001": "effet de l'initiative",
                         "4110": "part BNS supplémentaire", "4898": "prélèvement sur les capitaux propres"}.get(rub, "autre recette")
            effet = b
        else:
            categorie = "mesure transversale" if desc.lower().startswith("mesure transversale") else "mesure départementale"
            effet = a
        projet = lignes.get((svc, rub))
        if svc not in depts:
            ratt = "service absent des données"
        elif svc == "050" and categorie == "mesure transversale":
            ratt = "transversale, imputée à la Chancellerie"
        elif not projet:
            ratt = "ligne absente du projet 2027"
        else:
            ratt = "ligne du projet 2027"
        out.append({
            "amendement": num, "departement_publie": r["dpt"], "departement": depts.get(svc) or ALIAS.get(r["dpt"], r["dpt"]),
            "service": svc, "service_publie": r["lib"].strip(), "rubrique": rub, "nature": rub[:2],
            "type": "charge" if charge else "revenu", "description": desc,
            "mesure": a, "recettes_bns_extraordinaire": b, "effet_sur_resultat": effet,
            "categorie": categorie, "rattachement": ratt,
            "budget_2027_projet": "" if projet is None else round(projet),
            "budget_2027_amende": "" if projet is None or ratt != "ligne du projet 2027" else round(projet + cumul[(svc, rub)]),
            "statut": STATUT,
        })

    sa, sb = sum(o["mesure"] for o in out), sum(o["recettes_bns_extraordinaire"] for o in out)
    if (sa, sb) != total:
        sys.exit(f"Totaux {sa:,} / {sb:,} différents du total officiel {total[0]:,} / {total[1]:,}")
    with open(SORTIE, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader(); w.writerows(out)
    if os.path.exists("site/data.json"):
        data = json.load(open("site/data.json", encoding="utf-8"))
        cles = ["amendement", "departement", "service", "service_publie", "rubrique", "description", "mesure",
                "recettes_bns_extraordinaire", "effet_sur_resultat", "categorie", "rattachement",
                "budget_2027_projet", "budget_2027_amende"]
        data["amend"] = {"annee": 2027, "date": "2026-10-07", "statut": STATUT, "source": URL, "communique": COMMUNIQUE,
                         "total": list(total), "cles": cles, "lignes": [[o[c] for c in cles] for o in out]}
        json.dump(data, open("site/data.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"{len(out)} lignes, {nums[-1]} amendements, mesures {sa:,} = total officiel ; écrit dans {SORTIE}")


if __name__ == "__main__":
    main()
