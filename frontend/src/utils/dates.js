const MINUTE = 60
const HOUR = 3600
const DAY = 86400

const dateFormat = new Intl.DateTimeFormat('fr-FR', { day: 'numeric', month: 'short', year: 'numeric' })
const longDateFormat = new Intl.DateTimeFormat('fr-FR', {
  weekday: 'long',
  day: 'numeric',
  month: 'long',
  year: 'numeric',
})
const relative = new Intl.RelativeTimeFormat('fr', { numeric: 'auto' })

function toDate(value) {
  if (!value) return null
  const date = value instanceof Date ? value : new Date(value)
  return Number.isNaN(date.getTime()) ? null : date
}

export function formatDate(value) {
  const date = toDate(value)
  return date ? dateFormat.format(date) : ''
}

export function formatLongDate(value = new Date()) {
  const date = toDate(value)
  return date ? longDateFormat.format(date) : ''
}

/** « il y a 5 minutes », « hier », puis la date complète au-delà d'une semaine. */
export function timeAgo(value, now = Date.now()) {
  const date = toDate(value)
  if (!date) return ''
  const seconds = Math.round((now - date.getTime()) / 1000)
  if (seconds < 0) return formatDate(date) // date future (« à paraître ») : on affiche la date
  if (seconds < MINUTE) return 'à l’instant'
  if (seconds < HOUR) return relative.format(-Math.floor(seconds / MINUTE), 'minute')
  if (seconds < DAY) return relative.format(-Math.floor(seconds / HOUR), 'hour')
  if (seconds < 7 * DAY) return relative.format(-Math.floor(seconds / DAY), 'day')
  return formatDate(date)
}

/** Nom de domaine lisible d'un lien (« who.int »), pour indiquer où mène le lien. */
export function hostOf(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return ''
  }
}
