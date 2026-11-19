// Rôles de l'application. Ils viennent du jeton émis par FastAPI à la connexion.
// Attention : masquer un bouton ici n'est qu'un confort d'affichage. La vraie protection est
// dans le backend (domain/permissions.py), qui refuse la demande même si l'interface la laisse passer.

export const ROLE_ADMIN = 'admin'
export const ROLE_DOCTOR = 'doctor'

const LABELS = {
  [ROLE_ADMIN]: 'Administrator',
  [ROLE_DOCTOR]: 'Doctor',
}

// Questions proposées dans le chat selon le rôle (celles qui fonctionnent pour ce profil).
// C'est ici que se règlent les suggestions affichées : `suggestions` de stores/chat.js n'est plus utilisé.
const SUGGESTIONS = {
  [ROLE_ADMIN]: [
    'Who are you?',
    'How many patients are there at MHM ?',
    'Give me the number of visits at MHM in June 2026',
  ],
  [ROLE_DOCTOR]: [
    'Who are you?',
    'What are the symptoms of HIV?',
  ],
}

export const roleLabel = (role) => LABELS[role] || ''

export const suggestionsFor = (role) => SUGGESTIONS[role] || ['Who are you?']
