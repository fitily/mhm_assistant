// Petits formateurs d'affichage (en anglais, comme l'interface).
const UNITS = [
  ['day', 86_400_000],
  ['hour', 3_600_000],
  ['minute', 60_000],
]

/** « 3 hours ago », « 2 days ago »... à partir d'une date ISO. Chaîne vide si la date est invalide. */
export function timeAgo(iso, now = Date.now()) {
  const t = new Date(iso).getTime()
  if (Number.isNaN(t)) return ''
  const diff = Math.max(0, now - t)
  for (const [unit, ms] of UNITS) {
    const n = Math.floor(diff / ms)
    if (n >= 1) return `${n} ${unit}${n > 1 ? 's' : ''} ago`
  }
  return 'Just now'
}
