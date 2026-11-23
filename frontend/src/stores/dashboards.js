// État des tableaux de bord Superset côté navigateur : lequel est ouvert, et la pile des précédents.
// Le backend ne garde aucun état : le chat renvoie une « action » (voir backend/app/services/dashboard_answers.py)
// et c'est ce store qui l'exécute. Rien n'est conservé après la déconnexion.
import { defineStore } from 'pinia'
import { useAuthStore } from './auth'

const MAX_HISTORY = 10
const KEY_RE = /^[a-z][a-z0-9_-]{1,30}$/ // même forme que les clés du catalogue (config/dashboards.yaml)

export const useDashboardStore = defineStore('dashboards', {
  state: () => ({
    current: null, // clé du dashboard affiché, ou null
    history: [], // clés des dashboards précédents (le dernier = le plus récent)
    closed: false, // l'utilisateur a demandé de fermer : on n'en rouvre pas un tout seul
  }),
  getters: {
    canGoBack: (state) => state.history.length > 0,
  },
  actions: {
    _remember(key) {
      if (!key) return
      this.history.push(key)
      if (this.history.length > MAX_HISTORY) this.history.shift()
    },
    /** Affiche le dashboard `key`. `remember: false` pour une sélection automatique (pas d'historique). */
    open(key, { remember = true } = {}) {
      if (!key) return
      if (this.current && this.current !== key && remember) this._remember(this.current)
      if (!this.current && this.history.at(-1) === key) this.history.pop() // évite un doublon après « fermer »
      this.current = key
      this.closed = false
    },
    /** Ferme le dashboard ; il reste dans l'historique pour « revenir au précédent ». */
    close() {
      if (this.current) this._remember(this.current)
      this.current = null
      this.closed = true
    },
    /** Revient au dashboard précédent. false s'il n'y en a pas. */
    previous() {
      const key = this.history.pop()
      if (!key) return false
      this.current = key
      this.closed = false
      return true
    },
    reset() {
      this.current = null
      this.history = []
      this.closed = false
    },
    /**
     * Exécute une action reçue du chat.
     * Retourne 'opened' | 'closed' | 'no_previous' | 'ignored'.
     * Défense en profondeur : seul un administrateur exécute ces actions, et la forme de l'action est vérifiée
     * (le backend refuse de toute façon un dashboard hors catalogue au moment de demander le jeton).
     */
    async apply(action) {
      if (!useAuthStore().isAdmin || !action || typeof action.type !== 'string') return 'ignored'

      const { default: router } = await import('@/router') // import tardif : évite un cycle router <-> stores
      const goToAnalytics = () =>
        router.push({ name: 'analytics', query: this.current ? { d: this.current } : {} })

      if (action.type === 'open_dashboard') {
        if (typeof action.dashboard !== 'string' || !KEY_RE.test(action.dashboard)) return 'ignored'
        this.open(action.dashboard)
        await goToAnalytics()
        return 'opened'
      }
      if (action.type === 'previous_dashboard') {
        if (!this.previous()) return 'no_previous'
        await goToAnalytics()
        return 'opened'
      }
      if (action.type === 'close_dashboard') {
        this.close()
        return 'closed'
      }
      return 'ignored'
    },
  },
})
