# Compte technique Superset pour le backend

Le backend FastAPI a besoin d'un compte Superset **à lui**, uniquement pour demander des *jetons invités*
(accès temporaire à un seul dashboard). Ce n'est ni un compte personnel ni un compte administrateur.

## 1. Créer un rôle limité

Superset → **Settings → List Roles → +**

- Nom : `ambovo_backend`
- Permissions (cherche-les dans la liste, ajoute-les **toutes les trois et rien d'autre**) :
  - `can grant guest token on SecurityRestApi`
  - `can read on SecurityRestApi`
  - `can read on Dashboard` : lecture seule, pour **synchroniser les noms** des dashboards avec Superset
    (voir ci-dessous)

### Noms des dashboards

Les noms affichés dans l'application (page Analytics et chat) sont lus dans Superset (`dashboard_title`) :
renommer un dashboard dans Superset suffit, le changement apparaît en une minute environ (cache de 60 s),
sans modifier le code ni `config/dashboards.yaml`. Le rôle doit pouvoir **voir** ces dashboards
(publiés, ou rôle `ambovo_backend` ajouté dans leur propriété « Roles »). Sinon, ou si Superset est
injoignable, l'application affiche le `title` du catalogue (repli) et le signale dans les journaux
(`Noms des dashboards non synchronisés`).

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

## 5. Si le dashboard ne s'affiche pas dans l'application

Le backend peut donner un jeton (`check_superset.py` = OK) alors que l'iframe reste vide. Les causes habituelles
sont des réglages **de Superset** (fichier `superset_config.py`), pas de l'application :

| Ce qu'on voit | À vérifier |
|---|---|
| Iframe vide ou message « refused to connect » (console du navigateur : `frame-ancestors`) | Superset interdit d'être affiché dans une autre page. Autoriser l'adresse de l'application (ex. `http://localhost:5173`) dans la politique de sécurité (`TALISMAN_CONFIG` → `content_security_policy` → `frame-ancestors`). |
| Dashboard affiché mais « no data » / graphiques en erreur de droits | Le rôle des invités (`GUEST_ROLE_NAME` dans `superset_config.py`) n'a pas accès aux jeux de données du dashboard. |
| Erreur « embedded dashboard not found » | L'UUID du catalogue ne correspond pas à l'intégration (⋯ → Embed dashboard) ou les domaines autorisés n'incluent pas l'application. |
| Connexion qui échoue seulement dans le navigateur | `SUPERSET_PUBLIC_URL` (adresse vue par le navigateur) est fausse ou différente de celle de Superset. |

Aucun de ces réglages ne se change dans le code de l'application.
