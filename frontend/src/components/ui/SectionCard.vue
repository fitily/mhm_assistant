<script setup>
// Carte blanche standard pour regrouper un bloc de contenu. Slots : défaut, « actions » (en-tête).
defineProps({
  title: { type: String, default: '' },
  subtitle: { type: String, default: '' },
  flush: { type: Boolean, default: false }, // pas de marge interne (ex. contenu pleine largeur)
})
</script>

<template>
  <section class="card">
    <header v-if="title || $slots.actions" class="card-head">
      <div>
        <h2 v-if="title">{{ title }}</h2>
        <p v-if="subtitle" class="sub">{{ subtitle }}</p>
      </div>
      <div v-if="$slots.actions" class="head-actions"><slot name="actions" /></div>
    </header>
    <div :class="['card-body', { flush }]"><slot /></div>
  </section>
</template>

<style scoped>
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  min-width: 0;
}
.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border);
}
h2 {
  margin: 0;
  font-size: 1.02rem;
  color: var(--mhm-slate-dark);
}
.sub {
  margin: 2px 0 0;
  font-size: 0.85rem;
  color: var(--muted);
}
.head-actions {
  display: flex;
  gap: 8px;
}
.card-body {
  padding: 20px;
}
.card-body.flush {
  padding: 0;
}
</style>
