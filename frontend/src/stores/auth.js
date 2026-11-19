import { defineStore } from 'pinia'
import * as api from '@/services/api'
import { ROLE_ADMIN, ROLE_DOCTOR, roleLabel } from '@/utils/roles'

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
    role: (state) => state.user?.role || null,
    isAdmin: (state) => state.user?.role === ROLE_ADMIN,
    isDoctor: (state) => state.user?.role === ROLE_DOCTOR,
    roleLabel: (state) => roleLabel(state.user?.role),
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
