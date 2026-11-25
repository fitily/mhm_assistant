import { defineStore } from 'pinia'
import * as api from '@/services/api'
import { useAuthStore } from './auth'

// Pendant 5 minutes, revenir sur la page n'interroge pas le serveur (qui a lui-même un cache).
const FRESH_MS = 5 * 60 * 1000

const blank = () => ({
  status: 'idle', // idle | loading | ready | error
  items: [],
  sources: [],
  generatedAt: null,
  loadedAt: 0,
  refreshing: false,
  error: '',
})

const pending = {} // une seule requête à la fois par flux

export const useFeedsStore = defineStore('feeds', {
  state: () => ({
    'breaking-news': blank(),
    research: blank(),
  }),
  actions: {
    /** kind : « breaking-news » ou « research ». `force` ignore le délai de fraîcheur. */
    load(kind, { force = false } = {}) {
      const slice = this[kind]
      if (pending[kind]) return pending[kind]
      if (!force && slice.status === 'ready' && Date.now() - slice.loadedAt < FRESH_MS) {
        return Promise.resolve()
      }

      const auth = useAuthStore()
      const hadItems = slice.items.length > 0
      slice.status = hadItems ? 'ready' : 'loading'
      slice.refreshing = hadItems
      slice.error = ''

      pending[kind] = api
        .getFeed(kind, { token: auth.token, refresh: force })
        .then((data) => {
          Object.assign(slice, data, { status: 'ready', loadedAt: Date.now() })
        })
        .catch((err) => {
          if (err.status === 401) return auth.logout()
          // On garde ce qui est déjà affiché : une erreur d'actualisation ne vide pas la page.
          slice.status = hadItems ? 'ready' : 'error'
          slice.error = err.message || 'Une erreur est survenue.'
        })
        .finally(() => {
          slice.refreshing = false
          delete pending[kind]
        })
      return pending[kind]
    },
    loadAll(options) {
      return Promise.all([this.load('breaking-news', options), this.load('research', options)])
    },
    reset() {
      this['breaking-news'] = blank()
      this.research = blank()
    },
  },
})
