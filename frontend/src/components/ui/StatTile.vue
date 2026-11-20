<script setup>
// Tuile d'indicateur. `placeholder` = emplacement réservé (valeur grisée) en attendant les vraies données.
defineProps({
  label: { type: String, required: true },
  value: { type: [String, Number], default: '—' },
  hint: { type: String, default: '' },
  placeholder: { type: Boolean, default: false },
})
</script>

<template>
  <div class="tile" :class="{ placeholder }">
    <span class="label">{{ label }}</span>
    <strong class="value">{{ value }}</strong>
    <span v-if="hint" class="hint">{{ hint }}</span>
  </div>
</template>

<style scoped>
.tile {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 16px 18px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow-sm);
}
.label {
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--muted);
}
.value {
  font-size: 1.7rem;
  line-height: 1.2;
  color: var(--mhm-slate-dark);
}
.hint {
  font-size: 0.78rem;
  color: var(--muted);
}
.placeholder {
  border-style: dashed;
  background: var(--surface-2);
  box-shadow: none;
}
.placeholder .value {
  color: var(--border);
}
</style>
