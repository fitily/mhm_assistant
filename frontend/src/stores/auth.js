import { defineStore } from 'pinia'
import * as api from '@/services/api'

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
