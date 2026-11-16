# Vues analytics (source de vérité)

Le chatbot n'interroge **que** les vues du schéma `analytics` (liste blanche définie dans
`config/data_dictionary.yaml`). Il ne voit jamais les tables de production. Chaque fichier `.sql`
de `views/` définit une vue (ou des fonctions) et s'exécute dans l'ordre alphabétique.

## Fichiers

| Fichier | Contenu | Dans le data_dictionary |
|---|---|---|
| `00_functions.sql` | schéma `analytics` et fonctions : `patient_key`, `norm_gender`, `safe_date`, `age_group` (13 tranches) | non |
| `10_v_patients_masked.sql` | `analytics.v_patients_masked` : patients non supprimés (`deleted = 0`) | oui |
| `20_v_visits.sql` | `analytics.v_visits` : une ligne = une admission (une visite) | oui (vue par défaut) |
| `30_v_generalist_consultations.sql` | `analytics.v_generalist_consultations` : consultations de médecine générale | oui |
| `40_v_discharges.sql` | `analytics.v_discharges` : sorties et décès (`patient_dead`) | oui |
| `50_v_diagnoses.sql` | `analytics.v_diagnoses` : une ligne = un diagnostic posé | oui |
| `60_v_data_freshness.sql` | `analytics.v_data_freshness` : date minimale et maximale de chaque vue (technique) | non |
| `99_grants.sql` | droits de lecture du rôle `chatbot_ro` | non |

`v_data_freshness` est une vue technique : elle n'est pas interrogée par le chatbot. La clé
`data_freshness` du data_dictionary pointe actuellement sur `analytics.v_visits` / `visit_date`.

## Vues et colonnes

Les colonnes ci-dessous correspondent à `config/data_dictionary.yaml`. Valeur `Non renseigné` :
champ texte vide ou absent.

| Vue | Grain | Colonne de date | Colonnes |
|---|---|---|---|
| `v_visits` | une admission | `visit_date` | `visit_key`, `patient_key`, `visit_date`, `category`, `gender`, `age_group`, `district`, `commune` |
| `v_patients_masked` | un patient non supprimé | `registered_at` | `patient_key`, `registered_at`, `age`, `gender`, `age_group`, `district`, `commune` |
| `v_generalist_consultations` | une consultation de médecine générale | `consultation_date` | `consultation_key`, `patient_key`, `consultation_date`, `gender`, `age_group`, `district`, `commune`, `outcome` |
| `v_diagnoses` | un diagnostic posé | `diagnosis_date` | `diagnosis_key`, `patient_key`, `diagnosis_date`, `diagnosis_label`, `icd10_code`, `gender`, `age_group`, `district` |
| `v_discharges` | une sortie | `discharge_date` | `discharge_key`, `patient_key`, `discharge_date`, `patient_dead`, `gender`, `age_group` |

## Règles à connaître

- **Dates** : converties au fuseau `Indian/Antananarivo`.
- **Âge** : `age_group` est calculé à la date de l'événement (visite, consultation, diagnostic,
  sortie). Seule exception : `v_patients_masked`, où il s'agit de l'âge **actuel**.
- **Comptage** : `COUNT(*)` compte des lignes (visites, diagnostics, sorties...). Pour compter des
  patients, utiliser `COUNT(DISTINCT patient_key)`. Une visite peut avoir plusieurs diagnostics.
- **Mortalité** : `patient_dead` vaut `true`, `false` ou `NULL` (inconnu). Filtrer avec
  `patient_dead IS TRUE`.
- **Colonne fragile** : `outcome` (consultations) est mal renseignée, souvent vide après juin 2026.
  Ne pas en tirer de statistique fiable (voir `fragile_columns` dans le data_dictionary).
- **Patients supprimés** : seule `v_patients_masked` filtre `deleted = 0`. Les autres vues
  gardent les événements d'un patient supprimé (sexe et âge peuvent alors être vides).

## Ordre d'exécution et dépendances

`v_data_freshness` lit `v_visits`, `v_diagnoses`, `v_discharges` et `v_generalist_consultations`.
Pour pouvoir relancer `make views` à volonté :

- `50_v_diagnoses.sql` commence par `DROP VIEW IF EXISTS analytics.v_data_freshness;` puis
  `DROP VIEW IF EXISTS analytics.v_diagnoses;` avant de recréer la vue ;
- `60_v_data_freshness.sql` doit rester après le 50 ;
- ne pas utiliser `DROP ... CASCADE`, qui supprime des vues dépendantes sans prévenir.

`CREATE OR REPLACE VIEW` ne permet pas de renommer ni de réordonner des colonnes : en cas de
changement de colonnes, supprimer la vue (`DROP VIEW`) puis la recréer.

## Important

Les noms de colonnes de `public.*` sont des hypothèses. Avant d'exécuter, vérifiez chaque table
avec `\d nom_table` dans `psql` et adaptez les fichiers. Vérifiez en particulier que `created_at`
est bien un `timestamptz` (sinon la conversion de fuseau peut décaler la date d'un jour).

## Création et validation

- Création : `make views` (utilise `SRC_*`, `ADMIN_USER` et `ADMIN_PASSWORD` du fichier `.env`, avec
  un compte qui a le droit de créer des vues, pas `chatbot_ro`).
- Toute vue ajoutée ici doit aussi être déclarée dans `config/data_dictionary.yaml` (description,
  mots-clés, colonne de date, colonnes), puis lancer `make validate`.
