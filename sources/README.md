# Sources

Brochures budgétaires publiées par l'État de Vaud. Le texte extrait de chacune se trouve dans `txt/`. Les PDF ne sont pas versionnés par défaut ; pour reconstruire depuis les PDF, les placer dans `pdf/` sous le nom `budget-AAAA.pdf`.

| Fichier | Document d'origine | Statut |
|---|---|---|
| budget-2020 | Budget_2020_Grand_Conseil.pdf | adopté |
| budget-2021 | Brochure_budget_2021_adopté_par_GC.pdf | adopté |
| budget-2022 | Brochure_budget_2022_voté.pdf | adopté |
| budget-2023 | Brochure_budget_2023_adopté.pdf | adopté |
| budget-2024 | Brochure_Projet_Budget_2024.pdf | projet du Conseil d'État (le budget adopté est repris de la brochure 2025) |
| budget-2025 | Brochure_verte_Budget_2025_V_corr_du_27.02.2025.pdf | adopté (version corrigée du 27.02.2025) |
| budget-2026 | Brochure_verte_Budget_2026.pdf | adopté |
| budget-2027 | [Projet_Budget_2027_version_online.pdf](https://www.vd.ch/fileadmin/user_upload/themes/etat_droit/finances_publiques/Projet_Budget_2027_version_online.pdf) | projet du Conseil d'État |

Autres documents :

| Fichier | Document d'origine | Statut |
|---|---|---|
| amendements-2027 | [Annexe 1 : Liste des amendements pour compenser l'initiative 12 %](https://www.vd.ch/fileadmin/user_upload/accueil/fichiers_pdf/2026_octobre_actus/261007_Annexe_1_Liste_des_amendements_pour_compenser_l_intiative_12_.pdf), jointe au [communiqué du 7 octobre 2026](https://www.vd.ch/actualites/communiques-de-presse-de-letat-de-vaud/detail/communique/mise-en-oeuvre-de-linitiative-des-12) | amendements proposés par le Conseil d'État, avant le vote du Grand Conseil |

Le texte a été extrait avec `pdftotext -layout` ; `pipeline/amendements.py` le lit.

Chaque brochure contient le budget de l'année, celui de l'année précédente et les comptes d'il y a deux ans. Il serait utile d'ajouter la brochure adoptée 2024 pour disposer aussi de ses commentaires et de son budget d'investissement adopté.
