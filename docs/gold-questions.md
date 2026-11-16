# Questions de référence (gold set)

Le fichier `backend/tests/gold/gold_questions.yaml` liste des questions avec l'outil attendu.

- `make test` vérifie le **choix de l'outil** (sans LLM, sans base).
- `make gold` pose les questions au chatbot complet (Ollama + base) et compare le mode obtenu.

Règle de travail : chaque fois que le chatbot se trompe, ajouter la question ici AVANT de
corriger le code. Objectif : 40 à 60 questions validées par l'équipe médicale.

Format :
```yaml
- {question: "Combien de patients ?", expected_mode: INDICATOR, must_contain: ["total patients"]}
```
Modes : `INDICATOR`, `SQL`, `DOCS`, `GENERAL`, `PATIENT`, `SAFETY`, `UNDEFINED_TERM`.
