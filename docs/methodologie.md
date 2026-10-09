# Méthodologie

## Source et extraction

Chaque brochure budgétaire de l'État de Vaud contient, pour chaque service, toutes les rubriques budgétaires avec trois colonnes : le budget de l'année N, le budget de l'année N-1 et les comptes de l'année N-2. Le texte est extrait avec `pdftotext -layout`, puis lu par `pipeline/parse_brochure.py`.

Particularités de mise en page prises en compte :

- Les zéros sont imprimés `±±` (brochures 2026 et 2027) ou `––` (brochures plus anciennes) ; ils sont convertis en 0.
- Les pages « Renseignements complémentaires » sont lues séparément : elles donnent les commentaires et les effectifs.
- Les pages des départements sont repérées par leur en-tête, ce qui rend l'extraction indépendante du nombre de pages.

**Contrôle** : pour chaque brochure, la somme des lignes de chaque service doit égaler la récapitulation du département, et le total général doit égaler la récapitulation officielle. Une brochure qui échoue à ce contrôle bloque le pipeline.

## Construction des séries

Une série est soit un budget (B), soit des comptes (C) d'une année donnée.

| Série | Source retenue |
|---|---|
| Budget N | colonne « Budget N » de la brochure N |
| Budget de l'année la plus ancienne | colonne « Budget N-1 » de la première brochure |
| Comptes N-2 | colonne « Comptes N-2 » de la brochure N |

La colonne « Budget N-1 » des brochures suivantes n'est pas utilisée en général : elle est parfois retraitée (montants déplacés d'un service à un autre après une réorganisation), et la mélanger avec la version d'origine créerait des doublons. Exception : les opérations extraordinaires (natures 38 et 48), utilisées depuis la brochure suivante quand la brochure N ne les détaille pas.

### Statut des budgets

Certaines brochures sont des **projets du Conseil d'État** et non des budgets adoptés par le Grand Conseil (actuellement 2024 et 2027, voir `pipeline/config.json`). Les amendements votés ensuite n'y figurent pas.

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

## Limites connues

- Montants nominaux, non corrigés de l'inflation ni de la croissance de la population.
- Les annexes (UNIL, HEP, HES, CHUV) ne sont pas intégrées ; ces institutions apparaissent comme des subventions.
- Les comptes contiennent des écritures non budgétées (réévaluations, pertes sur créances) qui expliquent une partie des écarts entre budget et comptes.
- Les textes de lecture de l'onglet Analyses citent parfois des années précises ; ils doivent être relus lors de l'ajout d'une brochure.
