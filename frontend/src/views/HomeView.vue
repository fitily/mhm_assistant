<script setup>
import { computed, defineAsyncComponent } from 'vue'
import { useAuthStore } from '@/stores/auth'

// Une page d'accueil par rôle. Les rôles sans page dédiée (pour l'instant) gardent l'accueil actuel.
// Pour ajouter un rôle : créer sa vue, l'ajouter ici et dans ALIASES / ROLE_LABELS (utils/roles.js).
const HOMES = {
  doctor: defineAsyncComponent(() => import('./DoctorHomeView.vue')),
}
const DefaultHome = defineAsyncComponent(() => import('./DashboardView.vue'))

const auth = useAuthStore()
const Home = computed(() => HOMES[auth.role] || DefaultHome)
</script>

<template>
  <component :is="Home" />
</template>
