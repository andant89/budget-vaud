"""Fusionne les brochures extraites en une série pluriannuelle et exporte les données.

Entrée : build/brochures/AAAA.json (produits par parse_brochure.py) et pipeline/config.json
Sortie : data/*.csv (données ouvertes) et site/data.json (données du dashboard)

Règles principales (détaillées dans docs/methodologie.md) :
- Budget N : pris dans la brochure N (colonne « Budget N »).
- Budget N-1 : utilisé seulement pour l'année la plus ancienne et pour les opérations
  extraordinaires (natures 38 et 48) que la brochure N ne détaille pas.
- Comptes N-2 : pris dans la brochure N (colonne « Comptes N-2 »).
- Si une série ne se rapproche pas du résultat officiel parce que les opérations
  extraordinaires ne figurent pas dans les lignes, leur total est ajouté sous forme
  de lignes synthétiques 053|3800 et 053|4800.
- Les services sont classés dans les départements de la brochure la plus récente.
"""
import csv, glob, json, os, re, sys

NUM = r"-?[\d'±]+(?:\.[\d±]{2})?"


def n(x):
    return float(x.replace("'", "").replace("±±", "00"))


def parse_comment(lines):
    """Sépare un commentaire de brochure en éléments chiffrés et en texte libre."""
    items, text, buf = [], [], ""
    for l in lines:
        m = re.match(r"^(.*?)\s{2,}(%s)\s+(%s)\s*$" % (NUM, NUM), l)
        if m:
            lab = (buf + " " + m.group(1)).strip(); buf = ""
            if lab:
                items.append([re.sub(r"^\d+\.\s*", "", lab), n(m.group(2)), n(m.group(3))])
            continue
        if re.match(r"^\s*(%s)\s+(%s)\s*$" % (NUM, NUM), l):
            buf = ""; continue
        if re.match(r"^\d+\.\s", l) or buf:
            buf = (buf + " " + l).strip()
        else:
            text.append(l)
    if buf:
        text.append(buf)
    return items, " ".join(text).strip()


def main():
    cfg = json.load(open("pipeline/config.json"))
    A = {int(os.path.basename(p)[:4]): json.load(open(p)) for p in glob.glob("build/brochures/*.json")}
    if not A:
        sys.exit("Aucune brochure dans build/brochures/. Lancer d'abord parse_brochure.py.")
    YEARS = sorted(A)
    first, last = YEARS[0], YEARS[-1]
    YB = list(range(first - 1 - 2000, last + 1 - 2000))
    YC = [y - 2 - 2000 for y in YEARS]
    SER = [f"B{y}" for y in YB] + [f"C{y}" for y in YC]
    SI = {s: i for i, s in enumerate(SER)}

    vals, labels, prio = {}, {}, {}

    def put(key, ser, v, p):
        a = vals.setdefault(key, [0.0] * len(SER)); q = prio.setdefault(key, [9] * len(SER))
        if p < q[SI[ser]]:
            a[SI[ser]] = v; q[SI[ser]] = p

    # Un budget publié comme projet est remplacé par sa version adoptée lorsque la brochure
    # suivante est disponible (colonne « Budget N-1 », qui reflète le budget voté).
    projets = set(cfg["budgets_projets"])
    remplaces = {y for y in projets if y + 1 in A}
    for y in YEARS:
        N = y % 100
        for svc, rub, lab, b, b1, c in A[y]["lines"]:
            k = f"{svc}|{rub}"; labels.setdefault(k, lab); labels[k] = lab
            if y not in remplaces:
                put(k, f"B{N}", b, 0)
            put(k, f"C{N-2}", c, 0)
            if (y - 1) in remplaces:
                put(k, f"B{N-1}", b1, 0)
            elif y == first or rub[:2] in ("38", "48"):
                put(k, f"B{N-1}", b1, 1)

    # résultats officiels et opérations extraordinaires (compte de résultat)
    res, rex, cex = {}, {s: 0 for s in SER}, {s: 0 for s in SER}
    for y in YEARS:
        N = y % 100
        crb, crc = A[y]["crb"], A[y]["crc"]
        if y not in remplaces:
            res[f"B{N}"] = crb["res"][0]
            if crb.get("rex"): rex[f"B{N}"] = crb["rex"][0]
            if crb.get("cex"): cex[f"B{N}"] = crb["cex"][0]
        res[f"C{N-2}"] = crc["res"][0]
        if y == first or (y - 1) in remplaces:
            res[f"B{N-1}"] = crb["res"][1]
            if crb.get("rex"): rex[f"B{N-1}"] = crb["rex"][1]
            if crb.get("cex"): cex[f"B{N-1}"] = crb["cex"][1]
        if crc.get("rex"): rex[f"C{N-2}"] = crc["rex"][0]
        if crc.get("cex"): cex[f"C{N-2}"] = crc["cex"][0]

    def balance(s):
        i = SI[s]; C = R = 0.0
        for k, a in vals.items():
            if k.split("|")[1][0] == "3": C += a[i]
            else: R += a[i]
        return R - C

    synth = []
    for s in SER:
        if abs(balance(s) - res[s]) > 2:
            i = SI[s]
            for code, lab, amount in (("053|4800", "Revenus extraordinaires (total du compte de résultat)", rex[s]),
                                      ("053|3800", "Charges extraordinaires (total du compte de résultat)", cex[s])):
                if amount:
                    labels[code] = lab; vals.setdefault(code, [0.0] * len(SER))[i] += amount
            synth.append(s)
    controles = []
    for s in SER:
        diff = balance(s) - res[s]
        controles.append([s, round(balance(s), 2), res[s], round(diff, 2), abs(diff) < 2])
        fm = lambda x: f"{x:,.0f}".replace(",", "'")
        print(f"{s} : résultat recalculé {fm(balance(s))}, officiel {fm(res[s])}, écart {fm(diff)}")
    if not all(c[4] for c in controles):
        sys.exit("Au moins une série ne se rapproche pas du résultat officiel.")

    # services, classés selon les départements de la brochure la plus récente
    svc = {}
    for y in YEARS:
        for c, s in A[y]["services"].items():
            prev = svc.get(c)
            svc[c] = {"n": s["name"].replace("’", "'"), "d": s["dept"] if y == last else (prev or {}).get("d"),
                      "y0": (prev or {}).get("y0", y), "y1": y}
    for c, s in svc.items():
        if s["d"] is None:
            if c not in cfg["services_disparus"]:
                sys.exit(f"Service {c} absent de la dernière brochure : l'ajouter à services_disparus dans pipeline/config.json")
            s["d"] = cfg["services_disparus"][c]["departement"]

    etp = {}
    for y in YEARS:
        for c, v in A[y]["etp"].items():
            e = etp.setdefault(c, {}); e[y] = v[0]; e.setdefault(y - 1, v[1])
    EY = list(range(first - 1, last + 1))

    cms = {}
    for y in YEARS[::-1]:
        for k, v in A[y]["comments"].items():
            it, tx = parse_comment(v)
            if it or tx: cms.setdefault(k, []).append([y, it, tx])

    sav, meas = {}, {}
    for y in YEARS:
        for s0, title, rub, amt in A[y]["sav"]:
            k = f"{s0}|{rub}"; sav[k] = sav.get(k, 0) + amt
            m = meas.setdefault(s0, {}); t = title or "Autre"; m[t] = m.get(t, 0) + amt
    sav_years = [y for y in YEARS if A[y]["sav"]]

    proj = [f"B{y % 100}" for y in projets - remplaces if f"B{y % 100}" in SI]
    dcodes = [d[0] for d in cfg["departements_actuels"]]; dnames = [d[1] for d in cfg["departements_actuels"]]
    keys = sorted(vals)

    # ---------- exports CSV ----------
    os.makedirs("data", exist_ok=True)
    nat = lambda r: r[:2]
    def serie_info(s):
        typ = "budget" if s[0] == "B" else "comptes"; an = 2000 + int(s[1:])
        statut = ("projet" if s in proj else "adopté") if typ == "budget" else "bouclés"
        return typ, an, statut
    with open("data/lignes_large.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["service", "departement", "rubrique", "nature", "type", "libelle", "extraordinaire", "ligne_synthetique"] + [("budget_" if s[0] == "B" else "comptes_") + str(2000 + int(s[1:])) for s in SER])
        for k in keys:
            s0, rub = k.split("|")
            w.writerow([s0, dcodes[svc[s0]["d"] - 1], rub, nat(rub), "charge" if rub[0] == "3" else "revenu", labels[k],
                        int(nat(rub) in ("38", "48")), int(rub in ("3800", "4800"))] + [round(v, 2) for v in vals[k]])
    with open("data/lignes.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["service", "departement", "rubrique", "nature", "type", "libelle", "serie", "annee", "statut", "montant"])
        for k in keys:
            s0, rub = k.split("|")
            for s in SER:
                v = vals[k][SI[s]]
                if v == 0: continue
                typ, an, st = serie_info(s)
                w.writerow([s0, dcodes[svc[s0]["d"] - 1], rub, nat(rub), "charge" if rub[0] == "3" else "revenu", labels[k], typ, an, st, round(v, 2)])
    with open("data/services.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["service", "nom", "departement", "departement_nom", "premiere_brochure", "derniere_brochure"])
        for c in sorted(svc): w.writerow([c, svc[c]["n"], dcodes[svc[c]["d"] - 1], dnames[svc[c]["d"] - 1], svc[c]["y0"], svc[c]["y1"]])
    with open("data/effectifs.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["service", "annee", "etp"])
        for c in sorted(etp):
            for y in sorted(etp[c]): w.writerow([c, y, etp[c][y]])
    with open("data/investissements.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["annee_budget", "service", "objet", "libelle", "date_decret", "depenses", "recettes", "depenses_nettes"])
        for y in YEARS:
            for r in A[y]["inv"]: w.writerow([y] + r)
    with open("data/mesures_economie.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["annee_budget", "service", "mesure", "rubrique", "montant"])
        for y in YEARS:
            for s0, title, rub, amt in A[y]["sav"]: w.writerow([y, s0, title or "", rub, amt])
    with open("data/resultats.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["type", "annee", "statut", "resultat_officiel", "revenus_extraordinaires", "charges_extraordinaires", "resultat_recalcule", "rapprochement_ok"])
        for s, b, o, d, ok in controles:
            typ, an, st = serie_info(s); w.writerow([typ, an, st, o, rex[s], cex[s], b, int(ok)])
    with open("data/commentaires.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["annee_brochure", "service", "rubrique", "element", "montant_annee", "montant_annee_precedente", "texte"])
        for k in sorted(cms):
            s0, rub = k.split("|")
            for y, it, tx in cms[k]:
                for lab, a, b in it: w.writerow([y, s0, rub, lab, a, b, ""])
                if tx: w.writerow([y, s0, rub, "", "", "", tx])

    # ---------- données du dashboard ----------
    lines = []
    for k in keys:
        s0, rub = k.split("|")
        row = [s0, rub, labels[k].replace("’", "'"), [round(x, 2) if s[0] == "C" else round(x) for x, s in zip(vals[k], SER)]]
        if k in cms: row.append(cms[k][:2])
        lines.append(row)
    out = {"ser": SER, "proj": proj, "dcodes": dcodes, "dnames": dnames,
           "brochures": YEARS, "savYears": sav_years,
           "svcs": [[c, s["n"], s["d"]] for c, s in svc.items()],
           "etpY": EY, "etp": {c: [round(e.get(y, 0), 2) for y in EY] for c, e in etp.items()},
           "lines": lines, "sav": {k: round(v) for k, v in sav.items()},
           "meas": {c: sorted([[t, round(v)] for t, v in m.items()], key=lambda x: -x[1]) for c, m in meas.items()},
           "inv": {str(y): A[y]["inv"] for y in YEARS}, "cr": {"res": res, "rex": rex}}
    os.makedirs("site", exist_ok=True)
    json.dump(out, open("site/data.json", "w"), ensure_ascii=False, separators=(",", ":"))
    # ---------- contrôles croisés par brochure ----------
    rows = []
    def chk(y, nom, calcule, officiel, tol=1):
        ok = officiel is not None and abs(calcule - officiel) <= tol
        rows.append([y, nom, round(calcule, 2), officiel, int(ok)])
    for y in YEARS:
        b = A[y]; o = b["officiel"]
        rec = b["controle"]["recap_officielle"] or [None, None]
        chk(y, "charges = récapitulation générale", b["controle"]["total_charges"], rec[0])
        chk(y, "revenus = récapitulation générale", b["controle"]["total_revenus"], rec[1])
        nat = {}
        for l in b["lines"]: nat[l[1][:2]] = nat.get(l[1][:2], 0) + l[3]
        for code in sorted(o["natures"]):
            chk(y, f"nature {code} = tableau par nature", nat.get(code, 0), o["natures"][code])
        if o["etp_total"]:
            chk(y, "effectifs = Total Etat", sum(v[0] for v in b["etp"].values()), o["etp_total"][0], tol=0.05)
        if o["inv_total"]:
            for k, nom in ((4, "dépenses"), (5, "recettes"), (6, "dépenses nettes")):
                chk(y, f"investissements, {nom} = total du budget", sum(x[k] for x in b["inv"]), o["inv_total"][k - 4])
    with open("data/controles.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["brochure", "controle", "valeur_calculee", "valeur_officielle", "ok"]); w.writerows(rows)
    nko = [r for r in rows if not r[4]]
    print(f"{len(rows)} contrôles croisés, {len(nko)} en échec")
    for r in nko: print("  ÉCHEC", r)

    # ---------- retraitements : budget N-1 vu par la brochure N et par la brochure N-1 ----------
    ret = []
    for y in YEARS[1:]:
        if y - 1 not in A: continue
        def by_svc(lines, col):
            t = {}
            for l in lines:
                if l[1][:2] in ("38", "48"): continue
                k = (l[0], "charges" if l[1][0] == "3" else "revenus"); t[k] = t.get(k, 0) + l[col]
            return t
        orig, rest = by_svc(A[y - 1]["lines"], 3), by_svc(A[y]["lines"], 4)
        for k in sorted(set(orig) | set(rest)):
            a, b2 = orig.get(k, 0), rest.get(k, 0)
            if abs(a - b2) > 1:
                ret.append([y - 1, k[0], svc.get(k[0], {}).get("n", ""), k[1], round(a), round(b2), round(b2 - a)])
    with open("data/retraitements.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["budget", "service", "nom", "type", "selon_sa_brochure", "selon_brochure_suivante", "ecart"])
        w.writerows(ret)
    print(f"{len(ret)} retraitements de budget détectés entre brochures successives (data/retraitements.csv)")
    if nko: sys.exit("Des contrôles croisés ont échoué (voir data/controles.csv).")
    print(f"{len(lines)} lignes, {len(SER)} séries ({SER[0]} à {SER[-1]}), données écrites dans data/ et site/data.json")


if __name__ == "__main__":
    main()
