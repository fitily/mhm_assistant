import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { guestOnly: true, title: 'Login' },
  },
  {
    path: '/',
    name: 'home',
    component: () => import('@/views/HomeView.vue'),
    meta: { requiresAuth: true, title: 'Home' },
  },
  {
    // Espace administrateur : tableaux de bord (Superset, à venir)
    path: '/analytics',
    name: 'analytics',
    component: () => import('@/views/AnalyticsView.vue'),
    meta: { requiresAuth: true, roles: ['admin'], title: 'Analytics' },
  },
  {
    // Espace médecin : actualités médicales (flux à venir)
    path: '/news',
    name: 'news',
    component: () => import('@/views/NewsView.vue'),
    meta: { requiresAuth: true, roles: ['doctor'], title: 'Medical news' },
  },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return { name: 'login', query: to.fullPath !== '/' ? { redirect: to.fullPath } : {} }
  }
  // Page réservée à certains rôles : retour à l'accueil (confort ; le backend reste la vraie barrière)
  if (to.meta.roles && !to.meta.roles.includes(auth.role)) {
    return { name: 'home' }
  }
  if (to.meta.guestOnly && auth.isAuthenticated) {
    return { name: 'home' }
  }
})

router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} · iA'mbovo` : 'iA\'mbovo'
})

export default router
