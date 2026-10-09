# Méthodologie

## Source et extraction

Chaque brochure budgétaire de l'État de Vaud contient, pour chaque service, toutes les rubriques budgétaires avec trois colonnes : le budget de l'année N, le budget de l'année N-1 et les comptes de l'année N-2. Le texte est extrait avec `pdftotext -layout`, puis lu par `pipeline/parse_brochure.py`.

Particularités de mise en page prises en compte :

- Les zéros sont imprimés `±±` (brochures 2026 et 2027) ou `––` (brochures plus anciennes) ; ils sont convertis en 0.
- Les pages « Renseignements complémentaires » sont lues séparément : elles donnent les commentaires et les effectifs.
- Les pages des départements sont repérées par leur en-tête, ce qui rend l'extraction indépendante du nombre de pages.

**Contrôles par brochure** (résultats dans `data/controles.csv`, 185 contrôles, tous rejoués par les tests) :

| Contrôle | Comparé à |
|---|---|
| Somme des lignes de chaque service | Récapitulation du département |
| Total des charges et des revenus | Récapitulation générale |
| Total par nature (30, 31, 36, 40…) | Tableau « Charges et revenus d'après leur nature » |
| Somme des effectifs des services | Ligne « Total Etat » du tableau des effectifs |
| Dépenses, recettes et dépenses nettes d'investissement | Ligne « Total du budget de l'Etat » |

Une brochure qui échoue à l'un de ces contrôles bloque le pipeline.

## Construction des séries

Une série est soit un budget (B), soit des comptes (C) d'une année donnée.

| Série | Source retenue |
|---|---|
| Budget N | colonne « Budget N » de la brochure N |
| Budget de l'année la plus ancienne | colonne « Budget N-1 » de la première brochure |
| Comptes N-2 | colonne « Comptes N-2 » de la brochure N |

La colonne « Budget N-1 » des brochures suivantes n'est pas utilisée en général : elle est parfois retraitée (montants déplacés d'un service à un autre après une réorganisation), et la mélanger avec la version d'origine créerait des doublons. Exception : les opérations extraordinaires (natures 38 et 48), utilisées depuis la brochure suivante quand la brochure N ne les détaille pas.

### Statut des budgets

Certaines brochures sont des **projets du Conseil d'État** et non des budgets adoptés par le Grand Conseil (2024 et 2027, voir `pipeline/config.json`). Quand la brochure de l'année suivante existe, le projet est remplacé par la colonne « Budget N-1 » de cette brochure, qui reflète le budget adopté. C'est le cas pour 2024. Le budget 2027 reste un projet tant que la brochure 2028 n'est pas disponible.

Exemple de différence : le projet 2024 comptait 363 millions de prélèvement sur la fortune dans les revenus ordinaires du service 053 (rubrique 4309) ; le budget adopté les présente en revenus extraordinaires.

### Retraitements entre brochures

Le budget d'une année apparaît deux fois : dans sa propre brochure, puis dans la colonne « Budget N-1 » de la suivante. Les différences entre les deux versions (amendements, réorganisations, changements de présentation) sont listées dans `data/retraitements.csv`. Elles ne sont pas des erreurs d'extraction : les totaux de chaque version sont contrôlés séparément.

## Opérations extraordinaires

Les prélèvements sur la fortune et les attributions aux réserves (préfinancements) sont des opérations extraordinaires. Selon les années, la brochure les détaille ligne par ligne (dans le service 053) ou seulement en total dans le compte de résultat.

Quand une série ne se rapproche pas du résultat officiel parce que ces opérations manquent, leur total est ajouté sous forme de lignes synthétiques :

- `053|4800` Revenus extraordinaires (total du compte de résultat)
- `053|3800` Charges extraordinaires (total du compte de résultat)

Elles sont marquées `ligne_synthetique = 1` dans `lignes_large.csv`. Le tableau de bord exclut par défaut toutes les opérations extraordinaires, pour que les comparaisons entre années restent cohérentes.

**Contrôle** : pour chaque série, revenus moins charges (opérations extraordinaires comprises) doit égaler le résultat officiel de l'exercice, à 2 francs près (arrondis des comptes).

## Départements et services

Les codes de service sont stables d'une année à l'autre, mais les départements ont été réorganisés (2022, 2026). Tous les services sont rattachés au département qu'ils occupent dans la brochure la plus récente. Les services qui ont disparu sont rattachés manuellement dans `pipeline/config.json`.

Limite : un code de service stable ne garantit pas un contenu stable. Des tâches passent parfois d'un service à l'autre (par exemple, création du Service cantonal de l'accueil de jour des enfants en 2025). Les variations brutales sont signalées dans le tableau de bord.

## Détection des sauts

Une ligne est signalée « à vérifier » quand, entre deux budgets successifs ou deux comptes successifs, son montant :

- apparaît (passe de 0 à un montant) ou disparaît,
- est multiplié ou divisé par plus de 3, ou change de signe,

et que la variation dépasse 500'000 francs. Ces sauts viennent souvent d'une réorganisation ou d'une écriture comptable plutôt que d'une décision politique.

## Comparaisons

| Comparaison | Qualification |
|---|---|
| Deux budgets ou deux comptes successifs | Comparaison standard |
| Budget et comptes de la même année | Prévision vs réalisé |
| Même type, années éloignées | Écart de plusieurs années : montants non corrigés de l'inflation ni de la démographie |
| Budget et comptes d'années différentes | À interpréter avec prudence |

## Bénéficiaires des transferts

Le plan comptable MCH2 code le type de bénéficiaire dans le dernier chiffre des rubriques 360x (parts de revenus), 361x (dédommagements), 362x (péréquation) et 363x (subventions) : 0 Confédération, 1 cantons et concordats, 2 communes, 3 assurances sociales publiques, 4 entreprises publiques, 5 entreprises privées, 6 organisations privées à but non lucratif, 7 ménages, 8 étranger. Les rubriques 366x (amortissements de subventions d'investissement) et 37x (subventions fédérales redistribuées) sont classées à part. Les subventions nommées proviennent des commentaires chiffrés des brochures.

## Annexes des institutions

Les comptes d'exploitation du CHUV, de l'UNIL, de la HEP, de la HEIG-VD, de l'ECAL et de HESAV sont extraits des annexes (`pipeline/annexes.py`). Les totaux d'exploitation et le résultat sont repris tels que publiés. Le détail des lignes est contrôlé contre ces totaux : 46 institutions-années sur 48 se rapprochent dans toutes les colonnes ; les écarts restants (100 fr. pour le CHUV 2024, 29'640 fr. pour la HEP 2026) sont signalés comme avertissements dans `data/controles.csv`. Le dashboard n'affiche que le détail de la brochure la plus récente dont le contrôle est complet.

## Francs constants et par habitant

Inflation : renchérissement annuel moyen de l'IPC (OFS). Population : population résidante permanente au 31 décembre (Statistique Vaud). Les années sans chiffre officiel utilisent des hypothèses déclarées dans `pipeline/indicateurs.json` (inflation nulle, population +1 %). La décomposition de la hausse des charges est multiplicative : (1 + inflation) × (1 + population) × (1 + hausse réelle par habitant) = 1 + hausse nominale.

## Suivi des investissements

Chaque objet d'investissement garde son numéro (I.xxxxxx.xx) d'un budget à l'autre. Le suivi additionne les dépenses nettes inscrites à chaque budget. Il montre combien de fois un objet a été inscrit, pas ce qui a été réellement dépensé : les comptes d'investissement ne figurent pas dans les brochures.

## Limites connues

- Montants nominaux, non corrigés de l'inflation ni de la croissance de la population.
- Les annexes (UNIL, HEP, HES, CHUV) ne sont pas intégrées ; ces institutions apparaissent comme des subventions.
- Les comptes contiennent des écritures non budgétées (réévaluations, pertes sur créances) qui expliquent une partie des écarts entre budget et comptes.
- Les textes de lecture de l'onglet Analyses citent parfois des années précises ; ils doivent être relus lors de l'ajout d'une brochure.
