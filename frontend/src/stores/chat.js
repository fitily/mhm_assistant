import { defineStore } from 'pinia'
import * as api from '@/services/api'
import { useAuthStore } from './auth'
import { useDashboardStore } from './dashboards'

const KEY = 'mhm_chat'
const MAX_CONVERSATIONS = 20
const MAX_MESSAGES_PER_CONVERSATION = 100
const EMPTY_MESSAGES = []
let counter = 0

const newId = () => `m${Date.now()}-${counter++}`
const newSessionId = () =>
  globalThis.crypto?.randomUUID?.() || `s${Date.now()}-${Math.random().toString(16).slice(2)}`

function titleFromMessages(messages) {
  const firstQuestion = messages.find((message) => message.role === 'user')?.content?.trim()
  if (!firstQuestion) return 'Nouvelle conversation'
  const title = firstQuestion.replace(/\s+/g, ' ')
  return title.length > 60 ? `${title.slice(0, 59).trimEnd()}…` : title
}

function makeConversation(sessionId = newSessionId(), messages = []) {
  return {
    id: sessionId,
    sessionId,
    title: titleFromMessages(messages),
    messages: messages.slice(-MAX_MESSAGES_PER_CONVERSATION),
    updatedAt: messages.at(-1)?.time || Date.now(),
  }
}

function load() {
  try {
    const saved = JSON.parse(sessionStorage.getItem(KEY))
    if (Array.isArray(saved?.conversations)) {
      const conversations = saved.conversations
        .filter((conversation) =>
          conversation && typeof conversation.id === 'string'
          && Array.isArray(conversation.messages))
        .map((conversation) => {
          const messages = conversation.messages.slice(-MAX_MESSAGES_PER_CONVERSATION)
          return {
            id: conversation.id,
            sessionId: typeof conversation.sessionId === 'string'
              ? conversation.sessionId
              : conversation.id,
            title: typeof conversation.title === 'string' && conversation.title.trim()
              ? conversation.title
              : titleFromMessages(messages),
            messages,
            updatedAt: Number(conversation.updatedAt) || Date.now(),
          }
        })
        .sort((a, b) => b.updatedAt - a.updatedAt)
        .slice(0, MAX_CONVERSATIONS)
      const activeId = conversations.some(
        (conversation) => conversation.id === saved.activeConversationId,
      )
        ? saved.activeConversationId
        : conversations[0]?.id || null
      return { conversations, activeConversationId: activeId }
    }

    if (Array.isArray(saved?.messages) && (saved.messages.length || saved.sessionId)) {
      const conversation = makeConversation(
        typeof saved.sessionId === 'string' ? saved.sessionId : newSessionId(),
        saved.messages,
      )
      return { conversations: [conversation], activeConversationId: conversation.id }
    }
  } catch {
    return { conversations: [], activeConversationId: null }
  }
  return { conversations: [], activeConversationId: null }
}

function appendMessage(conversation, message) {
  conversation.messages.push(message)
  if (conversation.messages.length > MAX_MESSAGES_PER_CONVERSATION) {
    conversation.messages.splice(0, conversation.messages.length - MAX_MESSAGES_PER_CONVERSATION)
  }
}

function clearRemoteSession(sessionId, token) {
  if (sessionId) api.clearSession({ sessionId, token })
}

export const useChatStore = defineStore('chat', {
  state: () => {
    const saved = load()
    return {
      isOpen: false,
      fullscreen: false, // fenêtre de chat en plein écran (lu par ChatWidget)
      unread: 0,
      conversations: saved.conversations,
      activeConversationId: saved.activeConversationId,
      loadingConversationIds: [],
      suggestions: [
        'How many patients are there at MHM ?',
        'Give me the number of visits at MHM in June 2026',
        'What are the symptoms of HIV?',
      ],
    }
  },
  getters: {
    activeConversation: (state) =>
      state.conversations.find((conversation) => conversation.id === state.activeConversationId),
    conversationHistory: (state) =>
      [...state.conversations].sort((a, b) => b.updatedAt - a.updatedAt),
    messages: (state) =>
      state.conversations.find((conversation) => conversation.id === state.activeConversationId)
        ?.messages || EMPTY_MESSAGES,
    sessionId: (state) =>
      state.conversations.find((conversation) => conversation.id === state.activeConversationId)
        ?.sessionId || null,
    loading: (state) => state.loadingConversationIds.includes(state.activeConversationId),
  },
  actions: {
    persist() {
      this.conversations.sort((a, b) => b.updatedAt - a.updatedAt)
      this.conversations = this.conversations.slice(0, MAX_CONVERSATIONS)
      if (!this.conversations.some(
        (conversation) => conversation.id === this.activeConversationId,
      )) {
        this.activeConversationId = this.conversations[0]?.id || null
      }

      try {
        sessionStorage.setItem(KEY, JSON.stringify({
          conversations: this.conversations,
          activeConversationId: this.activeConversationId,
        }))
      } catch {
        /* Le chat reste disponible en mémoire si le stockage est indisponible. */
      }
    },
    ensureConversation() {
      let conversation = this.activeConversation
      if (!conversation) {
        conversation = makeConversation()
        this.conversations.unshift(conversation)
        this.activeConversationId = conversation.id
      }
      return conversation
    },
    open() {
      this.isOpen = true
      this.unread = 0
    },
    /** Ouvre le chat directement en plein écran (boutons « Ask iA'mbovo » de la barre latérale et de l'accueil). */
    openFullscreen() {
      this.fullscreen = true
      this.open()
    },
    minimize() {
      this.isOpen = false
    },
    /** Bulle flottante : ouvre toujours la petite fenêtre (même si le chat avait été vu en plein écran). */
    toggle() {
      if (this.isOpen) {
        this.minimize()
        return
      }
      this.fullscreen = false
      this.open()
    },
    startConversation() {
      const current = this.activeConversation
      if (!current || current.messages.length) {
        const conversation = makeConversation()
        this.conversations.unshift(conversation)
        this.activeConversationId = conversation.id
      }
      this.open()
      this.persist()
    },
    selectConversation(id) {
      if (!this.conversations.some((conversation) => conversation.id === id)) return
      this.activeConversationId = id
      this.open()
      this.persist()
    },
    deleteConversation(id) {
      const conversation = this.conversations.find((item) => item.id === id)
      if (!conversation) return

      const auth = useAuthStore()
      clearRemoteSession(conversation.sessionId, auth.token)
      this.conversations = this.conversations.filter((item) => item.id !== id)
      this.loadingConversationIds = this.loadingConversationIds.filter((item) => item !== id)
      if (this.activeConversationId === id) {
        this.activeConversationId = null
      }
      this.persist()
    },
    closeCurrent() {
      this.deleteConversation(this.activeConversationId)
      this.isOpen = false
      this.unread = 0
    },
    /** Ferme le chat et efface tout l’historique, notamment à la déconnexion. */
    end() {
      this.isOpen = false
      this.fullscreen = false
      this.reset()
    },
    reset() {
      const auth = useAuthStore()
      for (const conversation of this.conversations) {
        clearRemoteSession(conversation.sessionId, auth.token)
      }
      this.conversations = []
      this.activeConversationId = null
      this.loadingConversationIds = []
      this.unread = 0
      this.persist()
    },
    ask(text) {
      this.open()
      return this.send(text)
    },
    async send(text, { resend = false } = {}) {
      const content = text.trim()
      if (!content) return

      const conversation = this.ensureConversation()
      if (this.loadingConversationIds.includes(conversation.id)) return
      if (!resend) {
        const isFirstQuestion = !conversation.messages.some((message) => message.role === 'user')
        appendMessage(conversation, {
          id: newId(),
          role: 'user',
          content,
          time: Date.now(),
        })
        if (isFirstQuestion) conversation.title = titleFromMessages(conversation.messages)
      }
      conversation.updatedAt = Date.now()
      this.loadingConversationIds.push(conversation.id)
      this.persist()

      const auth = useAuthStore()
      try {
        const res = await api.sendMessage({
          message: content,
          sessionId: conversation.sessionId,
          token: auth.token,
        })
        if (!this.conversations.some((item) => item.id === conversation.id)) return
        appendMessage(conversation, {
          id: newId(),
          role: 'assistant',
          content: res.answer || 'Je n’ai pas de réponse à afficher pour cette question.',
          mode: res.mode,
          sources: res.sources,
          table: res.table,
          notes: res.notes,
          time: Date.now(),
        })
        conversation.updatedAt = Date.now()
        if (!this.isOpen) this.unread++
        if (res.action) await this.runAction(res.action, conversation)
      } catch (err) {
        if (err.status === 401) {
          auth.logout()
          return
        }
        if (!this.conversations.some((item) => item.id === conversation.id)) return
        appendMessage(conversation, {
          id: newId(),
          role: 'assistant',
          error: true,
          content: err.message || 'Une erreur est survenue.',
          retryText: content,
          time: Date.now(),
        })
        conversation.updatedAt = Date.now()
      } finally {
        this.loadingConversationIds = this.loadingConversationIds.filter(
          (id) => id !== conversation.id,
        )
        this.persist()
      }
    },
    /** Exécute l'action demandée par la réponse du chat (ouvrir / fermer un dashboard...). */
    async runAction(action, conversation) {
      const outcome = await useDashboardStore().apply(action)
      if (outcome === 'opened') {
        this.fullscreen = false // le chat en plein écran masquerait le dashboard qu'on vient d'ouvrir
      } else if (outcome === 'no_previous') {
        appendMessage(conversation, {
          id: newId(),
          role: 'assistant',
          content: 'There is no previous dashboard to go back to.',
          time: Date.now(),
        })
        conversation.updatedAt = Date.now()
      }
    },
    retry(messageId) {
      const conversation = this.activeConversation
      const index = conversation?.messages.findIndex((message) => message.id === messageId) ?? -1
      if (index === -1) return
      const { retryText } = conversation.messages[index]
      if (!retryText) return
      conversation.messages.splice(index, 1)
      return this.send(retryText, { resend: true })
    },
  },
})
