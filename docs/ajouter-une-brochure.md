# Ajouter une brochure

1. Télécharger la brochure budgétaire sur [vd.ch](https://www.vd.ch) et l'enregistrer sous `sources/pdf/budget-AAAA.pdf` (AAAA = année du budget).
2. Lancer `make all`. Le pipeline extrait le texte dans `sources/txt/`, contrôle les totaux, fusionne toutes les années et régénère `data/` et `site/index.html`.
3. Si le pipeline s'arrête :
   - **« les totaux ne correspondent pas »** : la mise en page a changé. Comparer le texte extrait avec la brochure, page par page, autour du service signalé.
   - **« Service … absent de la dernière brochure »** : un service a disparu. L'ajouter à `services_disparus` dans `pipeline/config.json` avec son département de rattachement.
4. Si les départements ont été réorganisés, mettre à jour `departements_actuels` dans `pipeline/config.json` (dans l'ordre de la brochure la plus récente).
5. Si la brochure est un projet du Conseil d'État, ajouter l'année à `budgets_projets`. Quand le budget adopté est publié, remplacer le PDF et retirer l'année de la liste.
6. Relire les textes de l'onglet Analyses qui citent des années précises (voir `site/template.html`).
7. Mettre à jour la liste des sources dans `sources/README.md`, puis committer `sources/txt/`, `data/` et `site/`.

Les contrôles (`make test`) sont rejoués automatiquement par GitHub à chaque modification.
