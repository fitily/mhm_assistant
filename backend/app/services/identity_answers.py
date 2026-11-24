"""Réponses fixes à « qui es-tu ? » et « que peux-tu faire ? » (sans IA).

Pourquoi : le petit modèle local inventait le nom de l'assistant (« Boivo ») et ses capacités.
Ces deux questions ont une seule bonne réponse, connue du backend : le nom vient de la configuration
et les capacités de domain/permissions.py (donc elles dépendent du rôle de la personne connectée).
"""
from __future__ import annotations

import re

from app.core.config import ASSISTANT_NAME
from app.domain import dashboard_intent, permissions
from app.domain.models import AnswerResult

MAX_CHARS = 80  # une vraie question d'identité est courte

_WHO = re.compile(
    r"\b(?:qui es tu|qui etes vous|qui est tu|who are you|who r u|what is your name|what s your name|"
    r"your name|quel est ton nom|quel est votre nom|comment t appelles tu|comment vous appelez vous|"
    r"iza ianao|iza moa ianao|inona no anaranao)\b")
_CAN_DO = re.compile(
    r"\b(?:what can you do|what are your capabilities|what do you do|que peux tu faire|que pouvez vous faire|"
    r"que sais tu faire|que savez vous faire|quelles sont tes capacites|a quoi sers tu|"
    r"inona no azonao atao|inona no ataonao)\b")

_WHO_TEXT = {
    "fr": f"Je suis {ASSISTANT_NAME}, l'assistant IA de MHM Ambovo (Mobile Hilfe Madagaskar).",
    "en": f"I'm {ASSISTANT_NAME}, the AI assistant of MHM Ambovo (Mobile Hilfe Madagaskar).",
    "mg": f"{ASSISTANT_NAME} aho, mpanampy IA an'ny MHM Ambovo (Mobile Hilfe Madagaskar).",
}
_INTRO = {"fr": "Voici ce que je peux faire :", "en": "Here is what I can do:", "mg": "Ireto no azoko atao:"}
_ABILITIES = {
    "DOCS": {
        "fr": "chercher des informations médicales dans les documents chargés, en citant mes sources ;",
        "en": "look up medical information in the loaded documents, citing my sources;",
        "mg": "mitady fampahalalana ara-pahasalamana ao amin'ny antontan-taratasy voatondro, miaraka amin'ny loharano;",
    },
    "SQL": {
        "fr": "répondre aux questions chiffrées sur les données de MHM (patients, visites…) ;",
        "en": "answer numerical questions about MHM data (patients, visits…);",
        "mg": "mamaly fanontaniana ara-tarehimarika momba ny angon-drakitra MHM (marary, fitsidihana…);",
    },
    "DASHBOARD": {
        "fr": "ouvrir, changer ou fermer les tableaux de bord (par exemple « ouvre le tableau de bord des visites ») ;",
        "en": "open, switch or close dashboards (for example “open the visits dashboard”);",
        "mg": "manokatra, manova na manakatona ny dashboard (ohatra: « sokafy ny dashboard visite »);",
    },
    "CHAT": {
        "fr": "discuter et expliquer comment je fonctionne.",
        "en": "chat and explain how I work.",
        "mg": "miresaka sy manazava ny fiasako.",
    },
}
_ORDER = ("DOCS", "SQL", "DASHBOARD", "CHAT")


def build(question: str, language: str, role: str | None) -> AnswerResult | None:
    """Réponse fixe si `question` demande l'identité ou les capacités ; None sinon (le routage continue)."""
    if len(question) > MAX_CHARS:
        return None
    text = dashboard_intent.normalize(question)
    if _WHO.search(text):
        return AnswerResult(_WHO_TEXT[language] + _capabilities(language, role, with_intro=True), "CHAT",
                            audit_stage="identity")
    if _CAN_DO.search(text):
        return AnswerResult(_capabilities(language, role, with_intro=False).lstrip("\n"), "CHAT",
                            audit_stage="capabilities")
    return None


def _capabilities(language: str, role: str | None, *, with_intro: bool) -> str:
    modes = [m for m in _ORDER if role is None or permissions.is_allowed(role, m)]
    lines = "\n".join(f"- {_ABILITIES[m][language]}" for m in modes)
    intro = _INTRO[language]
    return f"\n\n{intro}\n{lines}" if with_intro else f"{intro}\n{lines}"


# « oui », « yes please », « ok » seuls : iA'mbovo n'a aucune action en attente à confirmer. Sans cette règle,
# le modèle réécrivait « yes please » en une vieille question de l'historique et la relançait en SQL.
_CONFIRM = re.compile(
    r"^(?:oui|yes|yep|yeah|ok|okay|d accord|bien sur|sure|please|vas y|go ahead|eny|ie)"
    r"(?: (?:please|s il (?:te|vous) plait|merci|thanks|azafady))?$")
_NOTHING_PENDING = {
    "fr": "Je n'ai rien en attente de confirmation. Pouvez-vous me dire précisément ce que vous souhaitez ?",
    "en": "I have nothing waiting for confirmation. Could you tell me exactly what you would like?",
    "mg": "Tsy misy miandry fankatoavana aho. Azafady, lazao mazava izay tianao.",
}


def confirmation(question: str, language: str) -> AnswerResult | None:
    text = dashboard_intent.normalize(question).strip(" .!?,;:")
    if len(text) <= MAX_CHARS and _CONFIRM.fullmatch(text):
        return AnswerResult(_NOTHING_PENDING[language], "CHAT", audit_stage="bare_confirmation")
    return None
