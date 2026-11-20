<script setup>
// État vide / erreur / « bientôt disponible », avec icône, texte et zone d'actions (slot par défaut).
import AppIcon from './AppIcon.vue'

defineProps({
  icon: { type: String, default: 'info' },
  title: { type: String, required: true },
  text: { type: String, default: '' },
  tone: { type: String, default: 'neutral' }, // neutral | danger
})
</script>

<template>
  <div class="empty" :class="tone" role="status">
    <span class="icon"><AppIcon :name="icon" :size="26" /></span>
    <h3>{{ title }}</h3>
    <p v-if="text">{{ text }}</p>
    <div v-if="$slots.default" class="actions"><slot /></div>
  </div>
</template>

<style scoped>
.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 8px;
  padding: 32px 20px;
}
.icon {
  width: 56px;
  height: 56px;
  display: grid;
  place-items: center;
  border-radius: 16px;
  background: var(--mhm-blue-50);
  color: var(--mhm-blue);
}
.danger .icon {
  background: var(--danger-bg);
  color: var(--danger);
}
h3 {
  margin: 6px 0 0;
  font-size: 1.08rem;
  color: var(--mhm-slate-dark);
}
p {
  margin: 0;
  max-width: 460px;
  color: var(--muted);
}
.actions {
  margin-top: 10px;
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: center;
}
</style>
