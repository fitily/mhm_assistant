"""Réponses fixes à « qui es-tu ? », « que peux-tu faire ? » et « comment t'utiliser ? » (sans IA).

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

_HOW_TO_USE = re.compile(
    r"\bhow (?:do i |can i |should i |to )use (?:you|ia ?mbovo|the assistant|the chatbot)\b"
    r"|\b(?:user guide|getting started|quick start|how does this work)\b"
    r"|\bcomment (?:je |puis je )?(?:peux |dois |puis )?(?:t |vous )utilis\w+"
    r"|\bcomment utilis(?:er|ez)\b.{0,10}\b(?:t|vous|assistant|ia ?mbovo|chatbot)\b"
    r"|\b(?:mode d emploi|guide d utilisation|guide pratique)\b"
    r"|\bahoana (?:no|ny) (?:fampiasana|ampiasana)\b")

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
    if _HOW_TO_USE.search(text):
        return AnswerResult(_usage_guide(language, role), "CHAT", audit_stage="usage_guide")
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


# --- guide de prise en main : étapes numérotées, seulement celles que le rôle peut réellement utiliser ----------------
_GUIDE_TITLE = {
    "fr": f"Voici un petit guide pour utiliser {ASSISTANT_NAME}, étape par étape :",
    "en": f"Here is a quick step-by-step guide to using {ASSISTANT_NAME}:",
    "mg": f"Ity ny torolalana fohy hampiasana {ASSISTANT_NAME}, dingana isan-dingana:",
}
_GUIDE_STEPS = {
    "DOCS": {
        "fr": ["**Rechercher dans les documents.** Écrivez votre question médicale avec vos mots, par exemple « Quels sont les symptômes du VIH ? ». Je réponds uniquement à partir des documents chargés.",
               "**Vérifier les sources.** Sous chaque réponse issue des documents, les sources utilisées sont listées avec un score de pertinence. Consultez-les pour vérifier l'information avant de vous y fier."],
        "en": ["**Search the documents.** Type your medical question in your own words, for example “What are the symptoms of HIV?”. I answer only from the loaded documents.",
               "**Check the sources.** Under each answer taken from the documents, the sources used are listed with a relevance score. Open them to verify the information before relying on it."],
        "mg": ["**Mitady ao anaty antontan-taratasy.** Soraty amin'ny teninao ny fanontanianao ara-pahasalamana, ohatra: « Inona ny soritr'aretin'ny VIH? ». Ny antontan-taratasy voatondro ihany no ihoarako valiny.",
               "**Hamarino ny loharano.** Eo ambanin'ny valiny rehetra avy amin'ny antontan-taratasy dia lisitra ny loharano nampiasaina miaraka amin'ny isa maneho ny fifandraisana. Jereo izany alohan'ny hitokisana ny fampahalalana."],
    },
    "SQL": {
        "fr": ["**Poser une question sur les données.** Indiquez ce que vous voulez compter et la période, par exemple « Nombre de visites au MHM en juin 2026 ». Le résultat s'affiche en une phrase et un tableau, avec des notes si les données sont incomplètes."],
        "en": ["**Ask about the data.** Say what you want to count and the period, for example “Number of visits at MHM in June 2026”. The result comes as a short answer and a table, with notes when the data is incomplete."],
        "mg": ["**Manontany momba ny angon-drakitra.** Lazao izay tianao isaina sy ny vanim-potoana, ohatra: « Isan'ny fitsidihana ao amin'ny MHM tamin'ny jona 2026 ». Hita ho valiny fohy sy tabilao ny vokatra, miaraka amin'ny fanamarihana raha tsy feno ny angona."],
    },
    "DASHBOARD": {
        "fr": ["**Ouvrir un tableau de bord.** Dites « ouvre le tableau de bord des visites », puis « reviens au précédent » ou « ferme-le ». Demandez « combien de tableaux de bord avez-vous ? » pour voir la liste."],
        "en": ["**Open a dashboard.** Say “open the visits dashboard”, then “go back to the previous one” or “close it”. Ask “how many dashboards do you have?” to see the list."],
        "mg": ["**Manokatra dashboard.** Lazao hoe « sokafy ny dashboard visite », avy eo « miverena amin'ny teo aloha » na « akatony ». Anontanio hoe « firy ny dashboard ananao? » raha hijery ny lisitra."],
    },
}
_GUIDE_TIPS = {
    "fr": "**Bonnes habitudes.** Une question à la fois, avec un sujet et une période clairs ; le bouton d'agrandissement de la fenêtre aide pour les longues réponses ; vous pouvez écrire en français, en anglais ou en malgache.",
    "en": "**Good habits.** One question at a time, with a clear subject and period; the expand button of the chat window helps with long answers; you can write in French, English or Malagasy.",
    "mg": "**Fomba tsara.** Fanontaniana iray isaky ny mandeha, miaraka amin'ny lohahevitra sy vanim-potoana mazava; mety hanampy amin'ny valiny lava ny bokotra manitatra ny fikandrana; afaka manoratra amin'ny teny frantsay, anglisy na malagasy ianao.",
}
_CLINICAL_NOTE = {
    "fr": "Je suis une aide : je ne remplace pas votre jugement clinique.",
    "en": "I am an aid: I do not replace your clinical judgement.",
    "mg": "Mpanampy aho: tsy mitsahatra ny fitsarana ara-pitsaboana ataonao.",
}


def _usage_guide(language: str, role: str | None) -> str:
    modes = [m for m in ("DOCS", "SQL", "DASHBOARD") if role is None or permissions.is_allowed(role, m)]
    steps = [step for m in modes for step in _GUIDE_STEPS[m][language]] + [_GUIDE_TIPS[language]]
    body = "\n".join(f"{i}. {step}" for i, step in enumerate(steps, 1))
    note = f"\n\n{_CLINICAL_NOTE[language]}" if "DOCS" in modes else ""
    return f"{_GUIDE_TITLE[language]}\n\n{body}{note}"
