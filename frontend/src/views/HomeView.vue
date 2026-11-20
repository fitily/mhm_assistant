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
      <button class="btn" type="button" @click="chat.open()">iA'mbovo</button>
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
      <div class="grid">
        <button v-for="s in visibleShortcuts" :key="s.title" class="tile" type="button" @click="chat.ask(s.question)">
          <span class="tile-icon"><AppIcon :name="s.icon" :size="22" /></span>
          <strong>{{ s.title }}</strong>
          <span class="tile-text">{{ s.text }}</span>
          <span class="tile-q">« {{ s.question }} »</span>
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

.tile {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
  padding: 20px;
  text-align: left;
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  background: var(--surface);
  box-shadow: var(--shadow-sm);
  transition: border-color 0.15s, box-shadow 0.15s, transform 0.15s;
}
.tile:hover {
  border-color: var(--mhm-blue);
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
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
.tile strong {
  font-size: 1.02rem;
  color: var(--mhm-slate-dark);
}
.tile-text {
  color: var(--muted);
  font-size: 0.93rem;
}
.tile-q {
  margin-top: auto;
  font-size: 0.85rem;
  font-style: italic;
  color: var(--mhm-blue-dark);
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
}
</style>
