<script setup>
// Cadre dans lequel s'affichera le tableau de bord Superset.
//
// Contrat d'intégration :
//  - `state` pilote l'affichage : loading | error | empty | coming-soon | ready
//  - l'élément `mountEl` (exposé) est TOUJOURS dans le DOM : composables/useSupersetEmbed.js y monte
//    l'iframe du SDK. L'iframe prend 100 % du cadre.
//  - en cas d'erreur, le bouton « Try again » émet `retry`.
import { ref } from 'vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import SkeletonBlock from '@/components/ui/SkeletonBlock.vue'

defineProps({
  state: { type: String, default: 'loading' },
  title: { type: String, default: '' },
  message: { type: String, default: '' }, // détail de l'erreur (état « error »)
})
const emit = defineEmits(['retry'])

const mountEl = ref(null)
const frame = ref(null)
const fullscreen = ref(false)

function toggleFullscreen() {
  fullscreen.value = !fullscreen.value
}

defineExpose({ mountEl })
</script>

<template>
  <div ref="frame" class="viewport" :class="{ fullscreen }">
    <div class="toolbar">
      <span class="vp-title">{{ title || 'Dashboard' }}</span>
      <button
        class="tool"
        type="button"
        :aria-pressed="fullscreen"
        :title="fullscreen ? 'Exit full view' : 'Full view'"
        @click="toggleFullscreen"
      >
        <AppIcon name="expand" :size="18" />
        <span>{{ fullscreen ? 'Exit full view' : 'Full view' }}</span>
      </button>
    </div>

    <div class="stage">
      <!-- Point de montage de l'iframe Superset : toujours présent ET visible (il garde ainsi sa taille
           réelle pendant le chargement ; les états ci-dessous le recouvrent). -->
      <div ref="mountEl" class="mount" />

      <div v-if="state === 'loading'" class="overlay" aria-busy="true" aria-live="polite">
        <div class="skeleton-grid">
          <SkeletonBlock height="22px" width="40%" />
          <SkeletonBlock height="120px" radius="12px" />
          <SkeletonBlock height="200px" radius="12px" />
        </div>
      </div>

      <div v-else-if="state === 'error'" class="overlay">
        <EmptyState icon="alert" tone="danger" title="The dashboard could not be loaded" :text="message || 'Check your connection and try again. If the problem persists, contact the technical team.'">
          <button class="btn" type="button" @click="emit('retry')">Try again</button>
        </EmptyState>
      </div>

      <div v-else-if="state === 'empty'" class="overlay">
        <EmptyState icon="layers" title="No dashboard available" text="No dashboard has been shared with your account yet." />
      </div>

      <div v-else-if="state === 'coming-soon'" class="overlay">
        <EmptyState
          icon="chart"
          title="Dashboard coming soon"
          text="This space will display your Apache Superset dashboard, interactive and filterable, right here."
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.viewport {
  display: flex;
  flex-direction: column;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
}
.viewport.fullscreen {
  position: fixed;
  inset: 0;
  z-index: 900; /* au-dessus du menu, sous la bulle de chat (1000) */
  border-radius: 0;
}
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 16px;
  border-bottom: 1px solid var(--border);
  background: var(--surface-2);
}
.vp-title {
  font-weight: 600;
  color: var(--mhm-slate-dark);
}
.tool {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
  color: var(--muted);
  font-size: 0.85rem;
  font-weight: 600;
}
.tool:hover {
  color: var(--mhm-blue-dark);
  border-color: var(--mhm-blue);
}
.stage {
  position: relative;
  flex: 1;
  min-height: clamp(420px, 68vh, 860px);
}
.fullscreen .stage {
  min-height: 0;
}
.mount,
.mount :deep(iframe) {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  border: 0;
}
.overlay {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  padding: 24px;
  background:
    radial-gradient(circle at 1px 1px, var(--border) 1px, transparent 0) 0 0 / 22px 22px,
    var(--surface);
}
.skeleton-grid {
  width: min(720px, 100%);
  display: grid;
  gap: 16px;
}
@media (max-width: 640px) {
  .tool span {
    display: none;
  }
}
</style>
