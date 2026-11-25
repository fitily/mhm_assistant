<script setup>
import { onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useChatStore } from '@/stores/chat'
import { useFeedsStore } from '@/stores/feeds'
import { formatLongDate } from '@/utils/dates'
import AppTopbar from '@/components/layout/AppTopbar.vue'
import BreakingNewsSection from '@/components/feeds/BreakingNewsSection.vue'
import ResearchSection from '@/components/feeds/ResearchSection.vue'

const auth = useAuthStore()
const chat = useChatStore()
const feeds = useFeedsStore()

const today = formatLongDate()

onMounted(() => feeds.loadAll())
</script>

<template>
  <div class="shell">
    <AppTopbar />

    <main class="content">
      <header class="intro">
        <div>
          <h1>Bonjour {{ auth.displayName }}</h1>
          <p class="date">{{ today }}</p>
        </div>
        <button class="btn" type="button" @click="chat.open()">Ouvrir l’assistant</button>
      </header>

      <BreakingNewsSection
        :feed="feeds['breaking-news']"
        @refresh="feeds.load('breaking-news', { force: true })"
      />
      <ResearchSection
        :feed="feeds.research"
        @refresh="feeds.load('research', { force: true })"
      />

      <p class="foot">
        Titres et extraits fournis par l’OMS, The Lancet et le NEJM : chaque lien ouvre l’article sur
        le site de la source, dont l’accès complet peut être réservé aux abonnés. Ces informations ne
        remplacent pas les protocoles nationaux ni les consignes de votre établissement.
      </p>
    </main>
  </div>
</template>

<style scoped>
.content {
  max-width: 1100px;
  margin: 0 auto;
  padding: 28px 20px 120px;
}
.intro {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 14px;
  margin-bottom: 32px;
}
h1 {
  margin: 0;
  font-size: clamp(1.5rem, 3vw, 2rem);
  color: var(--mhm-slate-dark);
}
.date {
  margin: 4px 0 0;
  color: var(--muted);
}
.date::first-letter {
  text-transform: uppercase;
}
.foot {
  max-width: 70ch;
  margin: 44px 0 0;
  color: var(--muted);
  font-size: 0.85rem;
}
</style>
