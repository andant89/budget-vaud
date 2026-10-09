"""Assemble le dashboard : site/template.html + site/data.json -> site/index.html.

Le résultat est une page autonome (données incluses) qui fonctionne hors ligne
et sur GitHub Pages. Seules d3 et d3-sankey sont chargées depuis un CDN.
"""
html = open("site/template.html", encoding="utf-8").read()
data = open("site/data.json", encoding="utf-8").read()
assert "/*DATA*/null" in html, "Le gabarit doit contenir le marqueur /*DATA*/null"
page = ('<!doctype html>\n<html lang="fr">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        '<style>body{margin:0;font-size:14px}img{max-width:100%}[hidden]{display:none!important}</style>\n'
        '</head>\n<body>\n' + html.replace("/*DATA*/null", data) + "\n</body>\n</html>\n")
open("site/index.html", "w", encoding="utf-8").write(page)
print("site/index.html généré")
