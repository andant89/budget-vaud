# Pipeline complet : PDF -> texte -> extraction -> fusion -> site -> tests
# Prérequis : Python 3.9+ et pdftotext (poppler-utils)

PY ?= python3

all: texte extraction fusion site test

texte:
	$(PY) pipeline/extract.py

extraction:
	$(PY) pipeline/parse_brochure.py sources/txt/budget-*.txt

fusion:
	$(PY) pipeline/merge.py

site:
	$(PY) pipeline/build_site.py

test:
	$(PY) -m unittest discover tests

# Reconstruit données et site sans repartir des PDF (texte déjà dans sources/txt)
rebuild: extraction fusion site test

.PHONY: all texte extraction fusion site test rebuild
