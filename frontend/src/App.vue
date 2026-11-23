<script setup>
import { watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useChatStore } from '@/stores/chat'
import { useDashboardStore } from '@/stores/dashboards'
import ChatWidget from '@/components/chat/ChatWidget.vue'

const auth = useAuthStore()
const chat = useChatStore()
const dashboards = useDashboardStore()
const router = useRouter()

// À la déconnexion (volontaire ou session expirée) : on efface le chat et on revient au login
watch(
  () => auth.isAuthenticated,
  (loggedIn) => {
    if (!loggedIn) {
      chat.end()
      dashboards.reset()
      router.push({ name: 'login' })
    }
  },
)
</script>

<template>
  <RouterView />
  <!-- Le widget vit dans App.vue : il reste accessible pendant toute la navigation -->
  <ChatWidget v-if="auth.isAuthenticated" />
</template>
