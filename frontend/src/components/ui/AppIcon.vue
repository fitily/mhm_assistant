<script setup>
// Icônes en SVG intégré (aucune dépendance). Pour en ajouter une : une ligne dans PATHS (grille 24x24).
defineProps({
  name: { type: String, required: true },
  size: { type: Number, default: 20 },
})

const PATHS = {
  home: 'M12 3 2 12h3v8h5v-5h4v5h5v-8h3L12 3Z',
  chart: 'M3 3h2v18H3V3Zm4 10h3v8H7v-8Zm5-6h3v14h-3V7Zm5 3h3v11h-3V10Z',
  news: 'M4 4h13v16H6a2 2 0 0 1-2-2V4Zm15 4h1a1 1 0 0 1 1 1v9a2 2 0 0 1-2 2h-1V8ZM7 8h7V6H7v2Zm0 4h7v-2H7v2Zm0 4h7v-2H7v2Z',
  doc: 'M6 2h9l5 5v15H6V2Zm8 1.5V8h4.5L14 3.5ZM8 12h8v1.5H8V12Zm0 3.5h8V17H8v-1.5Z',
  chat: 'M4 4h16v12H8l-4 4V4Z',
  help: 'M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20Zm1 15h-2v-2h2v2Zm1.1-5.2-.9.9c-.5.5-.7.9-.7 1.8h-1.5v-.4c0-.8.3-1.5.9-2.1l1.2-1.2a1.5 1.5 0 1 0-2.6-1H8.5a3.5 3.5 0 1 1 5.6 2Z',
  logout: 'M10 4H4v16h6v-2H6V6h4V4Zm5 4-1.4 1.4 1.6 1.6H9v2h6.2l-1.6 1.6L15 16l4-4-4-4Z',
  refresh: 'M17.7 6.3A8 8 0 1 0 20 12h-2a6 6 0 1 1-1.8-4.2L13 11h8V3l-3.3 3.3Z',
  expand: 'M4 4h6v2H6v4H4V4Zm10 0h6v6h-2V6h-4V4ZM4 14h2v4h4v2H4v-6Zm14 0h2v6h-6v-2h4v-4Z',
  search: 'M10 4a6 6 0 1 0 3.7 10.7l4.8 4.8 1.4-1.4-4.8-4.8A6 6 0 0 0 10 4Zm0 2a4 4 0 1 1 0 8 4 4 0 0 1 0-8Z',
  alert: 'M12 2 1 21h22L12 2Zm1 14h-2v-2h2v2Zm0-4h-2V9h2v3Z',
  flask: 'M9 2h6v2h-1v5.5l5 8.5a2 2 0 0 1-1.7 3H6.7A2 2 0 0 1 5 18l5-8.5V4H9V2Z',
  info: 'M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20Zm1 15h-2v-6h2v6Zm0-8h-2V7h2v2Z',
  external: 'M14 3h7v7h-2V6.4l-8.3 8.3-1.4-1.4L17.6 5H14V3ZM5 5h6v2H7v10h10v-4h2v6H5V5Z',
  arrow: 'M5 11h11.2l-4.6-4.6L13 5l7 7-7 7-1.4-1.4 4.6-4.6H5v-2Z',
  layers: 'M12 2 2 7l10 5 10-5-10-5Zm-7.4 9L2 12l10 5 10-5-2.6-1L12 14 4.6 11Zm0 5L2 17l10 5 10-5-2.6-1L12 19l-7.4-3Z',
}
</script>

<template>
  <svg viewBox="0 0 24 24" :width="size" :height="size" aria-hidden="true" focusable="false">
    <path fill="currentColor" :d="PATHS[name] || PATHS.info" />
  </svg>
</template>
