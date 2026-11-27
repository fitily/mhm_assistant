<script setup>
// Espace « Medical news » du médecin : les actualités PUBLIÉES pendant les 7 derniers jours (période dynamique).
//  - les données viennent de services/news.js via /v1/news ; le backend filtre d'après la date de publication
//  - affichage sobre, comme la page « News » de l'OMS : image à gauche, texte à droite, 8 articles à la fois (« Show more »)
//  - états gérés : chargement, erreur, disponibilité partielle, aucun résultat, liste
//  - filtres (catégorie + recherche) ; la recherche est « débouncée »
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
import AppShell from '@/components/layout/AppShell.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import SectionCard from '@/components/ui/SectionCard.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import SkeletonBlock from '@/components/ui/SkeletonBlock.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import NewsCard from '@/components/news/NewsCard.vue'
import NewsFilters from '@/components/news/NewsFilters.vue'
import { fetchNews, NEWS_CATEGORIES } from '@/services/news'
import { shortDate, timeAgo } from '@/utils/format'

const PAGE_SIZE = 8

const category = ref('all')
const query = ref('')
const auth = useAuthStore()
const items = ref([])
const sources = ref([])
const updatedAt = ref(null)
const windowDays = ref(7)
const since = ref(null)
const outsideWindow = ref(0) // articles correspondant aux filtres mais hors période (non affichés)
const shown = ref(PAGE_SIZE)
const state = ref('loading') // loading | error | ready

let timer = null
let requestId = 0 // ignore les réponses obsolètes si l'utilisateur change vite de filtre

async function load() {
  const id = ++requestId
  state.value = 'loading'
  shown.value = PAGE_SIZE
  try {
    const res = await fetchNews({ category: category.value, query: query.value, token: auth.token })
    if (id !== requestId) return
    items.value = res.items
    sources.value = res.sources
    updatedAt.value = res.updatedAt
    windowDays.value = res.windowDays
    since.value = res.since
    outsideWindow.value = res.outsideWindow
    state.value = 'ready'
  } catch (error) {
    if (id === requestId) {
      if (error?.status === 401) auth.logout()
      state.value = 'error'
    }
  }
}

const hasFilters = computed(() => category.value !== 'all' || query.value.trim() !== '')
const lastUpdate = computed(() => (updatedAt.value ? `Updated ${timeAgo(updatedAt.value)}` : ''))
const period = computed(() =>
  since.value
    ? `Published in the last ${windowDays.value} days · ${shortDate(since.value)} – today`
    : `Published in the last ${windowDays.value} days`,
)
const online = computed(() => sources.value.filter((source) => source.connected).length)

const visible = computed(() => items.value.slice(0, shown.value))
const remaining = computed(() => Math.max(0, items.value.length - shown.value))
// Explique une liste vide : rien n'a été publié pendant la période, mais des articles plus anciens existent.
const olderNote = computed(() =>
  outsideWindow.value
    ? `${outsideWindow.value} older ${outsideWindow.value > 1 ? 'articles are' : 'article is'} not shown because ${outsideWindow.value > 1 ? 'they were' : 'it was'} not published in this period.`
    : '',
)

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
    <div class="page">
      <PageHeader eyebrow="Clinical watch" title="Medical news" :subtitle="period">
        <template #actions>
          <span v-if="lastUpdate" class="updated">{{ lastUpdate }}</span>
          <button class="btn btn-ghost" type="button" :disabled="state === 'loading'" @click="load">
            <AppIcon name="refresh" :size="18" />Refresh
          </button>
        </template>
      </PageHeader>

      <NewsFilters v-model:category="category" v-model:query="query" :categories="NEWS_CATEGORIES" />

      <div v-if="state === 'loading'" class="skeletons" aria-busy="true">
        <div v-for="n in 4" :key="n" class="ghost">
          <SkeletonBlock width="25%" height="12px" radius="999px" />
          <SkeletonBlock height="18px" />
          <SkeletonBlock width="70%" height="14px" />
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
          :text="`Nothing published in the last ${windowDays} days matches. Try another keyword or category. ${olderNote}`"
        >
          <button class="btn btn-ghost" type="button" @click="resetFilters">Clear filters</button>
        </EmptyState>
        <EmptyState
          v-else
          icon="news"
          :title="`No medical news in the last ${windowDays} days`"
          :text="olderNote || 'New articles from WHO, the Ministry of Public Health and leading journals will appear here as soon as they are published.'"
        />
      </SectionCard>

      <div v-else class="feed">
        <NewsCard v-for="article in visible" :key="article.id" :article="article" />
        <button v-if="remaining" class="btn btn-ghost more" type="button" @click="shown += PAGE_SIZE">
          Show more ({{ remaining }})
        </button>
      </div>

      <footer v-if="state === 'ready' && sources.length" class="sources" aria-label="News sources">
        <span class="sources-title">Sources</span>
        <ul>
          <li v-for="source in sources" :key="source.key" :class="{ off: !source.connected }">
            <i class="dot" :class="{ online: source.connected }" aria-hidden="true" />
            <a :href="source.url" target="_blank" rel="noopener noreferrer">{{ source.label }}</a>
            <span v-if="!source.connected" class="off-label">unavailable</span>
          </li>
        </ul>
        <span v-if="online < sources.length" class="sources-note">{{ online }} of {{ sources.length }} connected</span>
      </footer>
    </div>
  </AppShell>
</template>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: 18px;
}
.updated {
  font-size: 0.85rem;
  color: var(--muted);
}
.feed {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 520px), 1fr));
  column-gap: 36px;
  border-top: 1px solid var(--border);
}
.more {
  grid-column: 1 / -1;
  justify-self: center;
  margin-top: 18px;
}
.skeletons {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.ghost {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 16px 20px;
  border-radius: 12px;
  background: var(--surface);
  border: 1px solid var(--border);
}
.sources {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px 16px;
  padding-top: 14px;
  border-top: 1px solid var(--border);
  font-size: 0.8rem;
  color: var(--muted);
}
.sources-title {
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}
.sources ul {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 16px;
  margin: 0;
  padding: 0;
  list-style: none;
}
.sources li {
  display: flex;
  align-items: center;
  gap: 6px;
}
.sources a {
  color: var(--mhm-slate);
  text-decoration: none;
}
.sources a:hover {
  color: var(--mhm-blue-dark);
  text-decoration: underline;
}
.sources .off a {
  color: var(--muted);
}
.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--warning);
}
.dot.online {
  background: var(--success);
}
.sources-note {
  margin-left: auto;
}
@media (max-width: 640px) {
  .sources-note {
    margin-left: 0;
  }
}
</style>
