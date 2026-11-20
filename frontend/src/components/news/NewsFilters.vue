<script setup>
// Filtres du fil : catégories (puces) + recherche texte. v-model:category et v-model:query.
import AppIcon from '@/components/ui/AppIcon.vue'

defineProps({
  categories: { type: Array, required: true }, // [{ key, label }]
  category: { type: String, default: 'all' },
  query: { type: String, default: '' },
})
const emit = defineEmits(['update:category', 'update:query'])
</script>

<template>
  <div class="filters">
    <div class="chips" role="tablist" aria-label="Categories">
      <button
        v-for="c in categories"
        :key="c.key"
        class="chip"
        :class="{ active: c.key === category }"
        role="tab"
        type="button"
        :aria-selected="c.key === category"
        @click="emit('update:category', c.key)"
      >
        {{ c.label }}
      </button>
    </div>
    <label class="search">
      <AppIcon name="search" :size="18" />
      <span class="sr-only">Search news</span>
      <input
        type="search"
        placeholder="Search news…"
        :value="query"
        @input="emit('update:query', $event.target.value)"
      />
    </label>
  </div>
</template>

<style scoped>
.filters {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}
.chips {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  max-width: 100%;
}
.chip {
  flex: none;
  padding: 7px 14px;
  border: 1px solid var(--border);
  border-radius: 999px;
  background: var(--surface);
  color: var(--muted);
  font-weight: 600;
  font-size: 0.88rem;
  transition: all 0.15s;
}
.chip:hover {
  border-color: var(--mhm-blue);
  color: var(--mhm-blue-dark);
}
.chip.active {
  background: var(--mhm-blue);
  border-color: var(--mhm-blue);
  color: #fff;
}
.search {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 12px;
  min-width: 240px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  color: var(--muted);
}
.search:focus-within {
  border-color: var(--mhm-blue);
  box-shadow: 0 0 0 3px var(--mhm-blue-100);
}
.search input {
  flex: 1;
  min-width: 0;
  padding: 9px 0;
  border: 0;
  outline: 0;
  background: transparent;
}
@media (max-width: 640px) {
  .search {
    width: 100%;
  }
}
</style>
