<script setup>
import { useAuthStore } from '@/stores/auth'
import { useChatStore } from '@/stores/chat'
import BrandLogo from '@/components/BrandLogo.vue'

const auth = useAuthStore()
const chat = useChatStore()

const shortcuts = [
  {
    title: 'Interroger les données',
    text: 'Obtenez des statistiques, des tableaux et des indicateurs en posant une simple question.',
    question: 'Donne-moi un tableau de répartition par région',
    icon: 'M3 3h2v18H3V3Zm4 10h3v8H7v-8Zm5-6h3v14h-3V7Zm5 3h3v11h-3V10Z',
  },
  {
    title: 'Chercher dans les documents',
    text: 'Retrouvez une information dans les rapports de référence, avec la source et la page.',
    question: 'Que disent les documents sur la prévention ?',
    icon: 'M6 2h9l5 5v15H6V2Zm8 1.5V8h4.5L14 3.5ZM8 12h8v1.5H8V12Zm0 3.5h8V17H8v-1.5Z',
  },
  {
    title: 'Découvrir l’assistant',
    text: 'Voyez ce que l’assistant sait faire et comment formuler vos questions.',
    question: 'Que peux-tu faire pour moi ?',
    icon: 'M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20Zm1 15h-2v-2h2v2Zm1.1-5.2-.9.9c-.5.5-.7.9-.7 1.800h-1.500v-.4c0-.8.3-1.500.9-2.100l1.200-1.200a1.500 1.500 0 1 0-2.600-1H8.500a3.500 3.500 0 1 1 5.600 2Z',
  },
]
</script>

<template>
  <div class="shell">
    <header class="topbar">
      <div class="topbar-inner">
        <BrandLogo :size="36" />
        <div class="user">
          <span class="avatar" aria-hidden="true">{{ auth.displayName.charAt(0).toUpperCase() }}</span>
          <span class="name">{{ auth.displayName }}</span>
          <button class="btn btn-ghost logout" type="button" @click="auth.logout()">
            Se déconnecter
          </button>
        </div>
      </div>
    </header>

    <main class="content">
      <section class="welcome">
        <h1>Bonjour {{ auth.displayName }} 👋</h1>
        <p>
          Bienvenue sur <strong>MHM Assistant</strong>. Cliquez sur la bulle bleue en bas à droite
          pour discuter avec l’assistant, ou choisissez une question ci-dessous.
        </p>
        <button class="btn" type="button" @click="chat.open()">Ouvrir l’assistant</button>
      </section>

      <section aria-labelledby="shortcuts-title">
        <h2 id="shortcuts-title" class="section-title">Pour commencer</h2>
        <div class="grid">
          <button
            v-for="s in shortcuts"
            :key="s.title"
            class="tile"
            type="button"
            @click="chat.ask(s.question)"
          >
            <span class="tile-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" width="22" height="22"><path fill="currentColor" :d="s.icon" /></svg>
            </span>
            <strong>{{ s.title }}</strong>
            <span class="tile-text">{{ s.text }}</span>
            <span class="tile-q">« {{ s.question }} »</span>
          </button>
        </div>
      </section>
    </main>
  </div>
</template>

<style scoped>
.topbar {
  position: sticky;
  top: 0;
  z-index: 10;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
}
.topbar-inner {
  max-width: 1100px;
  margin: 0 auto;
  padding: 10px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.user {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.avatar {
  flex: none;
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: var(--mhm-slate);
  color: #fff;
  font-weight: 700;
}
.name {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 600;
  color: var(--mhm-slate);
}
.logout {
  padding: 8px 14px;
}

.content {
  max-width: 1100px;
  margin: 0 auto;
  padding: 28px 20px 120px;
}
.welcome {
  padding: 28px;
  border-radius: 16px;
  color: #fff;
  background: linear-gradient(135deg, var(--mhm-blue), var(--mhm-slate));
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
.welcome .btn {
  background: #fff;
  color: var(--mhm-slate);
}
.welcome .btn:hover:not(:disabled) {
  background: var(--mhm-blue-50);
}

.section-title {
  margin: 32px 0 14px;
  font-size: 1.15rem;
  color: var(--mhm-slate);
}
.grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}
.tile {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
  padding: 20px;
  text-align: left;
  border: 1px solid var(--border);
  border-radius: 14px;
  background: var(--surface);
  box-shadow: var(--shadow-sm);
  transition: border-color 0.15s, box-shadow 0.15s, transform 0.15s;
}
.tile:hover {
  border-color: var(--mhm-blue);
  box-shadow: 0 8px 22px rgba(0, 147, 215, 0.15);
  transform: translateY(-2px);
}
.tile-icon {
  width: 42px;
  height: 42px;
  display: grid;
  place-items: center;
  border-radius: 12px;
  background: var(--mhm-blue-50);
  color: var(--mhm-blue);
}
.tile strong {
  font-size: 1.02rem;
  color: var(--mhm-slate);
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
    grid-template-columns: 1fr;
  }
}
@media (max-width: 520px) {
  .name {
    display: none;
  }
  .content {
    padding-top: 18px;
  }
  .welcome {
    padding: 22px 18px;
  }
}
</style>
