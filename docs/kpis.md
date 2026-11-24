# Indicateurs clés (page Analytics, admin)

| Tuile | Définition | Source |
|---|---|---|
| New patients | Fiches patients créées sur les 7 derniers jours, aujourd'hui inclus (0 s'il n'y en a aucune) | `analytics.v_patients_masked.registered_at` |
| Admissions | Visites (admissions) des 7 derniers jours, aujourd'hui inclus | `analytics.v_visits.visit_date` |
| Visits last month | Visites du dernier mois **complet des données** + évolution face au mois précédent | `analytics.v_visits.visit_date` |

- Configuration : `config/kpis.yaml` (aucun SQL : une vue + une colonne de date du dictionnaire ; le code écrit `SELECT COUNT(*)`).
- Route : `GET /v1/kpis` (admin ; médecin 403). Cache 5 minutes, renouvelé à minuit.
- « 7 derniers jours » suit la date du jour ; si les données sont plus anciennes, la tuile affiche 0 et la dernière date disponible.
- « Dernier mois complet » suit la **dernière date des données** (septembre incomplet → août).
- Un indicateur en panne s'affiche « Unavailable » sans bloquer les autres (jamais un faux 0).
- Contrôle sur la vraie base : `python scripts/check_kpis.py` (utiliser le venv du projet, depuis la racine).
