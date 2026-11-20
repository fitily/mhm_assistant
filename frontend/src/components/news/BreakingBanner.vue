<script setup>
// Bandeau d'alerte « dernière minute » : affiche le dernier article de catégorie breaking, s'il existe.
import AppIcon from '@/components/ui/AppIcon.vue'
import { timeAgo } from '@/utils/format'

defineProps({ article: { type: Object, required: true } })
</script>

<template>
  <aside class="banner" role="alert">
    <span class="badge"><AppIcon name="alert" :size="16" />Breaking</span>
    <component
      :is="article.url ? 'a' : 'span'"
      class="headline"
      v-bind="article.url ? { href: article.url, target: '_blank', rel: 'noopener noreferrer' } : {}"
    >
      {{ article.title }}
    </component>
    <time class="when">{{ timeAgo(article.published_at) }}</time>
  </aside>
</template>

<style scoped>
.banner {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  margin-bottom: 18px;
  border: 1px solid #f3c6c0;
  border-radius: var(--radius);
  background: var(--danger-bg);
}
.badge {
  flex: none;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px;
  border-radius: 999px;
  background: var(--danger);
  color: #fff;
  font-size: 0.74rem;
  font-weight: 700;
  text-transform: uppercase;
}
.headline {
  flex: 1;
  min-width: 0;
  font-weight: 600;
  color: var(--text);
  text-decoration: none;
}
a.headline:hover {
  text-decoration: underline;
}
.when {
  flex: none;
  font-size: 0.8rem;
  color: var(--muted);
}
@media (max-width: 640px) {
  .banner {
    flex-wrap: wrap;
  }
  .headline {
    flex: 1 0 100%;
    order: 3;
  }
}
</style>
