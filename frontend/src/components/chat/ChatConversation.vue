<script setup>
import { ref, watch, nextTick } from 'vue'
import { useChatStore } from '@/stores/chat'
import ChatMessage from './ChatMessage.vue'
import ChatInput from './ChatInput.vue'

const props = defineProps({
  fullscreen: { type: Boolean, default: false },
})

const chat = useChatStore()
const scroller = ref(null)
const input = ref(null)

function scrollToBottom() {
  nextTick(() => {
    const element = scroller.value
    if (element) element.scrollTo({ top: element.scrollHeight, behavior: 'smooth' })
  })
}

watch(() => [chat.activeConversationId, chat.messages.length, chat.loading, props.fullscreen], scrollToBottom)
watch(
  () => chat.isOpen,
  (open) => {
    if (open) {
      scrollToBottom()
      nextTick(() => input.value?.focus())
    }
  },
)
</script>

<template>
  <main class="conversation" :class="{ fullscreen }">
    <div ref="scroller" class="messages" aria-live="polite">
      <div v-if="!chat.messages.length" class="empty">
        <div class="empty-icon" aria-hidden="true">
          <img src="/images/iambovo-icon.jpeg" alt="" />
        </div>
        <h3>Hello, how can I help you today.</h3>
        <p>You can ask question related to data and documents of MHM.</p>
        <div class="suggestions">
          <button
            v-for="suggestion in chat.suggestions"
            :key="suggestion"
            type="button"
            @click="chat.send(suggestion)"
          >
            {{ suggestion }}
          </button>
        </div>
      </div>

      <ChatMessage
        v-for="message in chat.messages"
        :key="message.id"
        :message="message"
        @retry="chat.retry"
      />

      <div v-if="chat.loading" class="typing-row" role="status" aria-label="iA'mbovo rédige une réponse">
        <span class="avatar" aria-hidden="true">
          <img src="/images/iambovo-icon.jpeg" alt="" />
        </span>
        <div class="typing"><span></span><span></span><span></span></div>
      </div>
    </div>

    <ChatInput ref="input" :disabled="chat.loading" @send="chat.send($event)" />
  </main>
</template>

<style scoped>
.conversation {
  min-width: 0;
  min-height: 0;
  display: flex;
  flex: 1;
  flex-direction: column;
}
.messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px 14px 6px;
  overscroll-behavior: contain;
}
.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 18px 8px 10px;
  text-align: center;
}
.empty-icon {
  width: 56px;
  height: 56px;
  display: grid;
  place-items: center;
  overflow: hidden;
  margin-bottom: 10px;
  border-radius: 50%;
  background: var(--mhm-blue-50);
}
.empty-icon img {
  width: 100%;
  height: 100%;
  display: block;
  border-radius: inherit;
  object-fit: cover;
}
.empty h3 {
  margin: 0 0 4px;
  color: var(--mhm-slate);
}
.empty p {
  margin: 0 0 14px;
  color: var(--muted);
  font-size: 0.92rem;
}
.suggestions {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.suggestions button {
  padding: 10px 14px;
  border: 1px solid var(--mhm-blue-100);
  border-radius: 12px;
  background: #fff;
  color: var(--mhm-slate);
  font-size: 0.9rem;
  text-align: left;
  transition: background 0.15s, border-color 0.15s;
}
.suggestions button:hover {
  border-color: var(--mhm-blue);
  background: var(--mhm-blue-50);
}
.typing-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
}
.avatar {
  flex: none;
  width: 28px;
  height: 28px;
  overflow: hidden;
  border-radius: 50%;
}
.avatar img {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: cover;
}
.typing {
  display: flex;
  gap: 5px;
  padding: 12px 14px;
  border: 1px solid var(--border);
  border-radius: 16px 16px 16px 4px;
  background: var(--surface);
}
.typing span {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--mhm-blue);
  animation: bounce 1.2s infinite ease-in-out;
}
.typing span:nth-child(2) { animation-delay: 0.15s; }
.typing span:nth-child(3) { animation-delay: 0.3s; }
@keyframes bounce {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.45; }
  30% { transform: translateY(-5px); opacity: 1; }
}

.fullscreen .messages {
  width: min(100%, 980px);
  align-self: center;
  padding: 28px 24px 8px;
}
.fullscreen :deep(.input) {
  width: min(100%, 980px);
  align-self: center;
  border-top: 0;
  background: transparent;
  padding: 12px 24px calc(18px + env(safe-area-inset-bottom));
}
</style>
