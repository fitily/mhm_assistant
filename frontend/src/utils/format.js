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

/** 12345 -> « 12 345 » (même style que les chiffres du chat). Tiret si la valeur n'est pas un nombre. */
export function formatNumber(value) {
  return Number.isFinite(value) ? new Intl.NumberFormat('fr-FR').format(value) : '—'
}

/** 8.3 -> « +8,3 % » ; -2 -> « −2 % » ; null -> chaîne vide. */
export function formatTrend(percent) {
  if (!Number.isFinite(percent)) return ''
  const sign = percent > 0 ? '+' : percent < 0 ? '−' : ''
  return `${sign}${new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 1 }).format(Math.abs(percent))} %`
}

/** « 19 Nov » : jour et mois courts. */
export function shortDate(iso) {
  const date = new Date(iso)
  return Number.isNaN(date.getTime()) ? '' : new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short' }).format(date)
}

/** « 25 Nov 2026 » : date de publication affichée sur chaque article (jour seulement : certaines sources n'ont pas d'heure). */
export function formatDate(iso) {
  const date = new Date(iso)
  return Number.isNaN(date.getTime())
    ? ''
    : new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }).format(date)
}
