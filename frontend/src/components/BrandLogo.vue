<script setup>
defineProps({
  /** Hauteur du logo en pixels (la largeur suit automatiquement) */
  size: { type: Number, default: 48 },
  /** Place le logo sur une pastille blanche (utile sur fond coloré) */
  framed: { type: Boolean, default: false },
})

// Fichier à placer dans frontend/public/mhm-logo.png
const logoSrc = '/mhm-logo.png'
</script>

<template>
  <span class="brand" :class="{ framed }" :style="{ '--s': size + 'px' }">
    <img :src="logoSrc" alt="Mobile Hilfe Madagaskar e.V. (MHM)" />
  </span>
</template>

<style scoped>
.brand {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.brand img {
  display: block;
  height: var(--s);
  width: auto;
  max-width: 100%;
  object-fit: contain;
}
.framed {
  background: #fff;
  padding: 18px 26px;
  border-radius: 20px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
}
</style>
