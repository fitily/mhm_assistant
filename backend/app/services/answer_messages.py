"""Localized fallback messages used by chat answer generators."""

NO_DOC = {
    "fr": "Je ne trouve pas cette information dans les documents disponibles.",
    "en": "I cannot find this information in the available documents.",
    "mg": "Tsy hitako ao amin'ireo antontan-taratasy misy izany.",
}
DOCS_DOWN = {
    "fr": "La base documentaire n'est pas disponible pour le moment.",
    "en": "The document base is not available at the moment.",
    "mg": "Tsy misy amin'izao fotoana izao ny tahirin-kevitra.",
}
ANALYSIS_DOWN = {
    "fr": "L'analyse n'est pas disponible pour le moment.",
    "en": "The analysis is not available at the moment.",
    "mg": "Tsy misy amin'izao fotoana izao ny fanadihadiana.",
}
OUT_OF_RANGE = {
    "fr": "La période demandée est en dehors de la plage de données disponible.",
    "en": "The requested period is outside the available data range.",
    "mg": "Any ivelan'ny fe-potoana misy ny angona ny vanim-potoana nangatahana.",
}
NO_RESULT = {
    "fr": "Aucun résultat.",
    "en": "No results.",
    "mg": "Tsy misy valiny.",
}
LLM_DOWN = {
    "fr": "Le modèle de langage n'est pas disponible pour le moment. Réessayez dans un instant.",
    "en": "The language model is not available at the moment. Please try again shortly.",
    "mg": "Tsy misy amin'izao fotoana izao ny maodely fiteny. Andramo indray afaka kelikely.",
}
LLM_TIMEOUT = {
    "fr": "Le délai d’attente de l’IA a été dépassé.",
    "en": "The AI request timed out.",
    "mg": "Nihoatra ny fe-potoana fiandrasana ny fangatahana tamin'ny IA.",
}
ANALYSIS_ERROR = {
    "fr": "L'analyse a échoué. Aucun chiffre n'a été calculé.",
    "en": "The analysis failed. No figures were calculated.",
    "mg": "Tsy nahomby ny fanadihadiana. Tsy nisy tarehimarika voakajy.",
}
NO_VALUE = {
    "fr": "Aucune valeur numérique n'est disponible.",
    "en": "No numeric value is available.",
    "mg": "Tsy misy sanda isa azo ampiasaina.",
}
SINGLE_VALUE = {
    "fr": "Le nombre correspondant est {value}.",
    "en": "The matching number is {value}.",
    "mg": "Izao ny isa mifanaraka amin'izany: {value}.",
}
RESULTS_CALCULATED = {
    "fr": "Voici les résultats calculés.",
    "en": "Here are the calculated results.",
    "mg": "Ireto ny valin'ny kajy.",
}
# Refus selon le rôle : un médecin n'a pas les statistiques, un administrateur n'a pas les documents.
MODE_FORBIDDEN = {
    "SQL": {
        "fr": ("Les statistiques ne sont pas disponibles pour votre profil (médecin). "
               "Je peux répondre à vos questions de santé à partir des documents chargés. "
               "Pour obtenir des chiffres, contactez un administrateur."),
        "en": ("Statistics are not available for your profile (doctor). "
               "I can answer your health questions using the loaded documents. "
               "To get figures, please contact an administrator."),
        "mg": ("Tsy azo ampiasaina amin'ny mombamomba anao (dokotera) ny antontan'isa. "
               "Afaka mamaly ny fanontaniana ara-pahasalamana avy amin'ireo antontan-taratasy "
               "nampidirina aho. Raha mila tarehimarika ianao, mifandraisa amin'ny mpitantana."),
    },
    "DOCS": {
        "fr": ("Les questions de santé fondées sur les documents ne sont pas disponibles pour "
               "votre profil (administrateur). Je peux répondre aux questions statistiques sur "
               "les patients, consultations, sorties et diagnostics."),
        "en": ("Document-based health questions are not available for your profile "
               "(administrator). I can answer statistical questions about patients, "
               "consultations, discharges and diagnoses."),
        "mg": ("Tsy azo ampiasaina amin'ny mombamomba anao (mpitantana) ny fanontaniana "
               "ara-pahasalamana mifototra amin'ny antontan-taratasy. Afaka mamaly fanontaniana "
               "momba ny antontan'isa ny marary, ny fizahana, ny fivoahana ary ny aretina aho."),
    },
}
MODE_FORBIDDEN["DASHBOARD"] = {
    "fr": ("Les tableaux de bord ne sont pas disponibles pour votre profil (médecin). "
           "Je peux répondre à vos questions de santé à partir des documents chargés. "
           "Pour consulter un tableau de bord, contactez un administrateur."),
    "en": ("Dashboards are not available for your profile (doctor). "
           "I can answer your health questions using the loaded documents. "
           "To view a dashboard, please contact an administrator."),
    "mg": ("Tsy azo ampiasaina amin'ny mombamomba anao (dokotera) ny dashboard. "
           "Afaka mamaly ny fanontaniana ara-pahasalamana avy amin'ireo antontan-taratasy "
           "nampidirina aho. Raha mila mijery dashboard ianao, mifandraisa amin'ny mpitantana."),
}
ACCESS_DENIED = {
    "fr": "Accès refusé pour votre profil.",
    "en": "Access denied for your profile.",
    "mg": "Tsy azonao ampiasaina izany amin'ny mombamomba anao.",
}
