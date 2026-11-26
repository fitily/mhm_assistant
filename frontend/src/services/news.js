// Point d'entrée unique des actualités médicales.
import { fetchNewsFeed } from './api'

export const NEWS_CATEGORIES = [
  { key: 'all', label: 'All' },
  { key: 'breaking', label: 'Breaking' },
  { key: 'research', label: 'Research' },
  { key: 'update', label: 'Medical updates' },
]

const PREVIEW = import.meta.env.VITE_NEWS_PREVIEW === 'true'
const PREVIEW_SOURCES = [
  { key: 'who', label: 'WHO', url: 'https://www.who.int/news', connected: false },
  { key: 'who-africa', label: 'WHO Africa', url: 'https://www.afro.who.int/outbreaks-and-emergencies-updates', connected: false },
  { key: 'lancet', label: 'The Lancet', url: 'https://www.thelancet.com/', connected: false },
  { key: 'nejm', label: 'NEJM', url: 'https://www.nejm.org/', connected: false },
]

const ago = (hours) => new Date(Date.now() - hours * 3_600_000).toISOString()

// Exemples génériques pour juger la mise en page. Jamais affichés hors mode aperçu.
const SAMPLE = [
  { id: 's1', category: 'breaking', title: 'Sample headline for a breaking medical alert', summary: 'Placeholder text. A short summary of the alert will appear here once the live feed is connected.', source: 'Sample source', hours: 1 },
  { id: 's2', category: 'research', title: 'Sample headline for a recent research publication', summary: 'Placeholder text. Key findings, journal and authors will be summarised on this card.', source: 'Sample journal', hours: 6 },
  { id: 's3', category: 'update', title: 'Sample headline for an official health update', summary: 'Placeholder text. Guidelines, recommendations and public health notices will appear in this format.', source: 'Sample organisation', hours: 20 },
  { id: 's4', category: 'research', title: 'Another sample research headline, a little longer to check how long titles wrap on two lines', summary: 'Placeholder text for layout testing only.', source: 'Sample journal', hours: 30 },
  { id: 's5', category: 'update', title: 'Sample medical update headline', summary: 'Placeholder text for layout testing only.', source: 'Sample organisation', hours: 52 },
  { id: 's6', category: 'research', title: 'Sample research headline', summary: 'Placeholder text for layout testing only.', source: 'Sample journal', hours: 75 },
]

/**
 * @param {{category?: string, query?: string}} filters
 * @returns {Promise<{items: Array, updatedAt: string|null, connected: boolean, sources: Array, windowDays: number, since: string|null}>}
 *   `windowDays` / `since` : période affichée (les N derniers jours), calculée par le backend d'après la date de PUBLICATION.
 */
export async function fetchNews({ category = 'all', query = '', token } = {}) {
  if (!PREVIEW) {
    const data = await fetchNewsFeed({ category, query, token })
    return {
      items: data.items || [],
      updatedAt: data.updated_at || null,
      connected: Boolean(data.connected),
      sources: data.sources || [],
      windowDays: data.window_days || 7,
      since: data.since || null,
    }
  }

  const q = query.trim().toLowerCase()
  const items = SAMPLE.map(({ hours, ...a }) => ({ ...a, url: null, published_at: ago(hours) })).filter(
    (a) => (category === 'all' || a.category === category) && (!q || `${a.title} ${a.summary}`.toLowerCase().includes(q)),
  )
  const since = new Date()
  since.setHours(0, 0, 0, 0)
  since.setDate(since.getDate() - 7)
  return { items, updatedAt: new Date().toISOString(), connected: false, sources: PREVIEW_SOURCES, windowDays: 7, since: since.toISOString() }
}
