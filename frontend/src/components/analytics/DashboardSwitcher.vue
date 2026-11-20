<script setup>
// Onglets de sélection du tableau de bord. Reçoit la liste (catalogue) et émet la clé choisie.
defineProps({
  dashboards: { type: Array, required: true }, // [{ key, title, available }]
  modelValue: { type: String, default: null },
})
const emit = defineEmits(['update:modelValue'])
</script>

<template>
  <div class="switcher" role="tablist" aria-label="Dashboards">
    <button
      v-for="d in dashboards"
      :key="d.key"
      class="tab"
      :class="{ active: d.key === modelValue }"
      role="tab"
      type="button"
      :aria-selected="d.key === modelValue"
      @click="emit('update:modelValue', d.key)"
    >
      {{ d.title }}
      <span v-if="!d.available" class="soon">Soon</span>
    </button>
  </div>
</template>

<style scoped>
.switcher {
  display: flex;
  gap: 6px;
  overflow-x: auto;
  padding: 4px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 12px;
  width: fit-content;
  max-width: 100%;
}
.tab {
  flex: none;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  border: 0;
  border-radius: 9px;
  background: transparent;
  color: var(--muted);
  font-weight: 600;
  transition: background 0.15s, color 0.15s;
}
.tab:hover {
  color: var(--mhm-slate-dark);
}
.tab.active {
  background: var(--surface);
  color: var(--mhm-blue-dark);
  box-shadow: var(--shadow-sm);
}
.soon {
  padding: 1px 7px;
  border-radius: 999px;
  background: var(--warning-bg);
  color: var(--warning);
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
}
</style>
