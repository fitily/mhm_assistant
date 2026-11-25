<script setup>
import { computed, ref } from 'vue'
import { isMockFeeds } from '@/services/api'
import { hostOf } from '@/utils/dates'
import FeedSection from './FeedSection.vue'
import FeedMeta from './FeedMeta.vue'

defineProps({ feed: { type: Object, required: true } })
defineEmits(['refresh'])

const source = ref('all')
const expanded = ref(false)
const FIRST_PAGE = 6 // 1 article à la une + 5 dans la liste

const visible = (items) => (expanded.value ? items : items.slice(0, FIRST_PAGE))
const hasMore = (items) => items.length > FIRST_PAGE
const moreLabel = computed(() => (expanded.value ? 'Voir moins' : 'Voir plus d’actualités'))
</script>

<template>
  <FeedSection
    id="news"
    v-model="source"
    title="Breaking News"
    subtitle="Dernières actualités de l’OMS et alertes d’urgence sanitaire en Afrique."
    :feed="feed"
    :demo="isMockFeeds"
    empty-text="Aucune actualité pour cette source pour le moment."
    @refresh="$emit('refresh')"
  >
    <template #skeleton>
      <div class="items layout" aria-hidden="true">
        <div class="sk lead-sk"></div>
        <div class="sk-list">
          <div v-for="n in 4" :key="n" class="sk row-sk"></div>
        </div>
      </div>
    </template>

    <template #default="{ items }">
      <div class="items layout">
        <article class="lead" :class="{ alert: items[0].tag === 'alerte' }">
          <FeedMeta :item="items[0]" />
          <h3>
            <a :href="items[0].url" target="_blank" rel="noopener noreferrer">
              {{ items[0].title }}<span class="sr-only"> (s’ouvre dans un nouvel onglet)</span>
            </a>
          </h3>
          <p v-if="items[0].summary" class="summary">{{ items[0].summary }}</p>
          <span class="host">
            {{ hostOf(items[0].url) }}
            <svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"><path fill="currentColor" d="M14 3h7v7h-2V6.41l-8.29 8.3-1.42-1.42L17.59 5H14V3ZM5 5h6v2H5v12h12v-6h2v8H3V5Z" /></svg>
          </span>
        </article>

        <ul v-if="items.length > 1" class="side">
          <li v-for="item in visible(items).slice(1)" :key="item.id" :class="{ alert: item.tag === 'alerte' }">
            <article>
              <FeedMeta :item="item" />
              <h3>
                <a :href="item.url" target="_blank" rel="noopener noreferrer">
                  {{ item.title }}<span class="sr-only"> (s’ouvre dans un nouvel onglet)</span>
                </a>
              </h3>
            </article>
          </li>
        </ul>
      </div>

      <button v-if="hasMore(items)" class="more btn btn-ghost" type="button" :aria-expanded="expanded" @click="expanded = !expanded">
        {{ moreLabel }}
      </button>
    </template>
  </FeedSection>
</template>

<style scoped>
.layout {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(0, 1fr);
  gap: 20px;
  align-items: stretch;
}
article {
  position: relative;
}
h3 {
  margin: 0;
  color: var(--mhm-slate-dark);
  line-height: 1.3;
}
a {
  color: inherit;
  text-decoration: none;
}
a:hover {
  text-decoration: underline;
  text-underline-offset: 3px;
}
/* Toute la carte est cliquable : le lien s'étend sur l'article. */
a::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
}
a:focus-visible {
  outline: none;
}
a:focus-visible::after {
  outline: 3px solid var(--mhm-blue);
  outline-offset: 2px;
}

.lead {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 24px;
  border: 1px solid var(--border);
  border-radius: 16px;
  background: var(--surface);
  box-shadow: var(--shadow-sm);
  transition: border-color 0.15s;
}
.lead:hover {
  border-color: var(--mhm-blue);
}
.lead.alert {
  border-left: 5px solid var(--danger);
}
.lead h3 {
  font-size: clamp(1.25rem, 2.4vw, 1.65rem);
}
.summary {
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin: 0;
  max-width: 62ch;
  color: var(--text);
}
.host {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--mhm-blue-dark);
  font-size: 0.85rem;
  font-weight: 600;
}

.side {
  margin: 0;
  padding: 0;
  list-style: none;
  border: 1px solid var(--border);
  border-radius: 16px;
  background: var(--surface);
  overflow: hidden;
}
.side li {
  padding: 14px 18px;
  border-top: 1px solid var(--border);
}
.side li:first-child {
  border-top: 0;
}
.side li.alert {
  border-left: 4px solid var(--danger);
  padding-left: 14px;
}
.side li:hover {
  background: var(--mhm-blue-50);
}
.side h3 {
  margin-top: 4px;
  font-size: 0.98rem;
  font-weight: 600;
}
.more {
  margin: 14px auto 0;
  display: flex;
}

.sk {
  border-radius: 16px;
  background: linear-gradient(90deg, #e6edf2 25%, #f1f5f8 50%, #e6edf2 75%);
  background-size: 200% 100%;
  animation: shimmer 1.4s ease-in-out infinite;
}
.lead-sk {
  height: 230px;
}
.sk-list {
  display: grid;
  gap: 10px;
}
.row-sk {
  height: 52px;
  border-radius: 10px;
}
@keyframes shimmer {
  to {
    background-position: -200% 0;
  }
}

@media (max-width: 860px) {
  .layout {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 520px) {
  .lead {
    padding: 18px;
  }
}
</style>
