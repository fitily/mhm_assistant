.PHONY: install run test views validate gold ingest ingest-reset chat

install:
	pip install -r backend/requirements-dev.txt

run:
	cd backend && uvicorn app.main:app --reload --port 8000

test:
	cd backend && python -m pytest -q

views:
	bash scripts/create_analytics_views.sh

validate:
	python scripts/validate_dictionary.py

gold:
	python scripts/run_gold_evaluation.py

ingest:
	python scripts/ingest_documents.py data/documents

ingest-reset:
	python scripts/ingest_documents.py data/documents --reset

chat:
	python cli/chatbot.py
