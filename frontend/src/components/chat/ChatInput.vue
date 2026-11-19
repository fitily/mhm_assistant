<script setup>
import { ref, nextTick, onMounted } from 'vue'

const props = defineProps({
  disabled: { type: Boolean, default: false },
})
const emit = defineEmits(['send'])

const text = ref('')
const area = ref(null)
const MAX_HEIGHT = 120

function autosize() {
  const el = area.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, MAX_HEIGHT) + 'px'
}

function submit() {
  const value = text.value.trim()
  if (!value || props.disabled) return
  emit('send', value)
  text.value = ''
  nextTick(autosize)
}

function onKeydown(e) {
  // Entrée envoie, Maj+Entrée insère un retour à la ligne
  if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
    e.preventDefault()
    submit()
  }
}

function focus() {
  area.value?.focus()
}

onMounted(focus)
defineExpose({ focus })
</script>

<template>
  <form class="input" @submit.prevent="submit">
    <label for="chat-input" class="sr-only">Votre message</label>
    <textarea
      id="chat-input"
      ref="area"
      v-model="text"
      rows="1"
      placeholder="Posez votre question…"
      maxlength="2000"
      @input="autosize"
      @keydown="onKeydown"
    ></textarea>
    <button
      class="send"
      type="submit"
      :disabled="disabled || !text.trim()"
      aria-label="Envoyer le message"
    >
      <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path fill="currentColor" d="M3.4 20.4 21 12 3.4 3.600 3.400 10l12 2-12 2 0 6.400Z"/></svg>
    </button>
  </form>
</template>

<style scoped>
.input {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding: 10px 12px calc(10px + env(safe-area-inset-bottom));
  border-top: 1px solid var(--border);
  background: var(--surface);
}
textarea {
  flex: 1;
  min-height: 42px;
  max-height: 120px;
  padding: 10px 14px;
  resize: none;
  border: 1px solid var(--border);
  border-radius: 21px;
  background: #f7f9fb;
  font-size: 16px; /* évite le zoom automatique sur iOS */
  line-height: 1.35;
}
textarea:focus {
  outline: none;
  border-color: var(--mhm-blue);
  background: #fff;
  box-shadow: 0 0 0 3px var(--mhm-blue-100);
}
.send {
  flex: none;
  width: 42px;
  height: 42px;
  display: grid;
  place-items: center;
  border: 0;
  border-radius: 50%;
  background: var(--mhm-blue);
  color: #fff;
  transition: background 0.15s;
}
.send:hover:not(:disabled) {
  background: var(--mhm-blue-dark);
}
.send:disabled {
  background: #b9c8d2;
  cursor: not-allowed;
}
</style>
