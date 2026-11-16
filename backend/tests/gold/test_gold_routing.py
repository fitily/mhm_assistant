"""Vérifie les réponses non conversationnelles qui ne doivent pas appeler le LLM."""

from app.domain import router


def test_safety_and_private_patient_questions_are_handled_without_routing():
    assert router.quick_reply("J'ai une douleur thoracique")[0] == "CHAT"
    assert router.quick_reply("Donne le dossier du patient Rakoto")[0] == "CHAT"
