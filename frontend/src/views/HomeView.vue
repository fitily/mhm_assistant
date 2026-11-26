<script setup>
// Accueil commun aux deux rôles : briefing médical pour le médecin, accès aux espaces et au chat.
import { computed, onMounted, ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useChatStore } from '@/stores/chat'
import AppShell from '@/components/layout/AppShell.vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import NewsCard from '@/components/news/NewsCard.vue'
import SkeletonBlock from '@/components/ui/SkeletonBlock.vue'
import { fetchNews } from '@/services/news'
import { timeAgo } from '@/utils/format'

const auth = useAuthStore()
const chat = useChatStore()
const medicalNews = ref([])
const sourceStatus = ref([])
const newsState = ref('idle') // idle | loading | error | ready
const newsUpdatedAt = ref(null)
let newsRequestId = 0

async function loadMedicalNews() {
  const requestId = ++newsRequestId
  newsState.value = 'loading'
  try {
    const result = await fetchNews({ token: auth.token })
    if (requestId !== newsRequestId) return
    medicalNews.value = result.items
    sourceStatus.value = result.sources
    newsUpdatedAt.value = result.updatedAt
    newsState.value = 'ready'
  } catch (error) {
    if (requestId !== newsRequestId) return
    if (error?.status === 401) auth.logout()
    newsState.value = 'error'
  }
}

// Espace propre à chaque rôle (le router vérifie aussi l'accès).
const WORKSPACES = [
  {
    title: 'Analytics',
    text: 'Explore MHM indicators through interactive dashboards.',
    to: { name: 'analytics' },
    icon: 'chart',
    roles: ['admin'],
  },
  {
    title: 'Medical news',
    text: 'Stay up to date with medical news, research and updates.',
    to: { name: 'news' },
    icon: 'news',
    roles: ['doctor'],
  },
]

const shortcuts = [
  {
    title: 'Want to know the data?',
    text: 'Get statistics about MHM in a simple question.',
    question: 'Give me the number of female patients at MHM.',
    roles: ['admin'],
    icon: 'chart',
  },
  {
    title: 'Want to search any documents?',
    text: 'Find any information about MHM in the documents and provide the corresponding sources',
    question: 'What are the symptoms of HIV?',
    roles: ['doctor'],
    icon: 'doc',
  },
  {
    title: "Want to discover iA'mbovo",
    text: "Know who iA'mbovo is.",
    question: 'Who are you?',
    roles: ['admin', 'doctor'],
    icon: 'help',
  },
  {
    title: "Want to use iA'mbovo?",
    text: 'Follow a short step-by-step guide: ask questions, check the sources and get the most out of the assistant.',
    question: 'How do I use you?',
    roles: ['admin', 'doctor'],
    icon: 'guidance',
  },
]

// Chaque profil ne voit que ce qui lui est utile (le backend vérifie aussi les droits).
const workspaces = computed(() => WORKSPACES.filter((w) => w.roles.includes(auth.role)))
const visibleShortcuts = computed(() => shortcuts.filter((s) => s.roles.includes(auth.role)))
const breakingNews = computed(() =>
  medicalNews.value.filter((item) => item.category === 'breaking' || item.category === 'update').slice(0, 4),
)
const researchNews = computed(() =>
  medicalNews.value.filter((item) => item.category === 'research').slice(0, 4),
)
const connectedSources = computed(() => sourceStatus.value.filter((source) => source.connected).length)
const updatedLabel = computed(() => (newsUpdatedAt.value ? `Updated ${timeAgo(newsUpdatedAt.value)}` : 'Not updated yet'))

onMounted(() => {
  if (auth.isDoctor) loadMedicalNews()
})
</script>

<template>
  <AppShell>
    <section class="welcome">
      <p class="role-chip" v-if="auth.roleLabel">{{ auth.roleLabel }}</p>
      <h1>Welcome {{ auth.displayName }} 👋</h1>
      <p>
        <template v-if="auth.isDoctor">
          Your clinical briefing brings together the latest health updates and research. Ask
          <strong>iA'mbovo</strong> a question any time.
        </template>
        <template v-else>
          Welcome to <strong>iA'mbovo</strong>. Click the blue bubble at the bottom right to chat with the
          assistant, or choose a question below.
        </template>
      </p>
      <button class="btn" type="button" @click="chat.openFullscreen()">iA'mbovo</button>
    </section>

    <section
      v-if="auth.isDoctor"
      class="clinical-briefing"
      aria-labelledby="briefing-title"
      :aria-busy="newsState === 'loading'"
    >
      <header class="briefing-head">
        <div>
          <p class="briefing-eyebrow">Clinical watch</p>
          <h2 id="briefing-title">Your medical briefing</h2>
          <p class="briefing-description">Trusted updates from WHO, The Lancet and NEJM.</p>
        </div>
        <div class="briefing-actions">
          <span v-if="newsState === 'ready'" class="updated">
            {{ connectedSources }} of {{ sourceStatus.length }} sources connected · {{ updatedLabel }}
          </span>
          <button class="btn btn-ghost" type="button" :disabled="newsState === 'loading'" @click="loadMedicalNews">
            <AppIcon name="refresh" :size="18" />Refresh
          </button>
        </div>
      </header>

      <ul v-if="newsState === 'ready'" class="source-status" aria-label="News source availability">
        <li v-for="source in sourceStatus" :key="source.key">
          <i class="source-dot" :class="{ online: source.connected }" aria-hidden="true" />
          {{ source.label }}
        </li>
      </ul>

      <div v-if="newsState === 'loading'" class="briefing-grid" aria-busy="true">
        <section v-for="section in 2" :key="section" class="feed-panel">
          <SkeletonBlock width="45%" height="22px" />
          <div v-for="card in 2" :key="card" class="feed-skeleton">
            <SkeletonBlock width="30%" height="16px" radius="999px" />
            <SkeletonBlock height="20px" />
            <SkeletonBlock width="75%" height="14px" />
          </div>
        </section>
      </div>

      <EmptyState
        v-else-if="newsState === 'error'"
        icon="alert"
        tone="danger"
        title="The medical briefing could not be loaded"
        text="The news sources are temporarily unavailable. Check your connection and try again."
      >
        <button class="btn" type="button" @click="loadMedicalNews">Try again</button>
      </EmptyState>

      <div v-else-if="newsState === 'ready'" class="briefing-grid">
        <section class="feed-panel" aria-labelledby="breaking-title">
          <header class="feed-panel-head">
            <span class="feed-heading-icon breaking-icon"><AppIcon name="alert" :size="20" /></span>
            <div>
              <h3 id="breaking-title">Breaking News</h3>
              <p>Latest health updates from WHO</p>
            </div>
            <RouterLink class="feed-link" :to="{ name: 'news' }">See all <AppIcon name="arrow" :size="16" /></RouterLink>
          </header>
          <div v-if="breakingNews.length" class="article-list">
            <NewsCard v-for="article in breakingNews" :key="article.id" :article="article" />
          </div>
          <p v-else class="feed-empty">No recent WHO updates are available.</p>
        </section>

        <section class="feed-panel" aria-labelledby="research-title">
          <header class="feed-panel-head">
            <span class="feed-heading-icon research-icon"><AppIcon name="flask" :size="20" /></span>
            <div>
              <h3 id="research-title">Scientific Research</h3>
              <p>Recent publications from leading journals</p>
            </div>
            <RouterLink class="feed-link" :to="{ name: 'news' }">See all <AppIcon name="arrow" :size="16" /></RouterLink>
          </header>
          <div v-if="researchNews.length" class="article-list">
            <NewsCard v-for="article in researchNews" :key="article.id" :article="article" />
          </div>
          <p v-else class="feed-empty">No recent research publications are available.</p>
        </section>
      </div>
    </section>

    <section v-if="workspaces.length" aria-labelledby="workspace-title">
      <h2 id="workspace-title" class="section-title">Your workspace</h2>
      <div class="grid one">
        <RouterLink v-for="w in workspaces" :key="w.title" :to="w.to" class="space">
          <span class="tile-icon"><AppIcon :name="w.icon" :size="24" /></span>
          <span class="space-text">
            <strong>{{ w.title }}</strong>
            <span>{{ w.text }}</span>
          </span>
          <AppIcon name="arrow" :size="20" />
        </RouterLink>
      </div>
    </section>

    <section aria-labelledby="shortcuts-title">
      <h2 id="shortcuts-title" class="section-title">Get started</h2>
      <div class="grid shortcuts">
        <button v-for="s in visibleShortcuts" :key="s.title" class="shortcut" type="button" @click="chat.ask(s.question)">
          <span class="shortcut-head">
            <span class="shortcut-icon"><AppIcon :name="s.icon" :size="22" /></span>
            <span class="shortcut-go" aria-hidden="true"><AppIcon name="arrow" :size="18" /></span>
          </span>
          <strong class="shortcut-title">{{ s.title }}</strong>
          <span class="shortcut-text">{{ s.text }}</span>
          <span class="shortcut-q">
            <AppIcon name="chat" :size="14" />
            <span>« {{ s.question }} »</span>
          </span>
        </button>
      </div>
    </section>
  </AppShell>
</template>

<style scoped>
.welcome {
  padding: 30px;
  border-radius: var(--radius-lg);
  color: #fff;
  background: linear-gradient(135deg, var(--mhm-blue), var(--mhm-slate));
}
.role-chip {
  display: inline-block;
  margin: 0 0 10px;
  padding: 3px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.2);
  font-size: 0.78rem;
  font-weight: 700;
}
.welcome h1 {
  margin: 0 0 8px;
  font-size: clamp(1.4rem, 3vw, 1.9rem);
}
.welcome p {
  max-width: 640px;
  margin: 0 0 18px;
  opacity: 0.95;
}
.welcome p.role-chip {
  margin: 0 0 10px;
  opacity: 1;
}
.welcome .btn {
  background: #fff;
  color: var(--mhm-slate);
}
.welcome .btn:hover:not(:disabled) {
  background: var(--mhm-blue-50);
}

.section-title {
  margin: 30px 0 14px;
  font-size: 1.12rem;
  color: var(--mhm-slate-dark);
}
.clinical-briefing {
  margin-top: 30px;
}
.briefing-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 16px;
  margin-bottom: 14px;
}
.briefing-eyebrow {
  margin: 0 0 4px;
  color: var(--mhm-blue);
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
.briefing-head h2 {
  margin: 0;
  color: var(--mhm-slate-dark);
  font-size: 1.35rem;
}
.briefing-description {
  margin: 4px 0 0;
  color: var(--muted);
}
.briefing-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}
.updated {
  color: var(--muted);
  font-size: 0.82rem;
}
.source-status {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
  margin: 0 0 14px;
  padding: 0;
  list-style: none;
  color: var(--muted);
  font-size: 0.82rem;
}
.source-status li {
  display: inline-flex;
  align-items: center;
  gap: 7px;
}
.source-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--warning);
}
.source-dot.online {
  background: var(--success);
}
.briefing-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  align-items: start;
  gap: 16px;
}
.feed-panel {
  min-width: 0;
  padding: 18px;
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  background: var(--surface-2);
}
.feed-panel-head {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 46px;
  margin-bottom: 14px;
}
.feed-heading-icon {
  flex: none;
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  border-radius: 12px;
}
.breaking-icon {
  color: var(--danger);
  background: var(--danger-bg);
}
.research-icon {
  color: var(--mhm-blue-dark);
  background: var(--mhm-blue-50);
}
.feed-panel-head h3 {
  margin: 0;
  color: var(--mhm-slate-dark);
  font-size: 1rem;
}
.feed-panel-head p {
  margin: 2px 0 0;
  color: var(--muted);
  font-size: 0.8rem;
}
.feed-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-left: auto;
  color: var(--mhm-blue-dark);
  font-size: 0.82rem;
  font-weight: 600;
  text-decoration: none;
  white-space: nowrap;
}
.feed-link:hover {
  text-decoration: underline;
}
.article-list {
  display: grid;
  gap: 10px;
}
.feed-empty {
  margin: 0;
  padding: 20px 12px;
  border-radius: 12px;
  background: var(--surface);
  color: var(--muted);
  text-align: center;
}
.feed-skeleton {
  display: grid;
  gap: 12px;
  padding: 16px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--surface);
}
.grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}
.grid.one {
  grid-template-columns: minmax(0, 1fr);
}

.space {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  background: var(--surface);
  box-shadow: var(--shadow-sm);
  color: var(--mhm-blue);
  text-decoration: none;
  transition: border-color 0.15s, box-shadow 0.15s, transform 0.15s;
}
.space:hover {
  border-color: var(--mhm-blue);
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}
.space-text {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  color: var(--muted);
}
.space-text strong {
  font-size: 1.05rem;
  color: var(--mhm-slate-dark);
}

.tile-icon {
  flex: none;
  width: 44px;
  height: 44px;
  display: grid;
  place-items: center;
  border-radius: 12px;
  background: var(--mhm-blue-50);
  color: var(--mhm-blue);
}

/* ---- « Get started » : cartes de questions rapides ---- */
/* flex + centrage : 2 cartes restent centrées (pas de vide à droite), 3 cartes se partagent la ligne */
.grid.shortcuts {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 18px;
}
.shortcut {
  /* couleur d'accent propre à chaque carte (décorative) */
  --accent: var(--mhm-blue);
  --accent-bg: var(--mhm-blue-50);
  position: relative;
  display: flex;
  flex: 1 1 280px;
  max-width: 440px;
  flex-direction: column;
  align-items: stretch;
  gap: 10px;
  min-height: 210px;
  padding: 22px;
  overflow: hidden;
  text-align: left;
  cursor: pointer;
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  background:
    radial-gradient(120% 90% at 100% 0%, var(--accent-bg) 0%, transparent 55%),
    var(--surface);
  box-shadow: var(--shadow-sm);
  transition: border-color 0.2s, box-shadow 0.2s, transform 0.2s;
}
/* accents : uniquement les couleurs de la charte MHM (bleu, ardoise, bleu foncé) */
.shortcut:nth-child(3n + 2) {
  --accent: var(--mhm-slate);
  --accent-bg: #e7eef3;
}
.shortcut:nth-child(3n + 3) {
  --accent: var(--mhm-blue-dark);
  --accent-bg: var(--mhm-blue-100);
}
/* filet d'accent en bas, qui se déploie au survol */
.shortcut::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 3px;
  background: var(--accent);
  transform: scaleX(0);
  transform-origin: left;
  transition: transform 0.3s ease;
}
.shortcut:hover,
.shortcut:focus-visible {
  border-color: var(--accent);
  box-shadow: var(--shadow-md);
  transform: translateY(-3px);
}
.shortcut:hover::after,
.shortcut:focus-visible::after {
  transform: scaleX(1);
}
.shortcut:focus-visible {
  outline: 3px solid var(--mhm-blue-100);
  outline-offset: 2px;
}
.shortcut:active {
  transform: translateY(-1px) scale(0.99);
}

.shortcut-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.shortcut-icon {
  width: 46px;
  height: 46px;
  display: grid;
  place-items: center;
  border-radius: 14px;
  color: #fff;
  background: linear-gradient(135deg, var(--accent), color-mix(in srgb, var(--accent) 70%, #000));
  box-shadow: 0 6px 14px color-mix(in srgb, var(--accent) 35%, transparent);
  transition: transform 0.25s;
}
.shortcut:hover .shortcut-icon {
  transform: rotate(-6deg) scale(1.06);
}
.shortcut-go {
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  color: var(--accent);
  background: var(--accent-bg);
  opacity: 0.7;
  transition: transform 0.25s, opacity 0.25s, background 0.25s, color 0.25s;
}
.shortcut:hover .shortcut-go,
.shortcut:focus-visible .shortcut-go {
  opacity: 1;
  color: #fff;
  background: var(--accent);
  transform: translateX(3px);
}

.shortcut-title {
  margin-top: 6px;
  font-size: 1.08rem;
  line-height: 1.3;
  color: var(--mhm-slate-dark);
}
.shortcut-text {
  color: var(--muted);
  font-size: 0.92rem;
  line-height: 1.5;
}
/* la question qui sera envoyée, présentée comme une bulle de chat */
.shortcut-q {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-top: auto;
  padding: 10px 12px;
  border-radius: 12px 12px 12px 4px;
  background: var(--surface-2);
  border: 1px dashed var(--border);
  font-size: 0.84rem;
  font-style: italic;
  line-height: 1.4;
  color: var(--mhm-slate-dark);
  transition: background 0.2s, border-color 0.2s;
}
.shortcut-q svg {
  flex: none;
  margin-top: 2px;
  color: var(--accent);
}
.shortcut:hover .shortcut-q {
  background: #fff;
  border-color: var(--accent);
  border-style: solid;
}

@media (max-width: 900px) {
  .grid {
    grid-template-columns: minmax(0, 1fr);
  }
  .briefing-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
@media (max-width: 520px) {
  .welcome {
    padding: 22px 18px;
  }
  .grid.shortcuts {
    gap: 12px;
  }
  .shortcut {
    flex-basis: 100%; /* mobile : 1 colonne, cartes plus compactes */
    max-width: none;
    min-height: 0;
    padding: 18px;
  }
  .briefing-head {
    align-items: flex-start;
    flex-direction: column;
  }
  .briefing-actions {
    width: 100%;
    justify-content: space-between;
  }
  .feed-panel {
    padding: 14px;
  }
  .feed-panel-head {
    flex-wrap: wrap;
  }
}
@media (prefers-reduced-motion: reduce) {
  .shortcut,
  .shortcut::after,
  .shortcut-icon,
  .shortcut-go {
    transition: none;
  }
  .shortcut:hover,
  .shortcut:focus-visible,
  .shortcut:hover .shortcut-icon,
  .shortcut:hover .shortcut-go {
    transform: none;
  }
}
</style>
