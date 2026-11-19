<script setup>
import { ref } from 'vue'
import { useChatStore } from '@/stores/chat'
import ChatHeader from './ChatHeader.vue'
import ChatHistorySidebar from './ChatHistorySidebar.vue'
import ChatConversation from './ChatConversation.vue'

const chat = useChatStore()
const isFullscreen = ref(false)

function handleEscape() {
  if (isFullscreen.value) {
    isFullscreen.value = false
    return
  }
  chat.minimize()
}
</script>

<template>
  <div class="chat-root">
    <Transition name="pop">
      <section
        v-if="chat.isOpen"
        class="panel"
        :class="{ fullscreen: isFullscreen }"
        role="dialog"
        aria-label="iA'mbovo"
        @keydown.esc="handleEscape"
      >
        <ChatHeader
          :fullscreen="isFullscreen"
          @minimize="chat.minimize()"
          @toggle-fullscreen="isFullscreen = !isFullscreen"
          @close="chat.closeCurrent()"
        />
        <div class="layout" :class="{ fullscreen: isFullscreen }">
          <ChatHistorySidebar
            v-if="isFullscreen"
            :conversations="chat.conversationHistory"
            :active-id="chat.activeConversationId"
            @new="chat.startConversation()"
            @select="chat.selectConversation($event)"
          />
          <ChatConversation :fullscreen="isFullscreen" />
        </div>
      </section>
    </Transition>

    <button
      class="launcher"
      :class="{ hidden: chat.isOpen }"
      type="button"
      :aria-expanded="chat.isOpen"
      aria-label="Ouvrir iA'mbovo"
      @click="chat.toggle()"
    >
      <svg viewBox="0 0 24 24" width="28" height="28" aria-hidden="true"><path fill="currentColor" d="M4 2h16a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H8l-5 4V4a2 2 0 0 1 1-2Zm3 6v2h10V8H7Zm0 4v2h7v-2H7Z"/></svg>
      <span v-if="chat.unread" class="badge" aria-label="Nouveau message">{{ chat.unread }}</span>
    </button>
  </div>
</template>

<style scoped src="./ChatWidget.css"></style>
