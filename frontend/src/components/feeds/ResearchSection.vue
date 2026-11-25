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
const FIRST_PAGE = 8

const visible = (items) => (expanded.value ? items : items.slice(0, FIRST_PAGE))
const hasMore = (items) => items.length > FIRST_PAGE
const moreLabel = computed(() => (expanded.value ? 'Voir moins' : 'Voir plus de publications'))
</script>

<template>
  <FeedSection
    id="research"
    v-model="source"
    title="Scientific Research"
    subtitle="Dernières publications de The Lancet et du New England Journal of Medicine."
    :feed="feed"
    :demo="isMockFeeds"
    empty-text="Aucune publication pour cette revue pour le moment."
    @refresh="$emit('refresh')"
  >
    <template #skeleton>
      <ul class="items papers" aria-hidden="true">
        <li v-for="n in 4" :key="n" class="sk"></li>
      </ul>
    </template>

    <template #default="{ items }">
      <ul class="items papers">
        <li v-for="item in visible(items)" :key="item.id">
          <article>
            <FeedMeta :item="item" />
            <h3>
              <a :href="item.url" target="_blank" rel="noopener noreferrer">
                {{ item.title }}<span class="sr-only"> (s’ouvre dans un nouvel onglet)</span>
              </a>
            </h3>
            <p v-if="item.summary" class="summary">{{ item.summary }}</p>
            <span class="host">{{ hostOf(item.url) }}</span>
          </article>
        </li>
      </ul>

      <button v-if="hasMore(items)" class="more btn btn-ghost" type="button" :aria-expanded="expanded" @click="expanded = !expanded">
        {{ moreLabel }}
      </button>
    </template>
  </FeedSection>
</template>

<style scoped>
.papers {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.papers li {
  display: flex;
}
article {
  position: relative;
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 8px;
  padding: 18px 20px;
  border: 1px solid var(--border);
  border-radius: 14px;
  background: var(--surface);
  box-shadow: var(--shadow-sm);
  transition: border-color 0.15s;
}
article:hover {
  border-color: var(--mhm-blue);
}
h3 {
  margin: 0;
  color: var(--mhm-slate-dark);
  font-size: 1.04rem;
  line-height: 1.35;
}
a {
  color: inherit;
  text-decoration: none;
}
a:hover {
  text-decoration: underline;
  text-underline-offset: 3px;
}
a::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 14px;
}
a:focus-visible {
  outline: none;
}
a:focus-visible::after {
  outline: 3px solid var(--mhm-blue);
  outline-offset: 2px;
}
.summary {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin: 0;
  color: var(--muted);
  font-size: 0.92rem;
}
.host {
  margin-top: auto;
  color: var(--mhm-blue-dark);
  font-size: 0.82rem;
  font-weight: 600;
}
.more {
  margin: 14px auto 0;
  display: flex;
}

.sk {
  height: 132px;
  border-radius: 14px;
  background: linear-gradient(90deg, #e6edf2 25%, #f1f5f8 50%, #e6edf2 75%);
  background-size: 200% 100%;
  animation: shimmer 1.4s ease-in-out infinite;
}
@keyframes shimmer {
  to {
    background-position: -200% 0;
  }
}
@media (max-width: 760px) {
  .papers {
    grid-template-columns: 1fr;
  }
}
</style>
