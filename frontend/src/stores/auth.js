import { defineStore } from 'pinia'
import * as api from '@/services/api'
import { extractRole, ROLE_LABELS } from '@/utils/roles'

const KEY = 'mhm_auth'

function load() {
  try {
    return JSON.parse(localStorage.getItem(KEY)) || null
  } catch {
    return null
  }
}

export const useAuthStore = defineStore('auth', {
  state: () => {
    const saved = load()
    return { token: saved?.token || null, user: saved?.user || null }
  },
  getters: {
    isAuthenticated: (state) => !!state.token,
    displayName: (state) => state.user?.name || state.user?.email || 'Utilisateur',
    /** Identifiant normalisé du rôle (« doctor »…) ou null si l'utilisateur n'en a pas. */
    role: (state) => extractRole(state.user),
    roleLabel() {
      return ROLE_LABELS[this.role] || ''
    },
  },
  actions: {
    async login(username, password) {
      const { token, user } = await api.login(username.trim(), password)
      this.token = token
      this.user = user
      localStorage.setItem(KEY, JSON.stringify({ token, user }))
    },
    logout() {
      this.token = null
      this.user = null
      localStorage.removeItem(KEY)
    },
  },
})
