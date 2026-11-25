# Test temporaire : Gemini à la place de Llama 3.2

**Ce qui change** : seulement la génération de texte (`ollama.complete` / `ollama.stream`). Embeddings BGE-M3 (Ollama),
PostgreSQL + pgvector, validation SQL en lecture seule, routes FastAPI et frontend restent identiques.
Code ajouté : `backend/app/infrastructure/llm/gemini.py` (aucune ligne d'Ollama supprimée).

## Activer
Dans `.env` : `LLM_MODEL=gemini-…` (nom exact du modèle) et la clé dans `GEMINI_API_KEY` (ou, temporairement, `OLLAMA_HOST`).
Redémarrer le backend (`pkill -f uvicorn; make run`), puis `python scripts/check_gemini.py`.
`GET /health` indique le fournisseur actif (`"llm": "gemini:…"` ou `"ollama"`).

## Revenir à Ollama + Llama 3.2
Remettre `LLM_MODEL=llama3.2` et `OLLAMA_HOST=http://localhost:11434`, redémarrer. Rien d'autre.

## Comparer
`make gold` (questions de référence) avec Llama, puis avec Gemini ; comparer les modes obtenus et les temps.

## Erreurs gérées
429 / 500 / 502 / 503 / 504 et coupures réseau : 2 nouvelles tentatives avec attente croissante (`Retry-After` respecté, 20 s max) ;
réponse bloquée ou vide : erreur claire ; délais dépassés : message habituel du chat. La clé n'apparaît ni dans les URL, ni dans les journaux.

## Confidentialité
Les questions et les extraits de documents envoyés au modèle quittent la machine. Sur l'offre gratuite, Google peut réutiliser
les contenus pour améliorer ses produits : à vérifier dans les conditions de votre compte avant d'envoyer autre chose que des questions de test.
