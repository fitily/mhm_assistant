<script setup>
import { computed } from 'vue'
import { timeAgo } from '@/utils/dates'

const props = defineProps({
  id: { type: String, required: true },
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
  feed: { type: Object, required: true },
  modelValue: { type: String, default: 'all' }, // source sélectionnée (« all » = toutes)
  demo: { type: Boolean, default: false },
  emptyText: { type: String, default: 'Aucun article pour le moment.' },
})
defineEmits(['update:modelValue', 'refresh'])

const loading = computed(() => props.feed.status === 'loading')
const busy = computed(() => loading.value || props.feed.refreshing)

const filters = computed(() => [
  { id: 'all', name: 'Toutes', count: props.feed.items.length },
  ...props.feed.sources.map((s) => ({ id: s.id, name: s.name, count: s.count, status: s.status })),
])
const items = computed(() =>
  props.modelValue === 'all'
    ? props.feed.items
    : props.feed.items.filter((i) => i.sourceId === props.modelValue),
)

const problems = computed(() => props.feed.sources.filter((s) => s.status !== 'ok'))
const allDown = computed(
  () => props.feed.sources.length > 0 && props.feed.sources.every((s) => s.status === 'error'),
)
const showFilters = computed(() => props.feed.sources.length > 1 && props.feed.items.length > 0)

const updated = computed(() => {
  const times = props.feed.sources.map((s) => s.fetchedAt).filter(Boolean).map((t) => Date.parse(t))
  const latest = times.length ? Math.max(...times) : Date.parse(props.feed.generatedAt)
  return Number.isNaN(latest) ? '' : timeAgo(latest)
})
</script>

<template>
  <section class="feed" :aria-labelledby="`${id}-title`" :aria-busy="loading">
    <header class="head">
      <div>
        <h2 :id="`${id}-title`">
          {{ title }}
          <span v-if="demo" class="demo">Données de démonstration</span>
        </h2>
        <p v-if="subtitle" class="sub">{{ subtitle }}</p>
      </div>
      <div class="actions">
        <span v-if="updated && feed.status === 'ready'" class="updated" role="status">
          Actualisé {{ updated }}
        </span>
        <button class="refresh" type="button" :disabled="busy" @click="$emit('refresh')">
          <svg :class="{ spinning: busy }" viewBox="0 0 24 24" width="16" height="16" aria-hidden="true">
            <path fill="currentColor" d="M12 4a8 8 0 0 1 7.5 5.2l1.9-.7A10 10 0 0 0 2 12h2a8 8 0 0 1 8-8Zm0 16a8 8 0 0 1-7.5-5.2l-1.9.7A10 10 0 0 0 22 12h-2a8 8 0 0 1-8 8ZM20 3v6h-6l6-6ZM4 21v-6h6l-6 6Z" />
          </svg>
          <span>{{ busy ? 'Actualisation…' : 'Actualiser' }}</span>
        </button>
      </div>
    </header>

    <div v-if="showFilters" class="chips" role="group" :aria-label="`Filtrer par source : ${title}`">
      <button
        v-for="f in filters"
        :key="f.id"
        type="button"
        class="chip"
        :aria-pressed="modelValue === f.id"
        @click="$emit('update:modelValue', f.id)"
      >
        <span v-if="f.status && f.status !== 'ok'" class="state" :class="f.status" aria-hidden="true"></span>
        {{ f.name }}
        <span class="count">{{ f.count }}</span>
      </button>
    </div>

    <p v-for="s in problems" v-show="!allDown" :key="s.id" class="notice" :class="s.status" role="status">
      <strong>{{ s.name }}</strong> ne répond pas pour le moment.
      {{ s.status === 'stale' ? 'Les derniers articles connus restent affichés.' : 'Les autres sources restent à jour.' }}
    </p>

    <slot v-if="loading" name="skeleton" />

    <div v-else-if="feed.status === 'error' || (feed.status === 'ready' && allDown && !items.length)" class="state-box" role="alert">
      <p>
        {{ feed.error || 'Les sources de veille ne répondent pas. Réessayez dans quelques minutes.' }}
      </p>
      <button class="btn btn-ghost" type="button" @click="$emit('refresh')">Réessayer</button>
    </div>

    <slot v-else-if="items.length" :items="items" />

    <p v-else class="state-box empty">{{ emptyText }}</p>

    <p v-if="feed.error && feed.status === 'ready'" class="notice error" role="alert">
      Actualisation impossible : {{ feed.error }}
    </p>
  </section>
</template>

<style scoped>
.feed + .feed {
  margin-top: 44px;
}
.head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px 20px;
  flex-wrap: wrap;
}
h2 {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px 12px;
  margin: 0;
  font-size: 1.3rem;
  color: var(--mhm-slate-dark);
}
.demo {
  padding: 2px 10px;
  border-radius: 999px;
  background: var(--mhm-blue-50);
  color: var(--mhm-blue-dark);
  font-size: 0.75rem;
  font-weight: 600;
}
.sub {
  margin: 4px 0 0;
  max-width: 60ch;
  color: var(--muted);
  font-size: 0.93rem;
}
.actions {
  display: flex;
  align-items: center;
  gap: 12px;
}
.updated {
  color: var(--muted);
  font-size: 0.82rem;
}
.refresh {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border: 1px solid var(--border);
  border-radius: 999px;
  background: var(--surface);
  color: var(--mhm-slate);
  font-size: 0.85rem;
  font-weight: 600;
}
.refresh:hover:not(:disabled) {
  background: var(--mhm-blue-50);
}
.refresh:disabled {
  cursor: progress;
  opacity: 0.75;
}
.spinning {
  animation: spin 0.9s linear infinite;
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 16px 0 4px;
}
.chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  border: 1px solid var(--border);
  border-radius: 999px;
  background: var(--surface);
  color: var(--mhm-slate);
  font-size: 0.88rem;
  font-weight: 600;
}
.chip:hover {
  border-color: var(--mhm-blue);
}
.chip[aria-pressed='true'] {
  border-color: var(--mhm-slate);
  background: var(--mhm-slate);
  color: #fff;
}
.count {
  font-weight: 500;
  opacity: 0.75;
}
.state {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.state.stale {
  background: #c98a00;
}
.state.error {
  background: var(--danger);
}

.notice {
  margin: 12px 0 0;
  padding: 10px 14px;
  border-radius: 10px;
  border: 1px solid #f0dca6;
  background: #fff8e3;
  color: #5c4500;
  font-size: 0.9rem;
}
.notice.error {
  border-color: #f3c3bd;
  background: var(--danger-bg);
  color: #7a1f16;
}
.feed :deep(.items) {
  margin-top: 16px;
}
.state-box {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 16px;
  padding: 18px 20px;
  border: 1px dashed var(--border);
  border-radius: var(--radius);
  background: var(--surface);
  color: var(--muted);
}
.state-box p {
  margin: 0;
}
.empty {
  justify-content: flex-start;
}
@media (max-width: 520px) {
  .updated {
    display: none;
  }
}
</style>
