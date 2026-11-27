# Superset : tests de sécurité et de performance (étape 7)

## Tests automatiques
`backend/tests/unit/test_security_routes.py` (lancé avec `pytest`) vérifie, pour les 4 routes protégées
(`GET /v1/superset/dashboards`, `POST /v1/superset/guest-token`, `GET /v1/kpis`, `GET /v1/news`) :

| Cas | Résultat attendu |
|---|---|
| Sans jeton, jeton illisible, signature modifiée | 401 |
| Jeton expiré, sans expiration, signé avec un autre secret, algorithme `none` | 401 |
| Mauvais rôle (médecin sur une route admin, admin sur les actualités) | 403 |
| Rôle absent, vide ou inconnu (`superadmin`, `ADMIN`, `root`) | 403 |
| Médecin sur `guest-token` | 403 et Superset n'est **pas** contacté |
| Réponse `guest-token` | seulement `dashboard_key`, `dashboard_id`, `token`, `expires_at`, `superset_domain` ; `Cache-Control: no-store` |
| Erreur Superset contenant un mot de passe | message neutre côté client ; ni secret, ni jeton dans la réponse, l'audit ou les journaux |

Les tests de `test_superset_api.py` couvrent en plus : clés hors catalogue (404, Superset non contacté),
corps vide (422) et trace d'audit.

## Tests manuels (validés le 27/11/2026)
Connexion (le champ s'appelle `access_token`) :
```bash
ADMIN=$(curl -s localhost:8000/v1/auth/login -H 'Content-Type: application/json' \
  -d "{\"username\":\"$A\",\"password\":\"$AP\"}" | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
```
| Test | Résultat |
|---|---|
| Médecin sur `guest-token` et `dashboards` | 403 / 403 |
| Sans jeton, jeton falsifié | 401 |
| Clé inconnue, `../../etc/passwd` | 404 « Dashboard inconnu. » |
| `/v1/kpis` médecin / admin ; `/v1/news` admin / médecin | 403 / 200 ; 403 / 200 |
| Réponse `guest-token` | 5 champs seulement, jeton invité valable 300 s, aucun secret |
| Délai de génération | environ 0,11 s par jeton, `Cache-Control: no-store` |
| Audit | `guest_token_ok` et `unknown_dashboard` tracés, sans jeton ni mot de passe |

À valider : jeton expiré réel (`JWT_EXPIRE_MINUTES=1`) et test navigateur (un seul appel `guest-token` par
ouverture, nettoyage du cadre au changement de dashboard, renouvellement du jeton sans écran blanc).

## Performance
Un jeton invité est généré à chaque demande (pas de cache : il est lié à une personne). Coût mesuré :
environ 0,1 s, inutile d'optimiser.
