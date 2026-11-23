# Compte technique Superset pour le backend

Le backend FastAPI a besoin d'un compte Superset **à lui**, uniquement pour demander des *jetons invités*
(accès temporaire à un seul dashboard). Ce n'est ni un compte personnel ni un compte administrateur.

## 1. Créer un rôle limité

Superset → **Settings → List Roles → +**

- Nom : `ambovo_backend`
- Permissions (cherche-les dans la liste, ajoute-les **toutes les deux et rien d'autre**) :
  - `can grant guest token on SecurityRestApi`
  - `can read on SecurityRestApi`

## 2. Créer l'utilisateur

Superset → **Settings → List Users → +**

- Nom d'utilisateur : `svc_ambovo`
- Rôle : `ambovo_backend` (**uniquement celui-là**)
- Mot de passe : long et unique (`python3 -c "import secrets; print(secrets.token_urlsafe(24))"`)

## 3. Le déclarer dans le `.env` du projet

```
SUPERSET_URL=http://localhost:18088
SUPERSET_USERNAME=svc_ambovo
SUPERSET_PASSWORD=<le mot de passe>
```

## 4. Vérifier

```bash
python scripts/check_superset.py
```

Le script affiche une ligne `OK` par dashboard du catalogue (`config/dashboards.yaml`), ou la cause de l'échec :

| Message | Signification |
|---|---|
| `refuse les identifiants` | mauvais nom d'utilisateur ou mot de passe dans le `.env` |
| `n'a pas le droit de ...` | il manque une des deux permissions du rôle |
| `a refusé de créer le jeton invité (code 400/422)` | l'embarquement n'est pas activé pour ce dashboard (⋯ → Embed dashboard) ou l'UUID est faux |
| `injoignable` / `délai dépassé` | Superset est arrêté ou `SUPERSET_URL` est faux |
