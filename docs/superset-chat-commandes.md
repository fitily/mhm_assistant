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

## Compléments (réponses sans IA)

| Phrase | Réponse |
|---|---|
| « Combien de tableaux de bord avez-vous ? », « Quels dashboards ? », « List the dashboards » | Liste tirée du catalogue (`config/dashboards.yaml`), sans action. Ne passe jamais par le SQL. |
| « Reviens au précédent », « the previous one », « ferme-le », « close it » | Comprises **seulement si le message précédent était une commande de dashboard** (sinon routage normal). |
| « Qui es-tu ? », « Who are you? », « Que peux-tu faire ? » | Réponse fixe : nom `iA'mbovo` (config) + capacités selon le rôle (`domain/permissions.py`). Le modèle local n'est plus appelé. |

Limite connue : une question chiffrée formulée de façon inattendue peut encore être traduite en SQL par le modèle ;
pour la diagnostiquer, relever la ligne correspondante dans `logs/audit_log.jsonl`.

| « Génère / crée un dashboard… », « generate a dashboard… » | Réponse honnête : création impossible, liste des dashboards existants. Le modèle n'invente plus de dashboard. |
| « oui », « yes please », « ok » seuls | « Je n'ai rien en attente de confirmation… » : plus jamais réécrits en une ancienne question puis lancés en SQL. |
| « How do I use you? », « how to use you », « Comment t'utiliser ? », « mode d'emploi », « user guide » | Guide pas à pas fixe (sans IA), adapté au rôle : l'admin voit données + dashboards, le médecin voit documents + sources (+ rappel qu'iA'mbovo ne remplace pas le jugement clinique). fr / en / mg. |
