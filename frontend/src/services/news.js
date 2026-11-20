// Point d'entrée unique des actualités médicales.
// ÉTAT ACTUEL : aucun flux réel. `fetchNews` renvoie une liste vide, sauf si VITE_NEWS_PREVIEW=true
// (aperçu du design avec des cartes d'exemple, clairement génériques et non médicales).
//
// CONTRAT pour l'intégration (étape suivante) — il suffit de remplacer le corps de `fetchNews` :
//   GET /v1/news?category=&q=  ->  { items: Article[], updated_at: ISO }
//   Article = { id, title, summary, source, url, published_at (ISO), category, image? }
//   category ∈ NEWS_CATEGORIES (hors « all »). Temps réel possible plus tard (SSE/WebSocket) : le view
//   n'a qu'à ajouter les nouveaux articles à `items`.

export const NEWS_CATEGORIES = [
  { key: 'all', label: 'All' },
  { key: 'breaking', label: 'Breaking' },
  { key: 'research', label: 'Research' },
  { key: 'update', label: 'Medical updates' },
]

export const NEWS_CONNECTED = false
const PREVIEW = import.meta.env.VITE_NEWS_PREVIEW === 'true'

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
 * @returns {Promise<{items: Array, updatedAt: string|null, connected: boolean}>}
 */
export async function fetchNews({ category = 'all', query = '' } = {}) {
  if (!PREVIEW) return { items: [], updatedAt: null, connected: NEWS_CONNECTED }

  const q = query.trim().toLowerCase()
  const items = SAMPLE.map(({ hours, ...a }) => ({ ...a, url: null, published_at: ago(hours) })).filter(
    (a) => (category === 'all' || a.category === category) && (!q || `${a.title} ${a.summary}`.toLowerCase().includes(q)),
  )
  return { items, updatedAt: new Date().toISOString(), connected: false }
}
