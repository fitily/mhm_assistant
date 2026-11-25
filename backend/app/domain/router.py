"""Réécriture des suivis et routage déterministe."""
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass

import httpx
from langdetect import DetectorFactory, LangDetectException, detect_langs

from app.core.config import ASSISTANT_NAME, debug_trace
from app.core.dictionary import undefined_terms
from app.domain import prompts
from app.domain.formatting import format_history, numbers_in
from app.infrastructure.llm import ollama

_FOLLOWUP = re.compile(
    r"^\W*(?:et|and|also|aussi|pourquoi|why|que veut dire|"
    r"what does (?:that|this|it|the result|the answer) mean|what about|"
    r"non[, ]|mais|mais alors|ça|cela|it|that|those|them)\b", re.I)
_FRAGMENT = re.compile(
    r"^\W*(?:les?|la|des|ceux?|celles?|cette|celui|celle|same|those|them|it|that|"
    r"oui|yes|femmes?|women|hommes?|men|garçons?|boys?|filles?|girls?)\b", re.I)
_CORRECTION_OR_EXPLANATION = re.compile(
    r"\b(?:que veut dire|que signifie|qu'est-ce que ça veut dire|what does .+ mean|"
    r"pourquoi|why|non[, ]+j['’]ai demandé|that is not what i asked)\b", re.I)
_IDENTITY = re.compile(
    r"\b(?:qui es[- ]tu|qui êtes[- ]vous|who are you|what is your name|what's your name|"
    r"quel est ton nom|comment t'appelles[- ]tu|what can you do|"
    r"que peux[- ]tu faire|que savez[- ]vous faire|quelles sont tes capacités|"
    r"what are your capabilities|quelles sources|quels documents|quelles vues|"
    r"comment fonctionnes[- ]tu|how do you work|est[- ]ce que je peux|"
    r"puis[- ]je|can i ask|can i|iza ianao|inona no anaranao|inona no azonao atao)\b", re.I)
_SUMMARY = re.compile(
    r"\b(?:résume(?:r)?|résumé|summari[sz]e|summary|fintino)\b.{0,50}"
    r"\b(?:conversation|échange|discussion|chat|resaka)\b", re.I)
_GREETINGS = re.compile(
    r"^\W*(?:bonjour|salut|bonsoir|hello|hi|hey|merci(?: beaucoup)?|"
    r"thanks|thank you(?: so much)?|salama|manao ahoana|misaotra(?: betsaka)?)[\W]*$", re.I)
_SQL = re.compile(
    r"\b(?:combien|how many|nombre de|count|total|statistiques?|statistics|"
    r"répartition|distribution|moyenne|average|pourcentage|percentage|"
    r"taux|trend|évolution|évolutions|comparer|compare|firy|isan['’]ny|"
    r"fitambaran|ampitahao|fizarana|salanisa)\b", re.I)
_DATA = re.compile(
    r"\b(?:patient|patients|admission|admissions|visite|visites|consultation|"
    r"consultations|diagnostic|diagnostics|décès|deces|mortalité|deaths|"
    r"district|commune|sexe|gender|tranche|âge|age|marary|fizahana|fitsidihana|"
    r"fahafatesana|taona|lahy|vavy)\b", re.I)
_DOCS = re.compile(
    r"\b(?:sympt[oô]mes?|maladie|maladies|disease|diseases|traitement|treatment|"
    r"soigner|treat|médicament|medicine|posologie|dosage|prévention|prevention|"
    r"protocole|guideline|recommandation|recommendation|définition|definition|"
    r"que signifie|qu'est-ce que|c'est quoi|what is|what does .{1,60} stand for|"
    r"who is|comment traiter|how to treat|health|santé|"
    r"\b(?:vih|sida|hiv|aids)\b|"
    r"fièvre|fever|douleur|pain|toux|cough|mal de tête|headache|nausée|nausea|"
    r"respirer|breath|enceinte|pregnant|aretina|soritr['’]aretina|fitsaboana|"
    r"fisorohana|fanafody)\b", re.I)
_MEDICAL = re.compile(
    r"\b(?:sympt[oô]me|maladie|disease|infection|virus|vih|sida|hiv|aids|"
    r"traitement|treatment|médicament|medicine|dosage|posologie|diagnostic|"
    r"fièvre|fever|douleur|pain|toux|cough|saignement|bleeding|grossesse|pregnan|"
    r"headache|mal de tête|nausée|nausea|respirer|breath|santé|health|aretina|"
    r"soritr['’]aretina|fitsaboana|fanafody)\b", re.I)
_MEDICAL_CONTENT = re.compile(
    r"\b(?:symptoms?|sympt[oô]mes?|treatment|traitement|transmitted|transmission|"
    r"contagious|contagieux|diagnosis|diagnostic|dosage|posologie|caused by|"
    r"causé par|means|signifie|defined as|se définit|virus|infection|disease|"
    r"infectious|contagion|prevention|prévention|spreads?|se transmet|aretina|"
    r"fitsaboana|fisorohana|mifindra)\b", re.I)
_NO_ACCESS = re.compile(
    r"\b(?:i (?:do not|don't|cannot|can't|will not|won't) have access to|"
    r"i (?:cannot|can't|will not|won't) (?:be able to )?access|"
    r"je n['’](?:ai|aurai|aurais) pas accès|je ne peux pas accéder|"
    r"je ne dispose pas d'accès|tsy afaka miditra|tsy manana fahafahana miditra)\b", re.I)
_FR_WORDS = {"qui", "es", "tu", "est", "quoi", "êtes", "vous", "comment", "combien", "les",
             "des", "une", "je", "bonjour", "quel", "quelle", "pourquoi", "peux", "c'est",
             "parles", "parlez", "merci", "salut", "et", "pour", "de", "du", "en", "chez",
             "le", "la", "dans", "sur", "avec", "oui", "fournir", "utiliser", "t'utiliser", "d'emploi"}
_EN_WORDS = {"who", "are", "you", "what", "is", "how", "many", "the", "your", "can",
             "hello", "why", "do", "does", "thanks", "speak", "and", "about", "women", "men",
             "in", "have", "any", "clue", "stand", "stands", "for", "from", "with", "health",
             "to", "of", "this", "that", "its", "there", "prevalence", "study", "reported",
             "means"}
_MG_WORDS = {"aho", "ahó", "ianao", "izy", "izahay", "isika", "ianareo", "iza", "inona",
             "aiza", "ahoana", "oviana", "firy", "ve", "tsy", "eny", "ary", "sy", "ny",
             "dia", "amin", "momba", "mba", "azafady", "misaotra", "salama", "aretina",
             "soritr'aretina", "afaka", "manana", "atao", "fa", "no", "izany"}
EMERGENCY = re.compile(
    r"\b(chest pain|cannot breathe|difficulty breathing|severe bleeding|unconscious|"
    r"suicide|seizure|anaphylaxis|choking|stroke|urgence médicale|douleur thoracique|"
    r"difficulté respiratoire|hémorragie|inconscient|convulsion|anaphylaxie|avc)\b", re.I)
PATIENT_RECORD = re.compile(
    r"\b(patient[e]?\s+(?:nommé|named|appelé)|mrn|(?:dossier|historique|antécédents?).{0,40}"
    r"\bpatient)\b", re.I)
EMERGENCY_TEXT = {
    "fr": "Cela peut être une urgence médicale. Contactez immédiatement les services d'urgence locaux.",
    "en": "This may be a medical emergency. Contact local emergency services immediately.",
    "mg": "Mety ho vonjy taitra ara-pahasalamana izany. Mifandraisa avy hatrany amin'ny sampana mpamonjy voina eo an-toerana.",
}
PATIENT_MESSAGE = {
    "fr": "La consultation de dossiers individuels n'est pas disponible. Je peux répondre à des questions statistiques agrégées.",
    "en": "Looking up individual patient records is not available. I can answer aggregate statistical questions.",
    "mg": "Tsy azo jerena ny antontan-taratasin'ny marary tsirairay. Afaka mamaly fanontaniana momba ny antontan'isa mitambatra aho.",
}
NO_DATA_TEXT = {
    "fr": "Je n'ai pas de chiffre fiable pour cette question. Reformulez-la complètement.",
    "en": "I don't have a reliable figure for this. Please rephrase the question in full.",
    "mg": "Tsy manana tarehimarika azo antoka momba izany aho. Azafady, avereno amin'ny fomba mazava kokoa ny fanontaniana.",
}
ACCESS_REPLY = {
    "fr": ("Je peux répondre aux questions chiffrées sur les patients, consultations, sorties et diagnostics. "
           "Pour la santé, je m'appuie sur les documents chargés."),
    "en": ("I can answer numerical questions about patients, consultations, discharges, and diagnoses. "
           "For health questions, I use the loaded documents."),
    "mg": ("Afaka mamaly fanontaniana momba ny isan'ny marary, ny fizahana, ny fivoahana ary ny aretina aho. "
           "Ho an'ny fanontaniana ara-pahasalamana dia mampiasa ireo antontan-taratasy nampidirina aho."),
}
LANGUAGE_NAMES = {"en": "English", "fr": "French", "mg": "Malagasy"}

DetectorFactory.seed = 0


@dataclass(frozen=True)
class Route:
    name: str
    question: str
    response: str | None = None


def detect_lang(text: str) -> str:
    """Detect the current message language; use English for short or uncertain input."""
    low = unicodedata.normalize("NFKC", text).casefold()
    words = set(re.findall(r"[a-zàâçéèêëîïôûùüÿœ']+", low))
    scores = {
        "fr": len(words & _FR_WORDS) + 2 * bool(re.search(r"[àâçéèêëîïôûùüÿœ]", low)),
        "en": len(words & _EN_WORDS),
        "mg": len(words & _MG_WORDS),
    }
    strongest = max(scores, key=scores.get)
    unique_signals = {
        "fr": {"bonjour", "merci", "salut", "bonsoir", "oui", "êtes", "c'est", "ça",
               "d'accord", "le", "la", "les", "des", "une", "un", "du", "je", "tu",
               "vous", "quel", "quelle", "utiliser", "t'utiliser", "emploi", "d'emploi", "utilisation"},
        "en": {"hello", "hey", "thanks", "please", "who", "what"},
        "mg": {"salama", "misaotra", "ahoana", "ianao", "azafady", "eny", "tsy",
               "ny", "ve", "ary"},
    }
    if (scores[strongest] >= 2 or words & unique_signals[strongest]) and scores[strongest] > max(
            score for language, score in scores.items() if language != strongest):
        return strongest
    if len(words) < 3:
        return "en"
    try:
        detected = detect_langs(text)
    except LangDetectException:
        return "en"
    if detected and detected[0].prob >= 0.75:
        code = detected[0].lang
        return code if code in LANGUAGE_NAMES else "en"
    return "en"


def language_name(language: str) -> str:
    return LANGUAGE_NAMES.get(language, "English")


def is_summary_request(question: str) -> bool:
    return bool(_SUMMARY.search(question))


def rewrite_followup(question: str, history=None) -> str:
    """Rend autonome un suivi probable avant le choix de source."""
    if not history or not (_FOLLOWUP.search(question) or _FRAGMENT.search(question)):
        return question
    prompt = prompts.render("rewrite", history=format_history(history), question=question)
    try:
        data = json.loads(ollama.complete(
            prompt, predict=100, temperature=0, response_format="json", stage="réécriture"))
        rewritten = data.get("question", "") if isinstance(data, dict) else ""
    except httpx.TimeoutException:
        raise
    except (httpx.HTTPError, json.JSONDecodeError, AttributeError, TypeError):
        return question
    return rewritten.strip()[:2000] if isinstance(rewritten, str) and rewritten.strip() else question


def quick_reply(question: str, allow_chat_replies: bool = True) -> tuple[str, str] | None:
    """Réponses fixes courtes, de sécurité et de confidentialité."""
    lang = detect_lang(question)
    if allow_chat_replies and _GREETINGS.fullmatch(question):
        if re.search(r"\b(?:merci|thanks|thank you|misaotra)\b", question, re.I):
            return "CHAT", {
                "fr": "Avec plaisir.",
                "mg": "Tsy misy fisaorana.",
                "en": "You're welcome.",
            }[lang]
        greeting = {
            "fr": (f"Bonjour, je suis {ASSISTANT_NAME}, l'assistant IA de MHM Ambovo. "
                   "Comment puis-je vous aider ?"),
            "mg": (f"Salama, {ASSISTANT_NAME} aho, mpanampy IA an'ny MHM Ambovo. "
                   "Ahoana no azoko anampiana anao?"),
            "en": f"Hello, I'm {ASSISTANT_NAME}, the AI assistant at MHM Ambovo. How can I help?",
        }
        return "CHAT", greeting[lang]
    if EMERGENCY.search(question):
        return "CHAT", EMERGENCY_TEXT[lang]
    if PATIENT_RECORD.search(question):
        return "CHAT", PATIENT_MESSAGE[lang]
    if allow_chat_replies:
        for rule in undefined_terms():
            if re.search(rule["pattern"], question, re.I):
                return "CHAT", " ".join(rule["answer"].split())
    return None


def _deterministic(question: str) -> str:
    if _IDENTITY.search(question):
        return "chat"
    if _SUMMARY.search(question):
        return "chat"
    if _CORRECTION_OR_EXPLANATION.search(question) and not is_medical(question):
        return "chat"
    if _SQL.search(question) or re.search(r"\d", question):
        return "sql"
    if _DOCS.search(question) or (_DATA.search(question) and re.search(r"\b(?:quel|quelle|what|which)\b", question, re.I)):
        return "docs"
    return "chat"


def route(question: str, history=None) -> Route:
    """Réécrit le suivi avant les règles prioritaires et utilise CHAT par défaut."""
    standalone = rewrite_followup(question, history)
    quick = quick_reply(standalone)
    if quick:
        return Route("chat", standalone, quick[1])
    name = _deterministic(standalone)
    return Route(name, standalone)


def is_medical(text: str) -> bool:
    return bool(_MEDICAL.search(text))


def has_useful_content(text: str) -> bool:
    normalized = unicodedata.normalize("NFKC", text).strip()
    generic = re.compile(
        r"(?i)(?:je suis (?:ravi|heureux) de vous aider(?: avec vos questions(?: statistiques sur MHM)?)?|"
        r"je vais faire de mon mieux(?: pour (?:vous fournir des réponses claires et concises|vous aider))?|"
        r"n['’]hésitez pas à me poser vos questions"
        r"(?:,? (?:je suis là pour vous aider|et je ferai de mon mieux pour vous aider))?|"
        r"je suis là pour vous aider|i(?:'m| am) happy to help(?: with your questions)?|"
        r"i can help with that request|how can i help|comment puis-je vous aider(?: aujourd'hui)?|"
        r"qu'est-ce que vous souhaitez savoir sur MHM|what would you like to know about MHM|"
        r"je n'ai pas accès aux (?:données|bases(?: de données)?|documents)|"
        r"i (?:cannot|can't) access (?:the )?(?:data|database|documents))")
    sentences = re.split(r"[.!?]+", normalized)
    for sentence in sentences:
        sentence = re.sub(
            r"(?i)^\W*(?:bonjour|salut|bonsoir|hello|hi|hey|merci|thanks|thank you)\W*",
            "", sentence).strip()
        if len(re.findall(r"\w+", sentence)) >= 2 and not generic.fullmatch(sentence):
            return True
    return False


def guard_general(answer: str, question: str, history=None) -> str:
    """Évite les chiffres inventés et toute réponse médicale sans source documentaire."""
    lang = detect_lang(question)
    if _NO_ACCESS.search(answer):
        debug_trace("CHAT rejet", reason="déclaration d'accès interdite",
                    question=question, answer=answer)
        return ACCESS_REPLY[lang]
    capability_question = bool(_IDENTITY.search(question))
    summary_with_history = is_summary_request(question) and bool(history)
    medical_answer = (is_medical(answer) and bool(_MEDICAL_CONTENT.search(answer))
                      and not summary_with_history)
    if (is_medical(question) and not capability_question) or medical_answer:
        debug_trace("CHAT rejet", reason="garde-fou médical sans source",
                    question=question, answer=answer)
        return {
            "fr": "Je peux rechercher cette information dans les documents chargés.",
            "mg": "Afaka mikaroka izany ao amin'ireo antontan-taratasy nampidirina aho.",
            "en": "I can look for this information in the loaded documents.",
        }[lang]
    context = question + " " + " ".join(
        f"{q} {a}" for q, a in (history or [])[-10:])
    if numbers_in(answer) - numbers_in(context):
        debug_trace("CHAT rejet", reason="chiffre non vérifié", question=question, answer=answer)
        return NO_DATA_TEXT[detect_lang(question)]
    return answer
