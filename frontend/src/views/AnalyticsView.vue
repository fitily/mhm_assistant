<script setup>
// Espace « Analytics » de l'administrateur : tableaux de bord Superset intégrés.
//  - le catalogue vient du backend (/v1/superset/dashboards)
//  - le dashboard affiché est dans le store (stores/dashboards.js) : le chat peut l'ouvrir, le changer
//    ou le fermer ; l'URL (?d=clé) le reflète (lien partageable, retour arrière)
//  - composables/useSupersetEmbed monte le dashboard dans <DashboardViewport>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useDashboardStore } from '@/stores/dashboards'
import AppShell from '@/components/layout/AppShell.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import StatTile from '@/components/ui/StatTile.vue'
import DashboardSwitcher from '@/components/analytics/DashboardSwitcher.vue'
import DashboardViewport from '@/components/analytics/DashboardViewport.vue'
import { useSupersetEmbed } from '@/composables/useSupersetEmbed'
import { listDashboards, SUPERSET_LIVE } from '@/services/analytics'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const dash = useDashboardStore()

const dashboards = ref([])
const listState = ref('loading') // loading | ready | error
const listError = ref('')
const viewport = ref(null)

const embed = useSupersetEmbed({ getToken: () => auth.token, onUnauthorized: () => auth.logout() })

const urlKey = computed(() => (typeof route.query.d === 'string' ? route.query.d : null))
const selectedKey = computed(() => dash.current)
const selected = computed(() => dashboards.value.find((d) => d.key === dash.current) || null)

const viewportState = computed(() => {
  if (listState.value !== 'ready') return listState.value
  if (dash.closed && !dash.current) return 'closed'
  if (!selected.value) return 'empty'
  if (!selected.value.available) return 'coming-soon'
  return embed.state.value === 'idle' ? 'loading' : embed.state.value
})
const viewportMessage = computed(() => (listState.value === 'error' ? listError.value : embed.error.value))

// Pastille d'état de la liaison avec Superset
const connection = computed(() => {
  if (!SUPERSET_LIVE) return { on: false, text: 'Demo mode: Superset not connected' }
  if (viewportState.value === 'ready') return { on: true, text: 'Connected to Superset' }
  if (viewportState.value === 'error') return { on: false, text: 'Superset unavailable' }
  return { on: false, text: 'Connecting to Superset…' }
})

async function load() {
  listState.value = 'loading'
  listError.value = ''
  try {
    dashboards.value = await listDashboards({ token: auth.token })
    listState.value = 'ready'
  } catch (err) {
    if (err?.status === 401) auth.logout()
    listError.value = err?.message || ''
    listState.value = 'error'
  }
}

async function showSelected() {
  await nextTick()
  const el = viewport.value?.mountEl
  const d = selected.value
  if (d?.available && el) embed.mount(d, el)
  else embed.reset()
}

function retry() {
  if (listState.value === 'error') load()
  else showSelected()
}

function select(key) {
  dash.open(key)
}

// Au chargement du catalogue : lien direct (?d=) > dernier dashboard ouvert > le premier.
function initSelection() {
  if (dash.closed) return
  const wanted = urlKey.value ?? dash.current ?? dashboards.value[0]?.key
  if (wanted && wanted !== dash.current) dash.open(wanted, { remember: false })
}

// Le store pilote l'affichage ; l'URL suit.
watch([() => dash.current, listState], () => {
  if (listState.value !== 'ready') return
  showSelected()
})
watch(
  () => dash.current,
  (key) => {
    if (key === urlKey.value || (!key && urlKey.value === null)) return
    const { d: _ignored, ...rest } = route.query
    router.replace({ query: key ? { ...rest, d: key } : rest })
  },
)
// Retour arrière / lien modifié à la main
watch(urlKey, (key) => {
  if (key && key !== dash.current && listState.value === 'ready') dash.open(key)
})
watch(listState, (state) => {
  if (state === 'ready') initSelection()
})

onMounted(() => {
  dash.closed = false // une nouvelle visite de la page ne reste pas « fermée »
  load()
})
</script>

<template>
  <AppShell>
    <PageHeader
      eyebrow="Administration"
      title="Analytics"
      subtitle="Explore MHM indicators through interactive dashboards."
    >
      <template #actions>
        <span class="status" :class="{ on: connection.on }"><i aria-hidden="true" />{{ connection.text }}</span>
      </template>
    </PageHeader>

    <!-- Zone réservée aux indicateurs clés (à alimenter plus tard) -->
    <section class="kpis" aria-label="Key indicators">
      <StatTile v-for="n in 4" :key="n" label="Key indicator" hint="Available soon" placeholder />
    </section>

    <section class="board" aria-label="Dashboards">
      <DashboardSwitcher
        v-if="dashboards.length"
        :dashboards="dashboards"
        :model-value="selectedKey"
        @update:model-value="select"
      />
      <DashboardViewport
        ref="viewport"
        :state="viewportState"
        :title="selected?.title"
        :message="viewportMessage"
        @retry="retry"
      />
    </section>
  </AppShell>
</template>

<style scoped>
.status {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  border-radius: 999px;
  background: var(--warning-bg);
  color: var(--warning);
  font-size: 0.82rem;
  font-weight: 600;
}
.status i {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
}
.status.on {
  background: var(--success-bg);
  color: var(--success);
}
.kpis {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 22px;
}
.board {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
@media (max-width: 900px) {
  .kpis {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 480px) {
  .kpis {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
