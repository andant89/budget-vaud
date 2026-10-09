"""Extraction des annexes des brochures : UNIL, HEP, HEIG-VD, ECAL, HESAV, CHUV.

Chaque institution présente son propre compte de résultat (budget N, budget N-1, comptes N-2).
On extrait :
- les totaux officiels (charges et revenus d'exploitation, résultat de l'exercice),
- le détail des lignes d'exploitation, retenu seulement si sa somme égale le total officiel.
"""
import re

INSTITUTIONS = [
    ("CHUV", r"CHUV|Centre hospitalier universitaire|sant[ée] et de l.action sociale"),
    ("HESAV", r"Haute [EÉée]cole de Sant[ée]"),
    ("ECAL", r"ECAL|art et de design"),
    ("HEIG-VD", r"ing[ée]nierie et de gestion|HEIG"),
    ("HEP", r"Haute [EÉée]cole p[ée]dagogique"),
    ("UNIL", r"Universit[ée] de Lausanne|UNIL"),
]
NOMS = {"UNIL": "Université de Lausanne", "HEP": "Haute école pédagogique", "HEIG-VD": "Haute école d'ingénierie et de gestion",
        "ECAL": "École cantonale d'art de Lausanne", "HESAV": "Haute école de santé Vaud", "CHUV": "Centre hospitalier universitaire vaudois"}
TOK = r"-?[\d'±]+(?:\.[\d±]+)?|--|-"
NUMTAIL = re.compile(r"^(?P<lab>.*?\S)?(?:\.{2,}|\s{2,})\s*(?:\((?P<note>\d+)\)\s+)?(?P<nums>(?:(?:%s)\s+){1,3}(?:%s))\s*$" % (TOK, TOK))


def num(t):
    t = t.replace("±±", "00").replace("±", "0").replace("'", "")
    return 0.0 if t in ("--", "-", "") else float(t)


def head(p):
    return next((l.strip() for l in p.splitlines() if l.strip()), "")


def parse_annexes(pages):
    start = None
    for i, p in enumerate(pages):
        if head(p).startswith("Intérêts de la dette"):
            start = i + 1
    if start is None:
        return {}
    while start < len(pages) and not head(pages[start]).startswith("Département"):
        start += 1  # saute les pages intercalées (mesures d'économie, etc.)
    blocks, cur = {}, "UNIL"
    for p in pages[start:]:
        top = "\n".join(p.splitlines()[:12])
        for code, rx in INSTITUTIONS:
            if re.search(rx, top):
                cur = code; break
        if "Renseignements complémentaires" in top:
            continue  # pages de commentaires : pas de montants du compte de résultat
        blocks.setdefault(cur, []).append(p)
    out = {}
    for code, ps in blocks.items():
        out[code] = parse_institution("\n".join(ps))
    return out


def _cols(raw, nums_str):
    """Positions de fin de chaque montant dans la ligne brute."""
    start = raw.rfind(nums_str.strip().split()[0]) if nums_str.strip() else -1
    ends = []
    for m in re.finditer(TOK, raw[start:] if start >= 0 else raw):
        ends.append((start if start >= 0 else 0) + m.end())
    return ends


def parse_institution(txt):
    lines = txt.split("\n")
    # 1er passage : positions des colonnes, par section, à partir des lignes complètes (3 montants)
    import statistics
    pos = {"C": {"N": [], "N1": [], "C2": []}, "R": {"N": [], "N1": [], "C2": []}}
    sec = "C"
    for raw in lines:
        s0 = raw.strip(); low = s0.lower()
        if re.match(r"^revenus d'exploitation$", low) or low.startswith("total des charges d'exploitation"):
            sec = "R"
        if low.startswith("total des revenus d'exploitation"):
            sec = "X"
        mm = NUMTAIL.match(s0)
        if sec in pos and mm and len(re.findall(TOK, mm.group("nums"))) == 3:
            e = _cols(raw, mm.group("nums"))
            if len(e) == 3:
                for k, v in zip(("N", "N1", "C2"), e): pos[sec][k].append(v)
    cols = {sc: {k: statistics.median(v) for k, v in d.items() if v} for sc, d in pos.items()}

    def assign(raw, nums_str, vals, sc):
        col = cols.get(sc) if len(cols.get(sc, {})) == 3 else cols.get("C")
        if len(vals) >= 3 or not col or len(col) < 3:
            return (vals + [0.0, 0.0, 0.0])[:3]
        out = [0.0, 0.0, 0.0]
        for e, v in zip(_cols(raw, nums_str), vals):
            d = {k: abs(e - col[k]) for k in ("N", "N1", "C2")}
            out[{"N": 0, "N1": 1, "C2": 2}[min(d, key=d.get)]] = v
        return out

    sec, group = "C", None
    gsum, gn = [0.0, 0.0, 0.0], 0
    det, tot = [], {}
    pend = None
    for raw in lines:
        s = raw.strip()
        if not s:
            continue
        low = s.lower()
        m = re.match(r"^(\d{2})\s{2,}(\D.*)$", s)
        if m and not re.search(r"\d'\d{3}", s):
            group = re.sub(r"\.+$", "", m.group(2)).strip().lower(); gsum = [0.0, 0.0, 0.0]; gn = 0; continue
        if re.match(r"^(charges d'exploitation|r[ée]sultat d'exploitation)$", low):
            sec = "C"; continue
        if re.match(r"^revenus d'exploitation$", low):
            sec = "R"; continue
        rawline = raw
        if pend and re.fullmatch(r"(?:(?:%s)\s+){0,3}(?:%s)" % (TOK, TOK), s):
            mm = NUMTAIL.match(pend + "  " + s); lab_prefix = pend; pend = None
        else:
            mm = NUMTAIL.match(s); lab_prefix = None
        if not mm:
            if re.match(r"^\d{3,4}\s+\S", s) or (pend and not re.search(r"\d'\d{3}", s)):
                pend = (pend + " " + s) if pend else s
            continue
        lab = (mm.group("lab") or "").strip()
        if pend:
            lab = (pend + " " + lab).strip(); pend = None
        raw_vals = [num(x) for x in re.findall(TOK, mm.group("nums"))]
        vals = assign(rawline, mm.group("nums"), raw_vals, sec if sec in ("C", "R") else "R")
        lab_clean = re.sub(r"\.{2,}.*$", "", lab).strip()
        l2 = lab_clean.lower()
        if l2.startswith("total des charges d'exploitation"):
            tot["charges"] = vals; sec = "R"; continue
        if l2.startswith("total des revenus d'exploitation"):
            tot["revenus"] = vals; sec = "X"; continue
        if l2.startswith("resultat de l'exercice") or l2.startswith("résultat de l'exercice"):
            tot["resultat"] = vals; continue
        if sec not in ("C", "R") or l2.startswith(("total", "resultat", "résultat")):
            continue
        if len(raw_vals) < 2 or re.match(r"^(\d{3,4}\s+)?\d{1,2}\.\s", lab_clean):
            continue  # commentaires des notes (montant isolé, éléments numérotés)
        if group and l2.rstrip(" .") == group:
            continue  # sous-total d'un groupe (présentation UNIL)
        if gn and all(abs(vals[k] - gsum[k]) < 2 for k in range(3)):
            continue  # sous-total égal à la somme des lignes du groupe
        gsum = [gsum[k] + vals[k] for k in range(3)]; gn += 1
        mcode = re.match(r"^(\d{3,4})\s+(.*)$", lab_clean)
        rub, libelle = (mcode.group(1), mcode.group(2)) if mcode else ("", lab_clean)
        det.append([sec, rub, libelle, vals[0], vals[1], vals[2]])
    res = {"totaux": tot, "lignes": det, "detail_ok": False}
    if "charges" in tot and "revenus" in tot:
        sc = [sum(d[3 + k] for d in det if d[0] == "C") for k in range(3)]
        sr = [sum(d[3 + k] for d in det if d[0] == "R") for k in range(3)]
        res["somme_detail"] = [sc, sr]
        res["colonnes_ok"] = [abs(sc[k] - tot["charges"][k]) < 5 and abs(sr[k] - tot["revenus"][k]) < 5 for k in range(3)]
        res["detail_ok"] = all(res["colonnes_ok"])
    return res
