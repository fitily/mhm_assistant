<script setup>
// Espace « Medical news » du médecin. Prêt à recevoir un flux réel :
//  - les données viennent de services/news.js (à brancher sur /v1/news)
//  - états gérés : chargement, erreur, flux non connecté, aucun résultat, liste
//  - filtres (catégorie + recherche) déjà reliés ; la recherche est « débouncée »
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import AppShell from '@/components/layout/AppShell.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import SectionCard from '@/components/ui/SectionCard.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import SkeletonBlock from '@/components/ui/SkeletonBlock.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import NewsCard from '@/components/news/NewsCard.vue'
import NewsFilters from '@/components/news/NewsFilters.vue'
import BreakingBanner from '@/components/news/BreakingBanner.vue'
import { fetchNews, NEWS_CATEGORIES } from '@/services/news'
import { timeAgo } from '@/utils/format'

const category = ref('all')
const query = ref('')
const items = ref([])
const connected = ref(false)
const updatedAt = ref(null)
const state = ref('loading') // loading | error | ready

let timer = null
let requestId = 0 // ignore les réponses obsolètes si l'utilisateur change vite de filtre

async function load() {
  const id = ++requestId
  state.value = 'loading'
  try {
    const res = await fetchNews({ category: category.value, query: query.value })
    if (id !== requestId) return
    items.value = res.items
    connected.value = res.connected
    updatedAt.value = res.updatedAt
    state.value = 'ready'
  } catch {
    if (id === requestId) state.value = 'error'
  }
}

const breaking = computed(() => items.value.find((a) => a.category === 'breaking') || null)
const hasFilters = computed(() => category.value !== 'all' || query.value.trim() !== '')
const lastUpdate = computed(() => (updatedAt.value ? `Updated ${timeAgo(updatedAt.value)}` : 'Not updated yet'))

watch(category, load)
watch(query, () => {
  clearTimeout(timer)
  timer = setTimeout(load, 300)
})
function resetFilters() {
  category.value = 'all'
  query.value = ''
}

onMounted(load)
onBeforeUnmount(() => clearTimeout(timer))
</script>

<template>
  <AppShell>
    <PageHeader
      eyebrow="Clinical watch"
      title="Medical news"
      subtitle="Latest medical news, research publications and updates for healthcare professionals."
    >
      <template #actions>
        <span class="updated">{{ lastUpdate }}</span>
        <button class="btn btn-ghost" type="button" :disabled="state === 'loading'" @click="load">
          <AppIcon name="refresh" :size="18" />Refresh
        </button>
      </template>
    </PageHeader>

    <BreakingBanner v-if="state === 'ready' && breaking" :article="breaking" />

    <div class="layout">
      <div class="feed">
        <NewsFilters v-model:category="category" v-model:query="query" :categories="NEWS_CATEGORIES" />

        <div v-if="state === 'loading'" class="grid" aria-busy="true">
          <div v-for="n in 4" :key="n" class="ghost">
            <SkeletonBlock width="30%" height="18px" radius="999px" />
            <SkeletonBlock height="20px" />
            <SkeletonBlock width="80%" height="20px" />
            <SkeletonBlock height="14px" />
            <SkeletonBlock width="60%" height="14px" />
          </div>
        </div>

        <SectionCard v-else-if="state === 'error'">
          <EmptyState icon="alert" tone="danger" title="The news could not be loaded" text="Check your connection and try again.">
            <button class="btn" type="button" @click="load">Try again</button>
          </EmptyState>
        </SectionCard>

        <SectionCard v-else-if="!items.length">
          <EmptyState
            v-if="hasFilters"
            icon="search"
            title="No article matches your search"
            text="Try another keyword or choose a different category."
          >
            <button class="btn btn-ghost" type="button" @click="resetFilters">Clear filters</button>
          </EmptyState>
          <EmptyState
            v-else
            icon="news"
            title="Live medical news is coming soon"
            text="Breaking news, recent research and important medical updates will appear here as soon as the news feed is connected."
          />
        </SectionCard>

        <div v-else class="grid">
          <NewsCard v-for="a in items" :key="a.id" :article="a" />
        </div>
      </div>

      <aside class="side">
        <SectionCard title="Feed status">
          <p class="status" :class="{ on: connected }">
            <i aria-hidden="true" />{{ connected ? 'Live feed connected' : 'Live feed not connected yet' }}
          </p>
          <p class="note">Planned content</p>
          <ul class="planned">
            <li><AppIcon name="alert" :size="16" />Breaking medical news</li>
            <li><AppIcon name="flask" :size="16" />Recent research findings</li>
            <li><AppIcon name="info" :size="16" />Important medical updates</li>
          </ul>
        </SectionCard>
      </aside>
    </div>
  </AppShell>
</template>

<style scoped>
.updated {
  font-size: 0.85rem;
  color: var(--muted);
}
.layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  gap: 22px;
  align-items: start;
}
.feed {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}
.grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}
.ghost {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 18px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
}
.side {
  position: sticky;
  top: 24px;
}
.status {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 14px;
  font-weight: 600;
  color: var(--warning);
}
.status i {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
}
.status.on {
  color: var(--success);
}
.note {
  margin: 0 0 8px;
  font-size: 0.78rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--muted);
}
.planned {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 10px;
}
.planned li {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--mhm-slate);
}
.planned :deep(svg) {
  color: var(--mhm-blue);
}
@media (max-width: 1050px) {
  .layout {
    grid-template-columns: minmax(0, 1fr);
  }
  .side {
    position: static;
  }
}
@media (max-width: 640px) {
  .grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
