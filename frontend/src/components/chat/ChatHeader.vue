<script setup>
defineProps({
  fullscreen: { type: Boolean, default: false },
})

defineEmits(['minimize', 'toggle-fullscreen', 'close'])
</script>

<template>
  <header class="header">
    <div class="title">
      <span class="avatar" aria-hidden="true">
        <img src="/images/iambovo-icon.jpeg" alt="" />
      </span>
      <div>
        <strong>iA'mbovo</strong>
        <small>Data and documents</small>
      </div>
    </div>
    <div class="actions">
      <button
        type="button"
        title="Réduire (la conversation est conservée)"
        aria-label="Réduire la fenêtre"
        @click="$emit('minimize')"
      >
        <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path fill="currentColor" d="M5 11h14v2H5z"/></svg>
      </button>
      <button
        type="button"
        :title="fullscreen ? 'Revenir au mode bulle' : 'Ouvrir en plein écran'"
        :aria-label="fullscreen ? 'Revenir au mode bulle' : 'Ouvrir en plein écran'"
        :aria-pressed="fullscreen"
        @click="$emit('toggle-fullscreen')"
      >
        <svg v-if="!fullscreen" viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path fill="currentColor" d="M4 4h6v2H6v4H4V4Zm10 0h6v6h-2V6h-4V4ZM4 14h2v4h4v2H4v-6Zm14 0h2v6h-6v-2h4v-4Z"/></svg>
        <svg v-else viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path fill="currentColor" d="M9 3h2v6H5V7h4V3Zm10 4v2h-6V3h2v4h4ZM9 15h2v6H9v-4H5v-2h4Zm4 0h6v2h-4v4h-2v-6Z"/></svg>
      </button>
      <button
        type="button"
        title="Fermer et effacer la conversation"
        aria-label="Fermer et effacer la conversation"
        @click="$emit('close')"
      >
        <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path fill="currentColor" d="m6.400 5 5.600 5.600L17.600 5 19 6.400 13.400 12l5.600 5.600-1.400 1.400-5.600-5.600L6.400 19 5 17.600 10.600 12 5 6.400 6.400 5Z"/></svg>
      </button>
    </div>
  </header>
</template>

<style scoped>
.header {
  flex: none;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 12px 12px 16px;
  color: #fff;
  background: linear-gradient(135deg, var(--mhm-blue), var(--mhm-slate));
}
.title {
  display: flex;
  align-items: center;
  gap: 10px;
}
.title strong {
  display: block;
  line-height: 1.15;
}
.title small {
  opacity: 0.85;
  font-size: 0.76rem;
}
.avatar {
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  overflow: hidden;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
}
.avatar img {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: cover;
}
.actions {
  display: flex;
  gap: 2px;
}
.actions button {
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: #fff;
}
.actions button:hover {
  background: rgba(255, 255, 255, 0.2);
}
</style>
