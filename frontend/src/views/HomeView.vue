<script setup>
// Accueil commun aux deux rôles : bienvenue, accès à l'espace du rôle, questions rapides pour le chat.
import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useChatStore } from '@/stores/chat'
import AppShell from '@/components/layout/AppShell.vue'
import AppIcon from '@/components/ui/AppIcon.vue'

const auth = useAuthStore()
const chat = useChatStore()

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
]

// Chaque profil ne voit que ce qui lui est utile (le backend vérifie aussi les droits).
const workspaces = computed(() => WORKSPACES.filter((w) => w.roles.includes(auth.role)))
const visibleShortcuts = computed(() => shortcuts.filter((s) => s.roles.includes(auth.role)))
</script>

<template>
  <AppShell>
    <section class="welcome">
      <p class="role-chip" v-if="auth.roleLabel">{{ auth.roleLabel }}</p>
      <h1>Welcome {{ auth.displayName }} 👋</h1>
      <p>
        Welcome to <strong>iA'mbovo</strong>. Click the blue bubble at the bottom right to chat with the
        assistant, or choose a question below.
      </p>
      <button class="btn" type="button" @click="chat.openFullscreen()">iA'mbovo</button>
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
