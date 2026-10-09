"""Outils de requête sur les données du budget vaudois.

Ces fonctions lisent uniquement les fichiers CSV du dossier data/ et renvoient des
résultats compacts (dictionnaires et listes), prêts à être transmis à une IA.
Elles sont partagées par le serveur MCP (mcp_server.py) et le script ask.py.

Bibliothèque standard uniquement. Les montants sont en francs.
"""
import csv
import os
import unicodedata
from functools import lru_cache

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

NATURES = {"30": "Personnel", "31": "Biens, services et exploitation", "33": "Amortissements", "34": "Charges financières",
           "35": "Attributions aux fonds", "36": "Transferts et subventions", "37": "Subventions à redistribuer",
           "38": "Charges extraordinaires", "39": "Imputations internes", "40": "Impôts", "41": "Patentes et concessions",
           "42": "Taxes et émoluments", "43": "Revenus divers", "44": "Revenus financiers", "45": "Prélèvements sur fonds",
           "46": "Transferts reçus", "47": "Subventions à redistribuer", "48": "Revenus extraordinaires", "49": "Imputations internes"}
BENEF = ["Confédération", "Autres cantons et concordats", "Communes", "Assurances sociales publiques", "Entreprises publiques",
         "Entreprises privées", "Organisations privées à but non lucratif", "Ménages", "Étranger"]
SYNONYMES = {
    "ecole": ["enseignement", "scolar", "dgeo", "eleve", "pedagog"], "hopital": ["hospital", "sante", "chuv", "fhv", "soins"],
    "hopitaux": ["hospital", "sante", "chuv", "fhv"], "police": ["police", "gendarm"], "prison": ["penitentiaire", "detention"],
    "prisons": ["penitentiaire", "detention"], "route": ["route", "routier", "mobilite"], "routes": ["route", "routier", "mobilite"],
    "transport": ["transport", "mobilite", "ferroviaire"], "universite": ["unil", "universit", "enseignement superieur"],
    "social": ["social", "sociale", "insertion", "prestations financieres"], "subside": ["subside", "assurance-maladie", "primes"],
    "subsides": ["subside", "assurance-maladie", "primes"], "creche": ["accueil de jour", "faje", "enfance"],
    "asile": ["asile", "migrant", "refugi", "population"], "refugies": ["refugi", "asile", "migrant"], "impot": ["impot", "fiscal"],
    "impots": ["impot", "fiscal"], "salaire": ["salaire", "personnel"], "salaires": ["salaire", "personnel"],
    "informatique": ["informatique", "numerique"], "culture": ["culture", "culturel", "musee"], "ems": ["ems", "hebergement"],
    "justice": ["judiciaire", "tribunal", "ministere public"], "agriculture": ["agricult", "viticult"], "chomage": ["emploi", "chomage"],
}


def norm(s):
    return "".join(c for c in unicodedata.normalize("NFD", str(s).lower()) if unicodedata.category(c) != "Mn")


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def _read(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as f:
        return list(csv.DictReader(f))


@lru_cache(maxsize=1)
def donnees():
    lignes = _read("lignes_large.csv")
    series = [c for c in lignes[0] if c.startswith(("budget_", "comptes_"))]
    services = {s["service"]: s for s in _read("services.csv")}
    comm = {}
    for c in _read("commentaires.csv"):
        comm.setdefault((c["service"], c["rubrique"]), []).append(c)
    for l in lignes:
        s = services.get(l["service"], {})
        l["service_nom"] = s.get("nom", "")
        l["cle"] = norm(" ".join([l["service"], l["rubrique"], l["libelle"], l["service_nom"], s.get("departement_nom", "")] +
                                 [c["element"] + " " + c["texte"] for c in comm.get((l["service"], l["rubrique"]), [])]))
    return {"lignes": lignes, "series": series, "services": services, "comm": comm,
            "effectifs": _read("effectifs.csv"), "invest": _read("investissements.csv"), "resultats": _read("resultats.csv"),
            "annexes": _read("annexes_totaux.csv"), "mesures": _read("mesures_economie.csv")}


def _serie(annee, type_):
    t = "budget" if str(type_).startswith("b") else "comptes"
    col = f"{t}_{int(annee)}"
    if col not in donnees()["series"]:
        dispo = [c for c in donnees()["series"] if c.startswith(t)]
        raise ValueError(f"Série {col} indisponible. Disponibles : {', '.join(dispo)}")
    return col


def _statut(col):
    t, a = col.split("_")
    for r in donnees()["resultats"]:
        if r["type"] == t and r["annee"] == a:
            return r["statut"]
    return ""


def _ligne_courte(l, cols):
    return {"service": l["service"], "service_nom": l["service_nom"], "departement": l["departement"], "rubrique": l["rubrique"],
            "libelle": l["libelle"], "type": l["type"], **{c: round(_f(l[c])) for c in cols}}


def _ordinaire(l):
    return l["extraordinaire"] != "1"


# ---------------------------------------------------------------- outils
def series_disponibles():
    """Liste des budgets et comptes disponibles, avec leur statut, et rappel des règles de lecture."""
    d = donnees()
    return {"series": [{"serie": c, "statut": _statut(c)} for c in d["series"]],
            "rappel": ("Budget = prévision votée avant l'année ; comptes = réalisé, établis après l'année. "
                       "Un budget 'projet' n'est pas encore voté par le Grand Conseil. Montants en francs courants. "
                       "Les opérations extraordinaires (natures 38 et 48) sont exclues des totaux par défaut.")}


def rechercher_lignes(texte, annee=None, type="budget", nature=None, departement=None, limite=20):
    """Cherche des lignes budgétaires par mots (accepte les mots courants : école, hôpital, police…),
    numéro de rubrique ou nom de service. Renvoie les lignes triées par montant de l'année demandée."""
    d = donnees()
    col = _serie(annee or max(int(c.split("_")[1]) for c in d["series"] if c.startswith("budget")), type)
    termes = [norm(t) for t in str(texte).split() if t.strip()]
    def ok(l):
        return all(any(x in l["cle"] for x in [t] + SYNONYMES.get(t, [])) for t in termes)
    res = [l for l in d["lignes"] if ok(l) and _ordinaire(l) and (not nature or l["nature"] == str(nature))
           and (not departement or l["departement"].lower() == str(departement).lower())]
    res.sort(key=lambda l: -abs(_f(l[col])))
    charges = sum(_f(l[col]) for l in res if l["type"] == "charge")
    revenus = sum(_f(l[col]) for l in res if l["type"] == "revenu")
    elargi = {t: SYNONYMES[t] for t in termes if t in SYNONYMES}
    return {"serie": col, "statut": _statut(col), "nombre_de_lignes": len(res), "total_charges": round(charges), "total_revenus": round(revenus),
            "recherche_elargie": elargi, "lignes": [_ligne_courte(l, [col]) for l in res[:int(limite)]]}


def detail_ligne(service, rubrique):
    """Toute la série d'une ligne (budgets et comptes de toutes les années) et les commentaires des brochures."""
    d = donnees()
    for l in d["lignes"]:
        if l["service"] == str(service).zfill(3) and l["rubrique"] == str(rubrique):
            com = d["comm"].get((l["service"], l["rubrique"]), [])
            return {**_ligne_courte(l, d["series"]), "nature": NATURES.get(l["nature"], l["nature"]),
                    "commentaires": [{"brochure": c["annee_brochure"], "element": c["element"] or None, "texte": c["texte"] or None,
                                      "montant": _f(c["montant_annee"]) if c["montant_annee"] else None,
                                      "montant_annee_precedente": _f(c["montant_annee_precedente"]) if c["montant_annee_precedente"] else None}
                                     for c in com][:40]}
    return {"erreur": f"Ligne {service}|{rubrique} introuvable. Utiliser rechercher_lignes."}


def lister_services(departement=None):
    """Liste des services (code, nom, département). Filtre optionnel par code de département (DSAS, DEF…)."""
    s = donnees()["services"].values()
    return [{"service": x["service"], "nom": x["nom"], "departement": x["departement"], "departement_nom": x["departement_nom"],
             "annees": f"{x['premiere_brochure']}-{x['derniere_brochure']}"}
            for x in s if not departement or x["departement"].lower() == str(departement).lower()]


def fiche_service(service, annee=None):
    """Charges, revenus et effectifs d'un service pour toutes les années, et ses principales lignes."""
    d = donnees()
    code = str(service).zfill(3) if str(service).isdigit() else None
    if not code:
        cand = [s for s in d["services"].values() if norm(service) in norm(s["nom"])]
        if not cand:
            return {"erreur": "Service introuvable. Utiliser lister_services."}
        code = cand[0]["service"]
    s = d["services"].get(code)
    if not s:
        return {"erreur": "Service introuvable. Utiliser lister_services."}
    ls = [l for l in d["lignes"] if l["service"] == code and _ordinaire(l)]
    par_serie = {c: {"charges": round(sum(_f(l[c]) for l in ls if l["type"] == "charge")),
                     "revenus": round(sum(_f(l[c]) for l in ls if l["type"] == "revenu"))} for c in d["series"]}
    col = _serie(annee, "budget") if annee else [c for c in d["series"] if c.startswith("budget")][-1]
    top = sorted([l for l in ls if l["type"] == "charge"], key=lambda l: -_f(l[col]))[:10]
    etp = {e["annee"]: _f(e["etp"]) for e in d["effectifs"] if e["service"] == code}
    return {"service": code, "nom": s["nom"], "departement": s["departement_nom"], "par_serie": par_serie, "effectifs_etp": etp,
            "principales_charges": [_ligne_courte(l, [col]) for l in top], "serie_principales_charges": col}


def totaux(annee, type="budget", par="departement"):
    """Totaux des charges et revenus d'une année, regroupés par 'departement', 'nature' ou 'service'.
    Opérations extraordinaires exclues ; le résultat officiel de l'exercice est rappelé."""
    d = donnees()
    col = _serie(annee, type)
    g = {}
    for l in d["lignes"]:
        if not _ordinaire(l):
            continue
        k = {"departement": l["departement"], "nature": l["nature"] + " " + NATURES.get(l["nature"], ""),
             "service": l["service"] + " " + l["service_nom"]}[par]
        x = g.setdefault(k, {"charges": 0.0, "revenus": 0.0})
        x["charges" if l["type"] == "charge" else "revenus"] += _f(l[col])
    t, a = col.split("_")
    off = next((r for r in d["resultats"] if r["type"] == t and r["annee"] == a), {})
    C = sum(v["charges"] for v in g.values()); R = sum(v["revenus"] for v in g.values())
    return {"serie": col, "statut": _statut(col), "total_charges": round(C), "total_revenus": round(R),
            "resultat_operationnel": round(R - C), "resultat_officiel_de_l_exercice": _f(off.get("resultat_officiel")),
            "revenus_extraordinaires": _f(off.get("revenus_extraordinaires")),
            "groupes": sorted([{"groupe": k, "charges": round(v["charges"]), "revenus": round(v["revenus"])} for k, v in g.items()],
                              key=lambda x: -x["charges"])}


def comparer(annee_a, annee_b, type_a="budget", type_b="budget", niveau="service", sens="charges", departement=None, limite=15):
    """Plus fortes hausses et baisses entre deux séries (par exemple budget 2026 et budget 2027),
    au niveau 'service' ou 'ligne'. Avertit quand la comparaison mélange budget et comptes d'années différentes."""
    d = donnees()
    ca, cb = _serie(annee_a, type_a), _serie(annee_b, type_b)
    typ = "charge" if sens.startswith("c") else "revenu"
    g = {}
    for l in d["lignes"]:
        if not _ordinaire(l) or l["type"] != typ or (departement and l["departement"].lower() != str(departement).lower()):
            continue
        k = (l["service"], l["service_nom"]) if niveau == "service" else (l["service"] + "|" + l["rubrique"], l["libelle"] + " — " + l["service_nom"])
        x = g.setdefault(k, [0.0, 0.0]); x[0] += _f(l[ca]); x[1] += _f(l[cb])
    rows = [{"cle": k[0], "nom": k[1], ca: round(v[0]), cb: round(v[1]), "ecart": round(v[1] - v[0]),
             "variation_pct": round((v[1] - v[0]) / abs(v[0]) * 100, 1) if v[0] else None,
             "a_verifier": (v[0] == 0) != (v[1] == 0) or (v[0] and v[1] and not (1 / 3 < v[1] / v[0] < 3))} for k, v in g.items()]
    hausses = sorted([r for r in rows if r["ecart"] > 0], key=lambda r: -r["ecart"])[:int(limite)]
    baisses = sorted([r for r in rows if r["ecart"] < 0], key=lambda r: r["ecart"])[:int(limite)]
    avert = None
    if ca.split("_")[0] != cb.split("_")[0] and ca.split("_")[1] != cb.split("_")[1]:
        avert = "Budget et comptes d'années différentes : comparaison à interpréter avec prudence."
    return {"de": ca, "a": cb, "statuts": [_statut(ca), _statut(cb)], "avertissement": avert,
            "note": "'a_verifier' = montant qui apparaît, disparaît ou varie de plus de 3 fois : souvent une réorganisation.",
            "hausses": hausses, "baisses": baisses}


def budget_vs_comptes(annee, niveau="total", sens="revenus", limite=15):
    """Écart entre les comptes (réalisé) et le budget (prévu) d'une même année.
    niveau='total' : impôts, revenus, charges, résultat. niveau='service' ou 'ligne' : plus gros écarts."""
    if niveau == "total":
        d = donnees(); b, c = _serie(annee, "budget"), _serie(annee, "comptes")
        f = lambda cond, col: round(sum(_f(l[col]) for l in d["lignes"] if _ordinaire(l) and cond(l)))
        imp = lambda l: l["nature"] == "40"; rev = lambda l: l["type"] == "revenu"; cha = lambda l: l["type"] == "charge"
        res = {r["type"]: _f(r["resultat_officiel"]) for r in d["resultats"] if r["annee"] == str(annee)}
        return {"annee": annee, "impots": {"budget": f(imp, b), "comptes": f(imp, c)}, "revenus": {"budget": f(rev, b), "comptes": f(rev, c)},
                "charges": {"budget": f(cha, b), "comptes": f(cha, c)}, "resultat_officiel": res}
    return comparer(annee, annee, "budget", "comptes", niveau, sens, None, limite)


def beneficiaires(annee, type="budget"):
    """Répartition des transferts (natures 36 et 37) par type de bénéficiaire selon le plan comptable MCH2
    (ménages, communes, entreprises publiques, organisations privées…), avec les 3 principales lignes de chacun."""
    d = donnees(); col = _serie(annee, type); g = {}
    for l in d["lignes"]:
        if not _ordinaire(l) or l["nature"] not in ("36", "37"):
            continue
        r = l["rubrique"]
        if r.startswith("37"): b = "Subventions fédérales redistribuées"
        elif r.startswith("366"): b = "Amortissements de subventions d'investissement"
        elif r[:3] in ("360", "361", "362", "363") and r[3].isdigit() and int(r[3]) < 9: b = BENEF[int(r[3])]
        else: b = "Autres transferts"
        x = g.setdefault(b, {"montant": 0.0, "lignes": []}); x["montant"] += _f(l[col]); x["lignes"].append(l)
    tot = sum(v["montant"] for v in g.values())
    return {"serie": col, "statut": _statut(col), "total_transferts": round(tot),
            "beneficiaires": sorted([{"beneficiaire": k, "montant": round(v["montant"]), "part_pct": round(v["montant"] / tot * 100, 1),
                                      "principales_lignes": [_ligne_courte(l, [col]) for l in sorted(v["lignes"], key=lambda l: -_f(l[col]))[:3]]}
                                     for k, v in g.items()], key=lambda x: -x["montant"])}


def institutions(code=None):
    """Budgets et comptes d'exploitation du CHUV, de l'UNIL, de la HEP, de la HEIG-VD, de l'ECAL et de HESAV (annexes des brochures)."""
    rows = [r for r in donnees()["annexes"] if not code or r["institution"].lower() == str(code).lower()]
    return [{"institution": r["institution"], "nom": r["nom"], "serie": f"{r['type']}_{r['annee']}",
             "charges": _f(r["charges_exploitation"]), "revenus": _f(r["revenus_exploitation"]),
             "resultat": _f(r["resultat_exercice"]) if r["resultat_exercice"] else None} for r in rows]


def investissements(annee=None, texte=None, limite=20):
    """Objets du budget d'investissement (dépenses nettes), filtrables par année de budget et par mot."""
    rows = donnees()["invest"]
    if annee: rows = [r for r in rows if r["annee_budget"] == str(annee)]
    if texte: rows = [r for r in rows if norm(texte) in norm(r["libelle"] + " " + r["objet"])]
    rows = sorted(rows, key=lambda r: -_f(r["depenses_nettes"]))
    return {"nombre": len(rows), "total_depenses_nettes": round(sum(_f(r["depenses_nettes"]) for r in rows)),
            "objets": [{"annee_budget": r["annee_budget"], "service": r["service"], "objet": r["objet"], "libelle": r["libelle"],
                        "decret": r["date_decret"], "depenses_nettes": _f(r["depenses_nettes"])} for r in rows[:int(limite)]]}


def mesures_economie(texte=None):
    """Mesures d'économie détaillées en annexe du budget 2026, regroupées par mesure."""
    g = {}
    for r in donnees()["mesures"]:
        if texte and norm(texte) not in norm(r["mesure"]):
            continue
        k = (r["annee_budget"], r["mesure"]); x = g.setdefault(k, {"montant": 0.0, "services": set()})
        x["montant"] += _f(r["montant"]); x["services"].add(r["service"])
    return sorted([{"budget": k[0], "mesure": k[1], "montant": round(v["montant"]), "services": sorted(v["services"])} for k, v in g.items()],
                  key=lambda x: -x["montant"])[:40]


OUTILS = {
    "series_disponibles": (series_disponibles, {}),
    "rechercher_lignes": (rechercher_lignes, {"texte": ("string", "Mots, numéro de rubrique ou nom de service", True),
                                              "annee": ("integer", "Année (par défaut : dernier budget)", False),
                                              "type": ("string", "'budget' ou 'comptes'", False),
                                              "nature": ("string", "Nature à deux chiffres (30, 36, 40…)", False),
                                              "departement": ("string", "Code de département (DSAS, DEF, DJES…)", False),
                                              "limite": ("integer", "Nombre de lignes renvoyées (défaut 20)", False)}),
    "detail_ligne": (detail_ligne, {"service": ("string", "Code de service à 3 chiffres", True), "rubrique": ("string", "Rubrique à 4 chiffres", True)}),
    "lister_services": (lister_services, {"departement": ("string", "Code de département (facultatif)", False)}),
    "fiche_service": (fiche_service, {"service": ("string", "Code ou nom du service", True), "annee": ("integer", "Année des principales lignes", False)}),
    "totaux": (totaux, {"annee": ("integer", "Année", True), "type": ("string", "'budget' ou 'comptes'", False),
                        "par": ("string", "'departement', 'nature' ou 'service'", False)}),
    "comparer": (comparer, {"annee_a": ("integer", "Première année", True), "annee_b": ("integer", "Seconde année", True),
                            "type_a": ("string", "'budget' ou 'comptes'", False), "type_b": ("string", "'budget' ou 'comptes'", False),
                            "niveau": ("string", "'service' ou 'ligne'", False), "sens": ("string", "'charges' ou 'revenus'", False),
                            "departement": ("string", "Code de département (facultatif)", False), "limite": ("integer", "Nombre de résultats", False)}),
    "budget_vs_comptes": (budget_vs_comptes, {"annee": ("integer", "Année (budget et comptes disponibles)", True),
                                              "niveau": ("string", "'total', 'service' ou 'ligne'", False), "sens": ("string", "'charges' ou 'revenus'", False),
                                              "limite": ("integer", "Nombre de résultats", False)}),
    "beneficiaires": (beneficiaires, {"annee": ("integer", "Année", True), "type": ("string", "'budget' ou 'comptes'", False)}),
    "institutions": (institutions, {"code": ("string", "CHUV, UNIL, HEP, HEIG-VD, ECAL ou HESAV (facultatif)", False)}),
    "investissements": (investissements, {"annee": ("integer", "Année du budget", False), "texte": ("string", "Mot à chercher", False),
                                          "limite": ("integer", "Nombre d'objets", False)}),
    "mesures_economie": (mesures_economie, {"texte": ("string", "Mot à chercher dans l'intitulé (facultatif)", False)}),
}


def schema(nom):
    fn, params = OUTILS[nom]
    props = {k: {"type": t, "description": desc} for k, (t, desc, _) in params.items()}
    req = [k for k, (_, _, r) in params.items() if r]
    return {"name": nom, "description": " ".join(fn.__doc__.split()),
            "inputSchema": {"type": "object", "properties": props, "required": req}}


def appeler(nom, arguments):
    if nom not in OUTILS:
        return {"erreur": f"Outil inconnu : {nom}"}
    fn, params = OUTILS[nom]
    args = {k: v for k, v in (arguments or {}).items() if k in params and v not in (None, "")}
    try:
        return fn(**args)
    except Exception as e:  # message clair renvoyé à l'IA plutôt qu'un plantage
        return {"erreur": str(e)}
