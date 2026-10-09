"""Convertit les brochures PDF de sources/pdf/ en texte (sources/txt/).

Nécessite l'outil `pdftotext` (paquet poppler-utils sous Linux, `brew install poppler` sous macOS).
Les fichiers doivent être nommés budget-AAAA.pdf, AAAA étant l'année du budget.
"""
import glob, os, subprocess, sys
os.makedirs("sources/txt", exist_ok=True)
pdfs = sorted(glob.glob("sources/pdf/budget-*.pdf"))
if not pdfs:
    sys.exit("Aucune brochure trouvée dans sources/pdf/ (nommage attendu : budget-AAAA.pdf)")
for pdf in pdfs:
    out = "sources/txt/" + os.path.basename(pdf)[:-4] + ".txt"
    subprocess.run(["pdftotext", "-layout", pdf, out], check=True)
    print("texte extrait :", out)
