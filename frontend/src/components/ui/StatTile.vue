<script setup>
// Tuile d'indicateur. `placeholder` = emplacement réservé (valeur grisée) en attendant les vraies données.
defineProps({
  label: { type: String, required: true },
  value: { type: [String, Number], default: '—' },
  hint: { type: String, default: '' },
  placeholder: { type: Boolean, default: false },
  trend: { type: String, default: '' }, // « +8,3 % » : évolution face à la période précédente
  trendDirection: { type: String, default: 'flat' }, // up | down | flat
  error: { type: Boolean, default: false }, // indicateur indisponible
})
</script>

<template>
  <div class="tile" :class="{ placeholder, error }">
    <span class="label">{{ label }}</span>
    <strong class="value">
      {{ value }}
      <span v-if="trend" class="trend" :class="trendDirection" :aria-label="`Change versus previous period: ${trend}`">
        <span aria-hidden="true">{{ trendDirection === 'up' ? '▲' : trendDirection === 'down' ? '▼' : '■' }}</span>
        {{ trend }}
      </span>
    </strong>
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
.trend {
  margin-left: 8px;
  font-size: 0.8rem;
  font-weight: 600;
  white-space: nowrap;
}
.trend.up {
  color: var(--success);
}
.trend.down {
  color: var(--danger, #b42318);
}
.trend.flat {
  color: var(--muted);
}
.error .value {
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
