"""Détection (sans IA) des commandes de tableau de bord dans le chat.

  « montre / ouvre le tableau de bord des visites »   -> show_dashboard
  « passe au dashboard médical »                      -> switch_dashboard
  « reviens au tableau de bord précédent »            -> switch_dashboard (précédent)
  « ferme le dashboard »                              -> close_dashboard
  tout le reste (questions chiffrées, documents...)   -> None : le routage habituel (SQL / DOCS / CHAT) continue

Règles de sécurité et de précision :
 - il faut le mot « tableau de bord » ou « dashboard » (jamais « tableau » seul : « un tableau par district »
   est une question statistique) ET un verbe d'action ;
 - une question de quantité (« combien de visites dans le dashboard ? ») reste une question statistique ;
 - le dashboard visé est cherché UNIQUEMENT dans le catalogue (config/dashboards.yaml) : le chat ne peut
   jamais désigner autre chose, ni produire d'URL ou d'identifiant.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from app.domain.dashboard_catalog import Dashboard

MAX_COMMAND_CHARS = 160  # une commande est courte ; au-delà, c'est probablement une vraie question

_DASH = r"(?:tableaux? de bord|dashboards?)"
_DASH_RE = re.compile(rf"\b{_DASH}\b")
_QUANTITY = re.compile(
    r"\b(?:combien|how many|how much|nombre de|number of|count|pourcentage|percentage|taux|firy)\b")
_OPEN = re.compile(
    r"\b(?:montre|montres|montrer|montrez|affiche|afficher|affichez|ouvre|ouvrir|ouvrez|"
    r"visualise|visualiser|voir|fais moi voir|show|display|open|view|see|load|pull up|"
    r"asehoy|sokafy)\b")
_SWITCH = re.compile(
    r"\b(?:passe|passer|passez|bascule|basculer|basculez|change|changer|changez|switch|"
    r"go to|move to|aller|allez|navigate to)\b")
_CLOSE = re.compile(r"\b(?:ferme|fermer|fermez|masque|masquer|cache|cacher|close|hide|akatony)\b")
# « précédent » doit être collé à « dashboard » ou à un verbe de retour : « dashboard du mois précédent »
# ne doit pas être pris pour « revenir au dashboard d'avant ».
_PREVIOUS = re.compile(
    rf"(?:\b{_DASH}\s+(?:precedente?|previous|d avant)\b)"
    rf"|(?:\b(?:precedente?|previous|last|prior)\s+{_DASH}\b)"
    r"|(?:\b(?:retour|reviens|revenir|retourne|retourner|back|go back|return)\b.{0,25}"
    r"\b(?:precedente?|previous|last|avant)\b)")


@dataclass(frozen=True)
class DashboardCommand:
    intent: str                                  # show_dashboard | switch_dashboard | close_dashboard
    previous: bool = False                       # « revenir au précédent »
    dashboard: Dashboard | None = None           # dashboard identifié sans ambiguïté
    choices: tuple[Dashboard, ...] = ()          # plusieurs possibles (ou aucun précisé) : il faut demander


def normalize(text: str) -> str:
    """Minuscules, sans accents, apostrophes et tirets remplacés par des espaces."""
    decomposed = unicodedata.normalize("NFKD", text)
    plain = "".join(c for c in decomposed if not unicodedata.combining(c)).casefold()
    return " ".join(re.sub(r"[’'`_\-]", " ", plain).split())


def _mentions(text: str, dashboard: Dashboard) -> bool:
    terms = {normalize(dashboard.key), normalize(dashboard.title), *(normalize(k) for k in dashboard.keywords)}
    return any(re.search(rf"\b{re.escape(t)}\b", text) for t in terms if t)


def detect(question: str, dashboards: list[Dashboard]) -> DashboardCommand | None:
    """Commande de tableau de bord contenue dans `question`, ou None si ce n'en est pas une."""
    if len(question) > MAX_COMMAND_CHARS:
        return None
    text = normalize(question)
    if not _DASH_RE.search(text) or _QUANTITY.search(text):
        return None

    if _PREVIOUS.search(text):
        return DashboardCommand("switch_dashboard", previous=True)
    if _CLOSE.search(text):
        return DashboardCommand("close_dashboard")

    switching = bool(_SWITCH.search(text))
    if not (switching or _OPEN.search(text)):
        return None  # « c'est quoi un dashboard ? » : conversation normale
    intent = "switch_dashboard" if switching else "show_dashboard"

    matched = [d for d in dashboards if _mentions(text, d)]
    if len(matched) == 1:
        return DashboardCommand(intent, dashboard=matched[0])
    if not matched and len(dashboards) == 1:
        return DashboardCommand(intent, dashboard=dashboards[0])  # un seul possible : inutile de demander
    return DashboardCommand(intent, choices=tuple(matched or dashboards))
