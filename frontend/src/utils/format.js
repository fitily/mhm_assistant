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

const DAY_MS = 86_400_000
const dayKey = (date) => new Intl.DateTimeFormat('en-CA').format(date) // « 2026-11-26 », selon le fuseau du navigateur

/** « Today », « Yesterday », ou « Mon, 24 Nov » : libellé du jour d'une date ISO (invalide -> chaîne vide). */
export function dayLabel(iso, now = new Date()) {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return ''
  if (dayKey(date) === dayKey(now)) return 'Today'
  if (dayKey(date) === dayKey(new Date(now.getTime() - DAY_MS))) return 'Yesterday'
  return new Intl.DateTimeFormat('en-GB', { weekday: 'short', day: 'numeric', month: 'short' }).format(date)
}

/** Clé de regroupement par jour (même jour -> même clé). */
export const dayGroupKey = (iso) => (Number.isNaN(new Date(iso).getTime()) ? '' : dayKey(new Date(iso)))

/** « 19 Nov » : jour et mois courts. */
export function shortDate(iso) {
  const date = new Date(iso)
  return Number.isNaN(date.getTime()) ? '' : new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short' }).format(date)
}
