<script setup>
import { computed } from 'vue'
import { formatDate, timeAgo } from '@/utils/dates'

const props = defineProps({
  item: { type: Object, required: true },
})

// Couleur d'identification de la source : elle accompagne toujours le nom écrit.
const COLORS = { who: '#0079b3', afro: '#a85a00', lancet: '#8f2d56', nejm: '#2f6f4e' }
const TAGS = { alerte: 'Alerte sanitaire' }

const dot = computed(() => COLORS[props.item.sourceId] || 'var(--mhm-slate)')
const tag = computed(() => TAGS[props.item.tag] || '')
const ago = computed(() => timeAgo(props.item.publishedAt))
</script>

<template>
  <p class="meta">
    <span class="source"><span class="dot" :style="{ background: dot }" aria-hidden="true"></span>{{ item.sourceName }}</span>
    <span v-if="tag" class="tag">{{ tag }}</span>
    <time v-if="ago" :datetime="item.publishedAt" :title="formatDate(item.publishedAt)">{{ ago }}</time>
  </p>
</template>

<style scoped>
.meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 10px;
  margin: 0;
  font-size: 0.82rem;
  color: var(--muted);
}
.source {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  color: var(--mhm-slate);
}
.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.tag {
  padding: 1px 8px;
  border-radius: 999px;
  background: var(--danger-bg);
  color: var(--danger);
  font-weight: 600;
}
</style>
