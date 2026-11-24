"""Détection des commandes de tableau de bord : ce qui en est une, et surtout ce qui n'en est PAS une."""
import pytest

from app.domain.dashboard_catalog import Dashboard
from app.domain.dashboard_intent import detect, normalize

UUID_A = "b973604e-c78d-47ce-8fdf-876722c1aaed"
UUID_B = "7893e593-7f0c-481f-8326-8e2843abe736"
VISITE = Dashboard("visite", "AI-assistant-dashboard", UUID_A, "", ("visite", "visites", "visits", "consultations"))
MEDICAL = Dashboard("medicale", "HMH_Medical_Dashboard", UUID_B, "", ("medical", "medicale", "health"))
BOTH = [VISITE, MEDICAL]


def test_normalize_strips_accents_and_punctuation():
    assert normalize("Ouvre le tableau de bord MÉDICAL, d'avant !") == "ouvre le tableau de bord medical, d avant !"
    assert normalize("HMH_Medical_Dashboard") == "hmh medical dashboard"


@pytest.mark.parametrize("question,intent,key", [
    ("Montre-moi le tableau de bord des visites", "show_dashboard", "visite"),
    ("Ouvre le dashboard médical", "show_dashboard", "medicale"),
    ("Affiche le tableau de bord médical s'il te plaît", "show_dashboard", "medicale"),
    ("Show me the visits dashboard", "show_dashboard", "visite"),
    ("Open the medical dashboard", "show_dashboard", "medicale"),
    ("Display dashboard HMH_Medical_Dashboard", "show_dashboard", "medicale"),
    ("Asehoy ny dashboard visite", "show_dashboard", "visite"),
    ("Passe au tableau de bord médical", "switch_dashboard", "medicale"),
    ("Switch to the visits dashboard", "switch_dashboard", "visite"),
    ("Change de tableau de bord pour les visites", "switch_dashboard", "visite"),
])
def test_open_and_switch_commands_find_the_right_dashboard(question, intent, key):
    command = detect(question, BOTH)
    assert command and command.intent == intent
    assert command.dashboard and command.dashboard.key == key


@pytest.mark.parametrize("question", [
    "Ferme le tableau de bord", "Close the dashboard", "Masque le dashboard", "Akatony ny dashboard",
])
def test_close_commands(question):
    command = detect(question, BOTH)
    assert command and command.intent == "close_dashboard"


@pytest.mark.parametrize("question", [
    "Reviens au tableau de bord précédent", "Go back to the previous dashboard",
    "Retourne au dashboard d'avant", "Montre le dashboard précédent",
])
def test_previous_commands(question):
    command = detect(question, BOTH)
    assert command and command.intent == "switch_dashboard" and command.previous


def test_without_target_it_asks_which_one():
    command = detect("Montre-moi un tableau de bord", BOTH)
    assert command and command.dashboard is None
    assert [d.key for d in command.choices] == ["visite", "medicale"]


def test_with_a_single_dashboard_no_need_to_ask():
    command = detect("Show me the dashboard", [MEDICAL])
    assert command and command.dashboard.key == "medicale"


def test_two_dashboards_mentioned_means_ask():
    command = detect("Ouvre le dashboard visites et médical", BOTH)
    assert command and command.dashboard is None and len(command.choices) == 2


def test_unknown_name_never_invents_a_dashboard():
    command = detect("Ouvre le dashboard secret_rh", BOTH)
    assert command.dashboard is None
    assert {d.key for d in command.choices} == {"visite", "medicale"}  # on propose seulement le catalogue


def test_empty_catalog_gives_no_choice():
    command = detect("Ouvre le dashboard", [])
    assert command and command.dashboard is None and command.choices == ()


@pytest.mark.parametrize("question", [
    # questions chiffrées : restent des questions statistiques
    "Combien de visites y a-t-il dans le tableau de bord ?",
    "How many visits does the dashboard show?",
    "Montre-moi le nombre de visites du tableau de bord",
    # pas de « tableau de bord » / « dashboard » : jamais un dashboard
    "Affiche un tableau des patients par district",
    "Give me the number of visits at MHM in June 2026",
    "Montre-moi les symptômes du VIH",
    "Ouvre la fenêtre",
    # parle d'un dashboard sans le demander
    "C'est quoi un tableau de bord ?",
    "What is a dashboard?",
    "Qui es-tu ?", "Bonjour", "Who are you?",
    # « précédent » au sens du temps, pas d'un dashboard
    "Dashboard du mois précédent",
    # trop long pour être une commande
    "Montre le tableau de bord " + "et ensuite je voudrais comprendre " * 8,
])
def test_not_a_dashboard_command(question):
    assert detect(question, BOTH) is None


def test_previous_month_is_not_previous_dashboard():
    command = detect("Show me the dashboard for last month", BOTH)
    assert command is None or not command.previous


# --- liste du catalogue et phrases courtes après une commande -------------------------------------

@pytest.mark.parametrize("question", [
    "how many dashboard do you have there to show?",
    "Combien de tableaux de bord avez-vous ?",
    "What dashboards do you have?",
    "Quels tableaux de bord sont disponibles ?",
    "List the dashboards",
    "Dashboards disponibles",
])
def test_catalog_questions_list_the_dashboards(question):
    command = detect(question, BOTH)
    assert command is not None and command.intent == "list_dashboards"
    assert command.listing == tuple(BOTH)


@pytest.mark.parametrize("question", [
    "Combien de visites dans le dashboard ?",
    "How many patients are in the dashboard?",
    "What is a dashboard?",
])
def test_statistics_about_dashboard_content_are_not_listings(question):
    assert detect(question, BOTH) is None


@pytest.mark.parametrize("question,previous,intent", [
    ("go back to the previous one", True, "switch_dashboard"),
    ("Reviens au précédent", True, "switch_dashboard"),
    ("the previous one", True, "switch_dashboard"),
    ("close it", False, "close_dashboard"),
    ("Ferme-le", False, "close_dashboard"),
])
def test_short_phrases_work_only_right_after_a_dashboard_command(question, previous, intent):
    assert detect(question, BOTH) is None
    command = detect(question, BOTH, after_dashboard=True)
    assert command is not None and command.intent == intent and command.previous is previous


def test_short_phrases_do_not_swallow_other_questions_after_a_dashboard():
    assert detect("How many patients are there at MHM?", BOTH, after_dashboard=True) is None
    assert detect("Go back to the previous quarter data for visits in the region of Analamanga", BOTH,
                  after_dashboard=True) is None


@pytest.mark.parametrize("question", [
    "generate for me a dashboard about patients by district",
    "Crée un tableau de bord des patients",
    "Build a dashboard of visits",
])
def test_creation_requests_are_detected(question):
    assert detect(question, BOTH).intent == "create_dashboard"
