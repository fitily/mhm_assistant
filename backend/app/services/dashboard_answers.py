"""Réponses du chat aux commandes de tableau de bord (voir domain/dashboard_intent.py).

Le backend ne garde aucun état : il renvoie un texte et une « action » que l'interface exécute.
  {"type": "open_dashboard", "dashboard": "<clé du catalogue>", "title": "..."}
  {"type": "close_dashboard"}
  {"type": "previous_dashboard"}
L'action ne contient jamais d'UUID ni d'URL : l'interface passe par /v1/superset/guest-token (admin).
"""
from __future__ import annotations

from app.domain.dashboard_intent import DashboardCommand
from app.domain.models import AnswerResult

MODE = "DASHBOARD"

OPENING = {
    "fr": "J'ouvre le tableau de bord « {title} ».",
    "en": "Opening the “{title}” dashboard.",
    "mg": "Sokafako ny dashboard « {title} ».",
}
CLOSING = {
    "fr": "Je ferme le tableau de bord.",
    "en": "Closing the dashboard.",
    "mg": "Akatoko ny dashboard.",
}
PREVIOUS = {
    "fr": "Je reviens au tableau de bord précédent.",
    "en": "Going back to the previous dashboard.",
    "mg": "Miverina amin'ny dashboard teo aloha aho.",
}
ASK_WHICH = {
    "fr": "Quel tableau de bord souhaitez-vous voir ? Disponibles : {titles}.",
    "en": "Which dashboard would you like to see? Available: {titles}.",
    "mg": "Dashboard iza no tianao jerena? Misy: {titles}.",
}
NONE_AVAILABLE = {
    "fr": "Aucun tableau de bord n'est disponible pour le moment.",
    "en": "No dashboard is available at the moment.",
    "mg": "Tsy misy dashboard azo jerena amin'izao fotoana izao.",
}


LISTING = {
    "fr": "Il y a {n} tableau(x) de bord disponible(s) :\n{items}\nDites par exemple « ouvre le tableau de bord {key} ».",
    "en": "There are {n} dashboard(s) available:\n{items}\nFor example, say “open the {key} dashboard”.",
    "mg": "Misy dashboard {n} azo jerena:\n{items}\nOhatra: « sokafy ny dashboard {key} ».",
}


def _listing(command: DashboardCommand, language: str) -> AnswerResult:
    dashboards = command.listing
    if not dashboards:
        return AnswerResult(NONE_AVAILABLE[language], MODE, audit_stage="dashboard_none")
    items = "\n".join(f"- « {d.title} »" + (f" : {d.description}" if d.description else "") for d in dashboards)
    text = LISTING[language].format(n=len(dashboards), items=items, key=dashboards[0].key)
    return AnswerResult(text, MODE, audit_stage="dashboard_list")


def build(command: DashboardCommand, language: str) -> AnswerResult:
    if command.intent == "list_dashboards":
        return _listing(command, language)
    if command.intent == "close_dashboard":
        return AnswerResult(CLOSING[language], MODE, audit_stage="dashboard_close",
                            action={"type": "close_dashboard"})
    if command.previous:
        return AnswerResult(PREVIOUS[language], MODE, audit_stage="dashboard_previous",
                            action={"type": "previous_dashboard"})
    if command.dashboard is not None:
        d = command.dashboard
        return AnswerResult(OPENING[language].format(title=d.title), MODE,
                            audit_stage=f"dashboard_open:{d.key}",
                            action={"type": "open_dashboard", "dashboard": d.key, "title": d.title})
    if command.choices:
        titles = ", ".join(f"« {d.title} »" for d in command.choices)
        return AnswerResult(ASK_WHICH[language].format(titles=titles), MODE, audit_stage="dashboard_ask")
    return AnswerResult(NONE_AVAILABLE[language], MODE, audit_stage="dashboard_none")
