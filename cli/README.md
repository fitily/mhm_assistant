# CLI — Trusted local operator only

Outil en ligne de commande pour l'opérateur technique (toi), pour tester le chatbot sans
l'API ni l'interface. Il utilise **exactement** le même code que l'API (`backend/app`).

- Ne jamais l'exposer à des utilisateurs : il n'y a pas d'authentification.
- Les droits d'accès aux données sont ceux du compte PostgreSQL (`SRC_USER`, lecture seule).

```bash
python cli/chatbot.py                          # discuter
python cli/chatbot.py ingest data/documents    # ajouter les PDF au moteur de recherche
```

Le dialogue garde les 10 derniers échanges. Dans l'invite, `/clear` efface l'historique;
`/sql` et `/docs` forcent une source, `/views` liste les vues et `/audit` affiche la dernière requête.
Le mode utilisé est affiché avec chaque réponse. Le seuil documentaire est configurable avec
`MIN_SCORE` (0.55 par défaut). `MHM_DEBUG=1` affiche localement les scores, passages RAG,
durées par étape et délais réseau configurés.

Après une modification du découpage documentaire, `make ingest-reset` reconstruit les passages
et leurs embeddings. Cette commande supprime puis recrée toute la table documentaire.
