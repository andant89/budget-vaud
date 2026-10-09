"""Extrait les données d'une brochure budgétaire de l'État de Vaud.

Entrée : le texte d'une brochure produit par `pdftotext -layout` (voir extract.py).
Sortie : un fichier JSON par brochure dans build/brochures/, avec
  - les départements et services de l'année,
  - chaque ligne budgétaire (budget N, budget N-1, comptes N-2),
  - les commentaires (« renseignements complémentaires »),
  - les effectifs, le budget d'investissement et les mesures d'économie,
  - le compte de résultat (résultat et opérations extraordinaires),
  - le contrôle des totaux contre la récapitulation officielle.

Utilisation : python pipeline/parse_brochure.py sources/txt/budget-2026.txt
Bibliothèque standard uniquement.
"""
import re, json, sys, os
NUM=r"-?[\d'±]+(?:\.[\d±]{2})?|--"
def num(tok):
    tok=tok.replace('±±','00').replace("'",'')
    if tok in ('','--','-'): return 0.0
    return float(tok)
def head(p):
    return next((l.strip() for l in p.splitlines() if l.strip()),'')
def parse_year(path, Y):
    pages=open(path).read().replace('\u2013','±').split('\f')
    # locate sections
    dept_start=[]; recap_i=None; nature_i=None; etp_i=[]; inv_i=[]; sav_i=[]
    prev=None
    for i,p in enumerate(pages):
        h=head(p)
        if i>=4 and recap_i is None:
            if re.fullmatch(r"Budget 20\d\d",h): recap_i=i; continue
            if h and not h.isdigit() and h!=prev and (h.startswith('Département') or h.startswith('Ordre') or h.startswith('Secrétariat')):
                dept_start.append((i,h))
            if h and not h.isdigit(): prev=h
        if h.startswith('Evolution des effectifs'): etp_i.append(i)
        if h.startswith("Budget d'investissement"): inv_i.append(i)
        if h.startswith("Mesures d'économie"): sav_i.append(i)
    depts=[h.replace('¶',"'").replace('’',"'") for _,h in dept_start]
    def dept_of(i):
        d=None
        for k,(a,_) in enumerate(dept_start):
            if i>=a: d=k+1
        return d
    services={}; lines=[]; comments={}
    for pi in range(dept_start[0][0], recap_i):
        p=pages[pi]; d=dept_of(pi); plines=p.splitlines()
        if 'Renseignements complémentaires' in p:
            csvc=None; crub=None
            for L in plines:
                s=L.strip()
                if not s: continue
                m=re.match(r"^\s{3,}(\d{3}) (\S.*)$",L)
                if m and len(L)-len(L.lstrip())<12: csvc=m.group(1); crub=None; continue
                if re.search(r"(Effectif total|Postes fixes) 20",s): continue
                if 'Renseignements complémentaires' in s or s.startswith(('Budget 20','Revenu net','Charge nette','Excédent')): continue
                if re.fullmatch(r"\d{1,3}",s): continue
                if (s.startswith('Département') or s.startswith('Ordre judiciaire') or s.startswith('Secrétariat général du Grand Conseil')) and not csvc: continue
                m=re.match(r"^(\d{4})\s{2,}(.*)$",L)
                if m and csvc: crub=m.group(1); comments.setdefault(f"{csvc}|{crub}",[]).append(m.group(2).strip()); continue
                if csvc and crub: comments[f"{csvc}|{crub}"].append(re.sub(r"\s{2,}","  ",s))
            continue
        cur=None
        for i,L in enumerate(plines):
            m=re.match(r"^(\d{3}) (\S.*?)\s{2,}([-\d'.±][-\d'.±\s]*)$",L)
            if m:
                cur=m.group(1)
                services.setdefault(cur,{"name":m.group(2).strip().replace('¶',"'"),"dept":d})
                continue
            m=re.match(r"^(\d{4}) (\S.*?)\s{2,}([-\d'.±][-\d'.±\s]*)$",L)
            if m:
                if cur is None:
                    # continuation page: service header lines are repeated? find last service on previous pages
                    cur=lastsvc
                nums=[num(x) for x in re.findall(NUM,m.group(3))]
                if len(nums)!=3: print(Y,"WARN nums",pi,L[:90],file=sys.stderr)
                while len(nums)<3: nums.append(0.0)
                lines.append([cur,m.group(1),m.group(2).strip().replace('¶',"'"),nums[0],nums[1],nums[2]])
            elif re.match(r"^\d{4} \S",L):
                print(Y,"WARN unparsed",pi,L[:100],file=sys.stderr)
        if cur: lastsvc=cur
    # recap validation
    txt="\f".join(pages[recap_i-30:recap_i+1])
    recap={}
    for m in re.finditer(r"^(\d{3})   (\S.*?)\s{2,}(-?[\d']+)\s+(-?[\d'±]+|--)\s*$", "\f".join(pages[dept_start[0][0]:recap_i]), re.M):
        recap[m.group(1)]=(num(m.group(3)),num(m.group(4)))
    agg={}
    for l in lines:
        a=agg.setdefault(l[0],[0,0]); a[0 if l[1][0]=='3' else 1]+=l[3]
    bad=[(c,agg.get(c),recap[c]) for c in recap if c in services and (abs(agg.get(c,[0,0])[0]-recap[c][0])>1 or abs(agg.get(c,[0,0])[1]-recap[c][1])>1)]
    gtxt=pages[recap_i]
    m=re.search(r"Totaux\s+([\d']+)\s+([\d']+)",gtxt)
    gt=(num(m.group(1)),num(m.group(2))) if m else None
    tc=sum(v[0] for v in agg.values()); tr=sum(v[1] for v in agg.values())
    # result pages
    def cr(page):
        r={}
        for code,key in [("48","rex"),("38","cex")]:
            mm=re.search(r"^%s\s+\S.*?\s{2,}(%s)\s+(%s)\s*$"%(code,NUM,NUM),page,re.M)
            r[key]=[num(mm.group(1)),num(mm.group(2))] if mm else None
        mm=re.search(r"Résultat de l'exercice.*?\s{2,}(%s)\s+(%s)\s*$"%(NUM,NUM),page,re.M)
        r["res"]=[num(mm.group(1)),num(mm.group(2))] if mm else None
        return r
    crb=cr(pages[2]); crc=cr(pages[3])
    # etp
    etp={}
    for i in etp_i:
        for m in re.finditer(r"^ (\d{3})\s+(\S.*?)\.{2,}\s+([\d'.]+)\s+([\d'.]+)\s+(-?[\d'.]+)\s*$", pages[i], re.M):
            etp[m.group(1)]=[num(m.group(3)),num(m.group(4))]
    # investments
    inv=[]; svc=None
    for i in inv_i:
        for L in pages[i].splitlines():
            m=re.match(r"^(\d{3})\s{5,}(\S.*)$",L)
            if m: svc=m.group(1); continue
            m=re.match(r"^\s+(I\.\d{6}\.\d{2})\s+(.*?)\.{2,}\s+(\S+(?: nouv\S*)?)\s+(.*)$",L)
            if m and svc:
                vals=[num(x) for x in re.findall(NUM,m.group(4))]
                if not vals: continue
                inv.append([svc,m.group(1),m.group(2).strip(),m.group(3),round(vals[0]),round(vals[0]-vals[-1]),round(vals[-1])])
    # savings (only some years)
    sav=[]; svc=None; title=None; lwt=False
    for i in sav_i:
        for L in pages[i].splitlines():
            m=re.match(r"^(\d{3})\s{3,}(\S.*)$",L)
            if m: svc=m.group(1); title=None; lwt=False; continue
            m=re.match(r"^\s{6,}(\d{4})\s+(.*?)\.{2,}\s+(%s)\s+(%s)\s*$"%(NUM,NUM),L)
            if m and svc:
                lwt=False; sav.append([svc,title,m.group(1),num(m.group(3))]); continue
            s=L.strip()
            if svc and s and s[0].islower() and title is None and not lwt: continue
            if svc and s and re.match(r"^\s{6,9}[A-ZÀ-Üa-z]",L) and not re.search(r"\d{3}'?\d*\s*$",s):
                title=(title+" "+s) if lwt and title else s; lwt=True
    cm={}
    for k,v in comments.items(): cm[k]=v
    controle={"total_charges":tc,"total_revenus":tr,"recap_officielle":gt,"services_en_ecart":bad,
              "ok":(not bad) and gt is not None and abs(gt[0]-tc)<1 and abs(gt[1]-tr)<1}
    fm=lambda x:f"{x:,.0f}".replace(",","'")
    print(f"Brochure {Y} : {len(services)} services, {len(lines)} lignes, charges {fm(tc)}, revenus {fm(tr)}, contrôle {'OK' if controle['ok'] else 'ÉCHEC'}")
    return {"controle":controle,"year":Y,"depts":depts,"services":services,"lines":lines,"comments":cm,"etp":etp,"inv":inv,"sav":sav,"crb":crb,"crc":crc,"tot":[tc,tr]}

def main(paths):
    os.makedirs("build/brochures",exist_ok=True)
    ok=True
    for p in paths:
        m=re.search(r"(20\d\d)",os.path.basename(p))
        if not m: sys.exit(f"Année introuvable dans le nom de fichier : {p} (attendu : budget-AAAA.txt)")
        y=int(m.group(1)); r=parse_year(p,y)
        json.dump(r,open(f"build/brochures/{y}.json","w"),ensure_ascii=False)
        if not r["controle"]["ok"]:
            ok=False; print(f"  ATTENTION {y} : les totaux ne correspondent pas à la récapitulation officielle",file=sys.stderr)
    if not ok: sys.exit(1)

if __name__=="__main__":
    main(sys.argv[1:])
