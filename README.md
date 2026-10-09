# Budget vaudois en données ouvertes

Les budgets et les comptes de l'État de Vaud, ligne par ligne, extraits des brochures budgétaires officielles et rendus lisibles : un tableau de bord interactif et des fichiers CSV réutilisables.

**Couverture actuelle** : budgets 2019 à 2027 et comptes 2018 à 2025, soit 2'543 lignes budgétaires dans 48 services.

> Projet indépendant, sans lien avec l'État de Vaud. Les chiffres proviennent des brochures publiées par le Canton ; en cas de doute, la brochure officielle fait foi.

## Pourquoi

Le Canton publie ses budgets uniquement en PDF, et ne contribue pas à [opendata.swiss](https://opendata.swiss). Ce projet transforme ces brochures en données structurées pour pouvoir chercher une ligne, suivre son évolution sur plusieurs années et comparer le budget voté à ce qui a été réellement dépensé.

## Principe de neutralité

L'outil décrit ce que montrent les chiffres. Il ne dit pas ce qu'il faudrait en conclure, ce qui relève d'un choix politique. Les textes de lecture du tableau de bord s'en tiennent aux montants, aux écarts et aux méthodes de calcul. Toute contribution doit respecter ce principe.

## Contenu

| Dossier | Contenu |
|---|---|
| `site/index.html` | Tableau de bord autonome, à ouvrir dans un navigateur (aussi publié via GitHub Pages) |
| `data/` | Données ouvertes au format CSV (UTF-8, séparateur virgule) |
| `pipeline/` | Scripts d'extraction et de fusion (Python, bibliothèque standard uniquement) |
| `sources/` | Texte extrait de chaque brochure et liste des sources |
| `tests/` | Contrôles automatiques de cohérence |
| `docs/` | Méthodologie et procédure de mise à jour |

### Fichiers de données

| Fichier | Une ligne par | Colonnes principales |
|---|---|---|
| `lignes_large.csv` | ligne budgétaire | service, département, rubrique, nature, libellé, puis une colonne par budget et par exercice de comptes |
| `lignes.csv` | ligne budgétaire et année | même contenu en format long : série (budget ou comptes), année, statut, montant |
| `services.csv` | service | nom, département actuel, première et dernière brochure où il apparaît |
| `effectifs.csv` | service et année | effectif en équivalents plein temps (ETP) |
| `investissements.csv` | objet d'investissement | année du budget, service, numéro d'objet, libellé, date du décret, dépenses, recettes, dépenses nettes |
| `mesures_economie.csv` | mesure et rubrique | mesures d'économie détaillées en annexe (brochure 2026) |
| `commentaires.csv` | élément de commentaire | détail chiffré et texte des « renseignements complémentaires » |
| `resultats.csv` | série | résultat officiel, opérations extraordinaires, résultat recalculé et contrôle |
| `controles.csv` | contrôle | 185 contrôles croisés avec les totaux officiels de chaque brochure |
| `retraitements.csv` | service et budget | différences entre un budget et sa reprise dans la brochure suivante |

Les montants sont en francs, sans arrondi. Les codes de rubrique suivent le modèle comptable harmonisé MCH2 : 3xxx pour les charges, 4xxx pour les revenus ; les deux premiers chiffres donnent la nature (30 personnel, 36 transferts, 40 impôts, etc.).

## Le tableau de bord

- **Aperçu** : chiffres clés, trajectoire pluriannuelle, flux des revenus vers les départements, répartition par nature
- **Explorer** : carte proportionnelle, du département jusqu'à la ligne
- **Recherche** : toutes les lignes, filtrables, y compris dans les commentaires
- **Évolutions** : plus fortes hausses et baisses entre deux années
- **Budget vs comptes** : écarts entre prévision et réalisation
- **Analyses** : dix analyses (effet ciseaux, précision des prévisions, biais systématiques, concentration, personnel, contrôle de qualité…)
- **Fiche service** et **Économies et investissements**

Les comparaisons sont guidées : un badge indique si elle est standard (deux budgets successifs), de type prévision et réalisé, ou à interpréter avec prudence. Les montants qui apparaissent, disparaissent ou varient de plus de trois fois sont signalés « à vérifier ».

## Reconstruire les données

Prérequis : Python 3.9 ou plus récent. Pour repartir des PDF : `pdftotext` (paquet `poppler-utils`).

```sh
make rebuild   # depuis le texte déjà extrait dans sources/txt/
make all       # depuis les PDF placés dans sources/pdf/budget-AAAA.pdf
make test      # contrôles uniquement
```

Pour ajouter une nouvelle brochure, voir [docs/ajouter-une-brochure.md](docs/ajouter-une-brochure.md).

## Fiabilité

Chaque brochure est contrôlée contre ses totaux officiels : récapitulation générale, totaux par nature, effectifs et budget d'investissement (185 contrôles, `data/controles.csv`). Chaque série (budget ou comptes d'une année) se rapproche au franc près du résultat officiel de l'exercice. Ces contrôles sont rejoués automatiquement à chaque modification (`tests/`). Les choix de méthode et leurs limites sont décrits dans [docs/methodologie.md](docs/methodologie.md).

## Licence

Code sous licence MIT (voir `LICENSE`). Les données sont issues de documents publiés par l'État de Vaud ; merci de citer la source : « État de Vaud, brochures budgétaires, mise en forme par le projet Budget vaudois en données ouvertes ».
