import { ApiError } from './errors'
import * as mock from './mock'

// Le navigateur appelle /api/... ; le proxy (Vite en dev, nginx en prod) retire "/api"
// et transmet au backend FastAPI (ex. /api/v1/chat -> http://localhost:8000/v1/chat).
const BASE = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '')

// Deux interrupteurs indépendants :
//  - VITE_MOCK_AUTH=true : fausse connexion (démonstration, sans backend)
//  - VITE_MOCK_CHAT=true : fausses réponses du chat (sans backend)
const MOCK_AUTH = import.meta.env.VITE_MOCK_AUTH === 'true'
const MOCK_CHAT = import.meta.env.VITE_MOCK_CHAT === 'true'

// Route de connexion réelle (FastAPI) : chemin relatif à BASE, ou URL complète.
const LOGIN_URL = import.meta.env.VITE_LOGIN_URL || '/v1/auth/login'

export const isMockAuth = MOCK_AUTH
export const isMockChat = MOCK_CHAT

function defaultMessage(status) {
  if (status === 401) return 'Session expirée ou identifiants invalides.'
  if (status === 403) return 'Accès refusé.'
  if (status === 422) return 'Requête invalide. Vérifiez votre message.'
  if (status === 429) return 'Trop de requêtes. Réessayez dans un instant.'
  if (status >= 500) return 'Le serveur a rencontré une erreur. Réessayez plus tard.'
  return 'Une erreur est survenue.'
}

async function request(path, { method = 'GET', body, token } = {}) {
  const url = /^https?:\/\//.test(path) ? path : `${BASE}${path}`
  let response
  try {
    response = await fetch(url, {
      method,
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
    })
  } catch {
    throw new ApiError('Impossible de joindre le serveur. Vérifiez qu’il est démarré.', 0)
  }

  let data = null
  try {
    data = await response.json()
  } catch {
    /* réponse sans JSON */
  }

  if (!response.ok) {
    // FastAPI renvoie { "detail": "..." } (texte) ou { "detail": [ ... ] } (erreurs de validation)
    const detail = typeof data?.detail === 'string' ? data.detail : data?.message
    throw new ApiError(detail || defaultMessage(response.status), response.status)
  }
  return data
}

/**
 * Connexion.
 * - Mode fictif : identifiants de démonstration, jeton factice.
 * - Mode réel : POST /v1/auth/login { username, password }
 *   -> { access_token, expires_in, user: { email, name, role } }   (role : "doctor" ou "admin")
 */
export async function login(username, password) {
  if (MOCK_AUTH) return mock.login(username, password)

  const data = await request(LOGIN_URL, { method: 'POST', body: { username, password } })
  const token = data?.access_token || data?.token
  if (!token) throw new ApiError('Réponse de connexion invalide.', 500)
  const user = data.user || {}
  return {
    token,
    user: {
      name: user.name || username,
      email: user.email || username,
      role: user.role || null,
    },
  }
}

/**
 * POST /v1/chat  { question, session_id }
 * Réponse du backend : { text, sender, mode, sql, notes[], sources[{score,label}], data{columns,rows} }
 */
export async function sendMessage({ message, sessionId, token }) {
  const data = MOCK_CHAT
    ? await mock.sendMessage({ message, sessionId })
    : await request('/v1/chat', {
        method: 'POST',
        token,
        body: { question: message, session_id: sessionId },
      })

  const table = data?.data?.columns?.length ? data.data : null
  return {
    answer: data?.text || '',
    mode: data?.mode || null,
    sources: (data?.sources || []).map((s) => ({ label: s.label, score: s.score })),
    table,
    notes: data?.notes || [],
    action: data?.action || null, // ordre pour l'interface (ex. ouvrir un dashboard)
  }
}

/** POST /v1/clear : efface la mémoire de la conversation côté serveur (sans bloquer si ça échoue). */
export async function clearSession({ sessionId, token }) {
  if (MOCK_CHAT || !sessionId) return
  try {
    await request('/v1/clear', { method: 'POST', token, body: { session_id: sessionId } })
  } catch {
    /* ce n'est pas bloquant */
  }
}

/** GET /v1/kpis (admin) -> [{ key, label, value (nombre ou null), hint, delta_percent, error }] */
export function fetchKpis({ token }) {
  return request('/v1/kpis', { token })
}

/** GET /v1/superset/dashboards (admin) -> [{ key, title, description, available }] */
export function fetchDashboards({ token }) {
  return request('/v1/superset/dashboards', { token })
}

/**
 * POST /v1/superset/guest-token (admin) { dashboard: <clé du catalogue> }
 * -> { dashboard_key, dashboard_id (UUID), token, expires_at, superset_domain }
 * Le navigateur n'envoie qu'une CLÉ ; l'UUID est retrouvé par le backend.
 */
export function fetchGuestAccess({ key, token }) {
  return request('/v1/superset/guest-token', { method: 'POST', token, body: { dashboard: key } })
}
