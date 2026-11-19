// Rôles de l'application. Ils viennent du jeton émis par FastAPI à la connexion.
// Attention : masquer un bouton ici n'est qu'un confort d'affichage. La vraie protection est
// dans le backend (domain/permissions.py), qui refuse la demande même si l'interface la laisse passer.

export const ROLE_ADMIN = 'admin'
export const ROLE_DOCTOR = 'doctor'

const LABELS = {
  [ROLE_ADMIN]: 'Administrateur',
  [ROLE_DOCTOR]: 'Médecin',
}

// Questions proposées dans le chat selon le rôle (celles qui fonctionnent pour ce profil).
const SUGGESTIONS = {
  [ROLE_ADMIN]: [
    'Que peux-tu faire pour moi ?',
    'Donne-moi un tableau de répartition par région',
    'Combien de patients par district ?',
  ],
  [ROLE_DOCTOR]: [
    'Que peux-tu faire pour moi ?',
    'Que disent les documents sur la prévention ?',
    'Quel est le protocole pour le paludisme ?',
  ],
}

export const roleLabel = (role) => LABELS[role] || ''

export const suggestionsFor = (role) => SUGGESTIONS[role] || ['Que peux-tu faire pour moi ?']
