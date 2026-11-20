<script setup>
// Carte d'un article. Format attendu : voir le contrat dans services/news.js.
// Sans `url`, le titre n'est pas cliquable (aperçu / article sans lien).
import { computed } from 'vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import { timeAgo } from '@/utils/format'

const props = defineProps({ article: { type: Object, required: true } })

const META = {
  breaking: { label: 'Breaking', icon: 'alert' },
  research: { label: 'Research', icon: 'flask' },
  update: { label: 'Medical update', icon: 'info' },
}
const meta = computed(() => META[props.article.category] || META.update)
const when = computed(() => timeAgo(props.article.published_at))
</script>

<template>
  <article class="news" :class="article.category">
    <div class="top">
      <span class="pill"><AppIcon :name="meta.icon" :size="14" />{{ meta.label }}</span>
      <time v-if="when" :datetime="article.published_at">{{ when }}</time>
    </div>
    <h3>
      <a v-if="article.url" :href="article.url" target="_blank" rel="noopener noreferrer">
        {{ article.title }} <AppIcon name="external" :size="14" />
      </a>
      <template v-else>{{ article.title }}</template>
    </h3>
    <p v-if="article.summary" class="summary">{{ article.summary }}</p>
    <footer v-if="article.source" class="source">{{ article.source }}</footer>
  </article>
</template>

<style scoped>
.news {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 18px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  transition: box-shadow 0.15s, transform 0.15s;
}
.news:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-1px);
}
.top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px;
  border-radius: 999px;
  background: var(--mhm-blue-50);
  color: var(--mhm-blue-dark);
  font-size: 0.74rem;
  font-weight: 700;
}
.breaking .pill {
  background: var(--danger-bg);
  color: var(--danger);
}
.update .pill {
  background: var(--success-bg);
  color: var(--success);
}
time {
  font-size: 0.78rem;
  color: var(--muted);
}
h3 {
  margin: 0;
  font-size: 1.02rem;
  line-height: 1.35;
  color: var(--mhm-slate-dark);
}
h3 a {
  color: inherit;
  text-decoration: none;
}
h3 a:hover {
  color: var(--mhm-blue-dark);
  text-decoration: underline;
}
.summary {
  margin: 0;
  color: var(--muted);
  font-size: 0.92rem;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.source {
  margin-top: auto;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--mhm-slate);
}
</style>
