"""Ajoute les PDF d'un dossier au moteur de recherche documentaire.

    python scripts/ingest_documents.py data/documents [--reset]
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.domain.retrieval.ingest import ingest_folder  # noqa: E402

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    print(f"{ingest_folder(Path(sys.argv[1]), reset='--reset' in sys.argv)} passages ajoutés.")
