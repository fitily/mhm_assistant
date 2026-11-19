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
