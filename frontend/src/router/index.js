import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { guestOnly: true, title: 'Connexion' },
  },
  {
    path: '/',
    name: 'home',
    component: () => import('@/views/DashboardView.vue'),
    meta: { requiresAuth: true, title: 'Accueil' },
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
  if (to.meta.guestOnly && auth.isAuthenticated) {
    return { name: 'home' }
  }
})

router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} · MHM Assistant` : 'MHM Assistant'
})

export default router
