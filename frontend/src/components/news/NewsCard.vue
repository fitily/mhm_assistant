<script setup>
// Ligne d'actualité, sobre : catégorie · source, titre (lien), résumé limité à 2 lignes.
// La date est affichée par le groupe de jours de la page (NewsView) ; ici `published_at` sert d'attribut <time>.
// Sans `url`, le titre n'est pas cliquable. Format attendu : voir le contrat dans services/news.js.
import { computed } from 'vue'
import AppIcon from '@/components/ui/AppIcon.vue'

const props = defineProps({ article: { type: Object, required: true } })

const META = {
  breaking: { label: 'Breaking' },
  research: { label: 'Research' },
  update: { label: 'Update' },
}
const meta = computed(() => META[props.article.category] || META.update)
</script>

<template>
  <article class="news" :class="article.category">
    <p class="meta">
      <span class="cat">{{ meta.label }}</span>
      <template v-if="article.source">
        <span aria-hidden="true">·</span>
        <span>{{ article.source }}</span>
      </template>
      <time v-if="article.published_at" class="sr-only" :datetime="article.published_at">{{ article.published_at }}</time>
    </p>
    <h3>
      <a v-if="article.url" :href="article.url" target="_blank" rel="noopener noreferrer">
        <span>{{ article.title }}</span>
        <AppIcon name="external" :size="14" />
      </a>
      <template v-else>{{ article.title }}</template>
    </h3>
    <p v-if="article.summary" class="summary">{{ article.summary }}</p>
  </article>
</template>

<style scoped>
.news {
  --accent: var(--mhm-slate);
  position: relative;
  padding: 16px 18px 16px 20px;
  border-radius: 12px;
  transition: background 0.15s;
}
.news.breaking {
  --accent: var(--danger);
}
.news.research {
  --accent: var(--mhm-blue);
}
/* filet d'accent à gauche, discret au repos, plein au survol */
.news::before {
  content: '';
  position: absolute;
  left: 0;
  top: 16px;
  bottom: 16px;
  width: 3px;
  border-radius: 3px;
  background: var(--accent);
  opacity: 0.35;
  transition: opacity 0.15s;
}
.news:hover,
.news:focus-within {
  background: var(--surface-2);
}
.news:hover::before,
.news:focus-within::before {
  opacity: 1;
}
.meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin: 0 0 4px;
  font-size: 0.78rem;
  color: var(--muted);
}
.cat {
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--accent);
}
h3 {
  margin: 0;
  font-size: 1.02rem;
  line-height: 1.4;
  font-weight: 650;
  color: var(--mhm-slate-dark);
}
h3 a {
  color: inherit;
  text-decoration: none;
}
h3 a svg {
  display: inline-block;
  margin-left: 4px;
  vertical-align: -1px;
  opacity: 0;
  transition: opacity 0.15s;
}
h3 a:hover,
h3 a:focus-visible {
  color: var(--mhm-blue-dark);
}
h3 a:hover svg,
h3 a:focus-visible svg {
  opacity: 0.8;
}
h3 a:focus-visible {
  outline: 3px solid var(--mhm-blue-100);
  outline-offset: 2px;
  border-radius: 4px;
}
.summary {
  display: -webkit-box;
  margin: 6px 0 0;
  overflow: hidden;
  font-size: 0.9rem;
  line-height: 1.5;
  color: var(--muted);
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}
</style>
