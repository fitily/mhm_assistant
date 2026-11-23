# Commandes de tableau de bord dans le chat (administrateur)

Le chat reconnaît des commandes **sans IA** (règles dans `backend/app/domain/dashboard_intent.py`).
Il faut le mot « tableau de bord » ou « dashboard » **et** un verbe d'action.

| Intention | Exemples |
|---|---|
| `show_dashboard` | « Montre-moi le tableau de bord des visites » · « Open the medical dashboard » |
| `switch_dashboard` | « Passe au dashboard médical » · « Switch to the visits dashboard » |
| `switch_dashboard` (précédent) | « Reviens au tableau de bord précédent » · « Go back to the previous dashboard » |
| `close_dashboard` | « Ferme le tableau de bord » · « Close the dashboard » |
| *(question statistique)* | « Combien de visites dans le tableau de bord ? » → reste une question chiffrée (SQL) |
| *(conversation)* | « C'est quoi un dashboard ? » → conversation normale |

Règles :
- Seul l'**administrateur** a ces commandes ; un médecin reçoit un refus poli (audit : `forbidden:DASHBOARD`).
- Le dashboard visé est cherché **uniquement** dans `config/dashboards.yaml` (clé, titre ou `keywords`).
  Sans précision, ou si plusieurs correspondent, le chat demande lequel (il liste les titres du catalogue).
- Pour qu'un mot désigne un dashboard, l'ajouter dans `keywords` de ce dashboard.
- Le backend ne garde aucun état. Il répond avec un texte et un champ `action` que l'interface exécute :

```json
{"type": "open_dashboard", "dashboard": "visite", "title": "AI-assistant-dashboard"}
{"type": "close_dashboard"}
{"type": "previous_dashboard"}
```

L'action ne contient jamais d'UUID ni d'URL : l'interface obtient l'accès par `/v1/superset/guest-token`.
