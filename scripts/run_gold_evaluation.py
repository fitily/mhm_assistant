"""Évalue le chatbot COMPLET (LLM + base) sur les questions de référence.

    python scripts/run_gold_evaluation.py
Chaque question a un mode attendu et, éventuellement, des textes qui doivent apparaître.
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.chat_service import answer  # noqa: E402


def main() -> int:
    cases = yaml.safe_load((ROOT / "backend/tests/gold/gold_questions.yaml").read_text("utf-8"))
    ok = 0
    for case in cases:
        result = answer(case["question"], user="gold")
        good = result.mode == case["expected_mode"] and all(
            t.casefold() in result.text.casefold() for t in case.get("must_contain", []))
        ok += good
        print(f"[{'OK ' if good else 'KO '}] {case['question']}  → {result.mode}"
              f" (attendu {case['expected_mode']})")
    print(f"\n{ok}/{len(cases)} réussies")
    return 0 if ok == len(cases) else 1


if __name__ == "__main__":
    sys.exit(main())
