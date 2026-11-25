// Les rôles sont gérés par Laravel : le frontend ne fait que les lire (champ `role` ou `roles`
// de l'utilisateur renvoyé à la connexion) et choisir la bonne page d'accueil.

const ALIASES = {
  doctor: ['medecin', 'doctor', 'physician', 'docteur', 'dr'],
}

export const ROLE_LABELS = {
  doctor: 'Médecin',
}

const slug = (value) =>
  String(value || '')
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .trim()
    .toLowerCase()

/** Accepte « Médecin », « medecin », « doctor »… et retourne un identifiant stable (« doctor »). */
export function normalizeRole(raw) {
  const value = slug(raw)
  if (!value) return null
  for (const [role, names] of Object.entries(ALIASES)) {
    if (names.includes(value)) return role
  }
  return value
}

/** Laravel peut renvoyer `role: "medecin"`, `roles: ["medecin"]` ou `roles: [{ name: "medecin" }]`. */
export function extractRole(user) {
  if (!user) return null
  const candidate = user.role ?? (Array.isArray(user.roles) ? user.roles[0] : user.roles)
  return normalizeRole(typeof candidate === 'object' && candidate ? candidate.name : candidate)
}
