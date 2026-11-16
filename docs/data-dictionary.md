# Dictionnaire de données (lecture humaine)

La version lue par le programme est `config/data_dictionary.yaml` ; les définitions métier
sont dans `config/metrics.yaml`. Ce document sert à les expliquer à l'équipe.

| Vue | Une ligne = | Date de référence |
|---|---|---|
| `analytics.v_patients` | un patient non supprimé (`deleted = 0`) | `created_date` |
| `analytics.v_admissions` | une admission = une visite | `admission_date` |
| `analytics.v_generalist_consultations` | une consultation de médecine générale | `consultation_date` |
| `analytics.v_dismissals` | une sortie ; `patient_dead` = décès | `dismissal_date` |

Toutes les dates viennent de `created_at`. Les 13 tranches d'âge : 0-5, 6-11, 12-17, 18-23,
24-29, 30-35, 36-41, 42-46, 47-52, 53-58, 59-64, 65-70, plus de 70.

## Points ouverts (à valider avec le project manager)
- « Guéri » n'a pas de définition : le chatbot refuse ces questions.
- Les consultations dentaires, internes, externes et pédiatriques n'ont pas encore de vue.
- La colonne `outcome` est peu renseignée après juin 2026.
- Les noms de colonnes de `public.*` utilisés dans les vues sont à vérifier.
