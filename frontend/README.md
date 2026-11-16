# Frontend Vue.js (à créer)

Interface à créer après la stabilisation de l'API. Elle affichera le nom du bot à partir de
`sender` et appellera `POST /v1/chat` (réponse : `text`, `sender`, `mode`,
`data.columns/rows`, `sources`, `notes`). Les modes sont `SQL`, `DOCS` et `CHAT`.

Pour afficher la recherche documentaire avant la réponse et les morceaux générés en direct,
appeler `POST /v1/chat/stream` avec le même JSON. Le flux SSE émet `status`, `token`, puis
`complete` (même forme que la réponse JSON) ou `error`.
Pour les tableaux de bord fixes, utiliser Apache Superset plutôt que de les recoder.
