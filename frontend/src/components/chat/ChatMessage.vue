<script setup>
import { computed } from 'vue'
import { renderMarkdown } from '@/utils/markdown'

const props = defineProps({
  message: { type: Object, required: true },
})
defineEmits(['retry'])

const isUser = computed(() => props.message.role === 'user')
const html = computed(() => (isUser.value ? '' : renderMarkdown(props.message.content)))
const time = computed(() =>
  new Date(props.message.time).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }),
)
const sources = computed(() =>
  (props.message.sources || []).map((source) =>
    typeof source === 'string'
      ? { label: source }
      : {
          label: source.label || source.title || source.document || source.name || 'Document',
          page: source.page,
          url: source.url,
        },
  ),
)
const stats = computed(() => props.message.stats || [])
const table = computed(() => (props.message.table?.columns?.length ? props.message.table : null))
const notes = computed(() => props.message.notes || [])
</script>

<template>
  <div class="row" :class="{ user: isUser }">
    <span v-if="!isUser" class="avatar" aria-hidden="true">
      <img src="/images/iambovo-icon.jpeg" alt="" />
    </span>
    <div class="col">
      <div class="bubble" :class="{ user: isUser, error: message.error }">
        <p v-if="isUser" class="plain">{{ message.content }}</p>
        <template v-else>
          <div v-if="message.error" class="err-title">
            <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path fill="currentColor" d="M12 2 1 21h22L12 2Zm1 14h-2v-2h2v2Zm0-4h-2V8h2v4Z"/></svg>
            Une erreur est survenue
          </div>
          <div class="md" v-html="html"></div>
          <div v-if="table" class="data-table">
            <table>
              <thead>
                <tr><th v-for="(column, index) in table.columns" :key="index">{{ column }}</th></tr>
              </thead>
              <tbody>
                <tr v-for="(row, rowIndex) in table.rows" :key="rowIndex">
                  <td v-for="(cell, columnIndex) in row" :key="columnIndex">{{ cell }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <ul v-if="notes.length" class="notes">
            <li v-for="(note, index) in notes" :key="index">{{ note }}</li>
          </ul>
          <div v-if="stats.length" class="stats">
            <div v-for="(stat, index) in stats" :key="index" class="stat">
              <span class="stat-value">{{ stat.value }}</span>
              <span class="stat-label">{{ stat.label }}</span>
            </div>
          </div>
          <div v-if="sources.length" class="sources">
            <span class="sources-title">Sources</span>
            <ul>
              <li v-for="(source, index) in sources" :key="index">
                <component
                  :is="source.url ? 'a' : 'span'"
                  class="chip"
                  :href="source.url || undefined"
                  :target="source.url ? '_blank' : undefined"
                  rel="noopener noreferrer"
                >
                  <svg viewBox="0 0 24 24" width="13" height="13" aria-hidden="true"><path fill="currentColor" d="M6 2h9l5 5v15H6V2Zm8 1.500V8h4.500L14 3.500Z"/></svg>
                  {{ source.label }}<template v-if="source.page"> · p. {{ source.page }}</template>
                </component>
              </li>
            </ul>
          </div>
          <button
            v-if="message.error && message.retryText"
            class="retry"
            type="button"
            @click="$emit('retry', message.id)"
          >
            Réessayer
          </button>
        </template>
      </div>
      <span class="time">{{ isUser ? 'Vous' : 'Assistant' }} · {{ time }}</span>
    </div>
  </div>
</template>

<style scoped src="./ChatMessage.css"></style>
