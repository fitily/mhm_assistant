# IA'mbovo — assistant IA de MHM Ambovo

L'assistant répond aux questions **statistiques** (patients, consultations, sorties, diagnostics)
et aux questions de santé fondées sur les documents chargés, sans exposer les données patients.

```
Question + historique → réécriture → règles déterministes → SQL validé | documents | chat → réponse + audit
```

Les questions chiffrées vont en `SQL`, les questions de santé en `DOCS`, et les salutations,
explications, demandes d'identité ou capacités en `CHAT`. Les suivis sont réécrits avant le routage.
En mode `CHAT`, les réponses médicales non sourcées sont refusées et redirigées vers la recherche dans les documents.

## Principes de sécurité
1. Le modèle ne voit que le schéma `analytics` (quelques vues), jamais les 220 tables.
2. Compte PostgreSQL en **lecture seule** + timeout + coût `EXPLAIN` limité.
3. Tout SQL généré est validé (un seul `SELECT`, vues autorisées, paramètres liés, pas de `SELECT *`, identifiants patients seulement dans un `COUNT`).
4. Les définitions métier (patient, visite, tranches d'âge…) sont fixées dans `config/metrics.yaml`.
5. Chaque question est journalisée (`logs/audit_log.jsonl`).
6. L'authentification reste dans Laravel : il envoie un jeton JWT que FastAPI vérifie.

## Démarrage (sans Docker, sur ton Ubuntu)
```bash
cp .env.example .env            # puis remplir SRC_PASSWORD et VEC_PASSWORD
python3 -m venv .venv && source .venv/bin/activate
make install
make test                       # tests unitaires et intégration documentaire locale
```
1. **Adapter puis créer les vues** : ouvrir `data/analytics/views/*.sql`, vérifier les noms de colonnes avec `\d patients` dans `psql`, puis `make views` (ajouter `ADMIN_USER` et `ADMIN_PASSWORD` dans `.env`).
2. `make validate` : compare `config/data_dictionary.yaml` avec les vraies vues.
3. `make chat` : tester dans le terminal (Ollama doit tourner).
4. `make run` : lancer l'API sur http://localhost:8000 (documentation interactive : `/docs`).
5. `make ingest` : indexer les PDF placés dans `data/documents/`.

Les conversations gardent les 10 derniers échanges; `/clear` les efface dans le CLI
et `POST /v1/clear` les efface pour une session API. Le seuil RAG se règle avec
`MIN_SCORE` (défaut `0.55`) dans `.env`; seuls les passages au-dessus du seuil sont envoyés au LLM.
`MHM_DEBUG=1` affiche localement les requêtes de recherche, scores, extraits et motifs de rejet.
Le CLI affiche le mode sous chaque réponse; l'API renvoie `text`, `sender`, `mode`, les sources et les données.
La constante `ASSISTANT_NAME` définit le nom utilisé par le CLI, l'API et les prompts.

## Appeler l'API
```bash
curl -X POST localhost:8000/v1/chat -H "Content-Type: application/json" \
     -d '{"question": "Combien de patients par district ?"}'
curl -X POST localhost:8000/v1/clear -H "Content-Type: application/json" -d '{}'
```
En production : `AUTH_DISABLED=0`, `JWT_SECRET` identique à celui de Laravel, et l'en-tête
`Authorization: Bearer <jeton>` envoyé par Laravel.

## Organisation
| Dossier | Rôle |
|---|---|
| `config/` | dictionnaire de données, définitions métier, prompts |
| `data/analytics/views/` | SQL des vues (source de vérité) |
| `backend/app/domain/` | logique : routeur, exemples text-to-SQL, validation SQL, recherche documentaire |
| `backend/app/infrastructure/` | accès PostgreSQL et Ollama |
| `backend/app/services/` | orchestration (`chat_service.py`) |
| `backend/app/api/` | routes FastAPI |
| `backend/tests/` | tests unitaires et questions de référence (gold) |
| `cli/`, `scripts/` | outils d'opérateur |
| `docs/` | architecture, dictionnaire, questions de référence |
| `backend/app/core/config.py` | configuration et identité affichée |

## Docker (production uniquement)
```bash
docker build -f backend/Dockerfile -t iambovo .
```
