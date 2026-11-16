# Architecture

## Flux d'une question
```
Laravel / Vue ──(JWT)──▶ POST /v1/chat
                           │
                  chat_service.answer
                           │
        ┌──────────────────┼───────────────────────┐
   quick_reply         router.route            audit (jsonl)
 (urgence, terme       règles d'abord,
  non défini, …)       LLM si doute
                           │
     ┌───────────┬─────────┴─────────┬────────────┐
 INDICATOR      SQL                DOCS        GENERAL / PATIENT
 requêtes     LLM → validator     pgvector      réponse courte /
 écrites      → EXPLAIN → exec    + Ollama      refus (dossier individuel)
 à la main    (vues analytics)
```

## Décisions
- **Monolithe modulaire** : un seul service FastAPI. 10 utilisateurs et un seul développeur
  ne justifient pas de microservices.
- **Indicateurs d'abord** : les questions fréquentes n'utilisent pas le LLM (exactes, rapides).
  Le text-to-SQL libre est le second niveau, borné aux vues autorisées.
- **Authentification déléguée à Laravel** (JWT), pas de second système d'utilisateurs.
- **Ollama et PostgreSQL en local** en développement ; Docker seulement pour la production.
- **Pas de LlamaIndex** : requêtes pgvector directes (moins de dépendances, mémoire réduite).

## À ajouter plus tard
Observabilité (Prometheus/Grafana), `docker-compose`, CI GitHub, migrations Alembic,
interface Vue (`frontend/`), rôles par vue (une vue par profil utilisateur).
