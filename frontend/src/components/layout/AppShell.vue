<script setup>
// Cadre commun des pages connectées : menu (selon le rôle), identité de l'utilisateur, contenu.
// Bureau : menu latéral fixe. Mobile : bandeau en haut, menu défilant horizontalement.
import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useChatStore } from '@/stores/chat'
import { navFor } from '@/utils/navigation'
import BrandLogo from '@/components/BrandLogo.vue'
import AppIcon from '@/components/ui/AppIcon.vue'

const auth = useAuthStore()
const chat = useChatStore()
const items = computed(() => navFor(auth.role))
</script>

<template>
  <div class="shell">
    <aside class="sidebar">
      <RouterLink :to="{ name: 'home' }" class="brand" aria-label="Home">
        <BrandLogo :size="70" />
      </RouterLink>

      <nav class="nav" aria-label="Main navigation">
        <RouterLink v-for="item in items" :key="item.name" :to="item.to" class="nav-link">
          <AppIcon :name="item.icon" />
          <span>{{ item.label }}</span>
        </RouterLink>
      </nav>

      <div class="side-bottom">
        <button class="ask" type="button" @click="chat.openFullscreen()">
          <AppIcon name="chat" :size="18" />
          <span>Ask iA'mbovo</span>
        </button>

        <div class="user">
          <span class="avatar" aria-hidden="true">{{ auth.displayName.charAt(0).toUpperCase() }}</span>
          <span class="who">
            <span class="name">{{ auth.displayName }}</span>
            <span v-if="auth.roleLabel" class="role">{{ auth.roleLabel }}</span>
          </span>
          <button class="signout" type="button" title="Sign out" aria-label="Sign out" @click="auth.logout()">
            <AppIcon name="logout" :size="18" />
          </button>
        </div>
      </div>
    </aside>

    <main class="main">
      <div class="main-inner"><slot /></div>
    </main>
  </div>
</template>

<style scoped>
.shell {
  display: grid;
  grid-template-columns: 248px minmax(0, 1fr);
  min-height: 100vh;
}

.sidebar {
  position: sticky;
  top: 0;
  height: 100vh;
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 18px 14px;
  background: var(--surface);
  border-right: 1px solid var(--border);
}
.brand {
  display: flex;
  justify-content: center;
  padding: 4px 0 10px;
  border-bottom: 1px solid var(--border);
}

.nav {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.nav-link {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 11px 14px;
  border-radius: 10px;
  color: var(--muted);
  font-weight: 600;
  text-decoration: none;
  transition: background 0.15s, color 0.15s;
}
.nav-link:hover {
  background: var(--surface-2);
  color: var(--mhm-slate-dark);
}
.nav-link.router-link-exact-active {
  background: var(--mhm-blue-50);
  color: var(--mhm-blue-dark);
}

.side-bottom {
  margin-top: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.ask {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 11px 14px;
  border: 0;
  border-radius: 10px;
  background: var(--mhm-blue);
  color: #fff;
  font-weight: 600;
  transition: background 0.15s;
}
.ask:hover {
  background: var(--mhm-blue-dark);
}

.user {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--surface-2);
}
.avatar {
  flex: none;
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: var(--mhm-slate);
  color: #fff;
  font-weight: 700;
}
.who {
  min-width: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  line-height: 1.25;
}
.name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 600;
  color: var(--mhm-slate-dark);
}
.role {
  font-size: 0.78rem;
  color: var(--muted);
}
.signout {
  flex: none;
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--muted);
}
.signout:hover {
  background: var(--danger-bg);
  color: var(--danger);
}

.main {
  min-width: 0;
}
.main-inner {
  max-width: var(--content-max);
  margin: 0 auto;
  padding: clamp(20px, 2.4vw, 32px) var(--page-gutter) 120px; /* marge basse : la bulle de chat ne masque rien */
}

@media (max-width: 900px) {
  .shell {
    grid-template-columns: minmax(0, 1fr);
  }
  .sidebar {
    position: sticky;
    z-index: 20;
    height: auto;
    flex-direction: row;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px 12px;
    padding: 8px 14px;
    border-right: 0;
    border-bottom: 1px solid var(--border);
  }
  .sidebar :deep(.brand) {
    --s: 40px !important;
  }
  .brand {
    padding: 0;
    border: 0;
  }
  .side-bottom {
    margin: 0 0 0 auto;
    flex-direction: row;
    align-items: center;
  }
  .ask span,
  .who {
    display: none;
  }
  .ask {
    padding: 9px 11px;
  }
  .user {
    padding: 4px;
    border: 0;
    background: transparent;
  }
  .nav {
    order: 3;
    flex: 1 0 100%;
    flex-direction: row;
    overflow-x: auto;
    gap: 6px;
    padding-bottom: 2px;
  }
  .nav-link {
    flex: none;
    padding: 8px 12px;
  }
  .main-inner {
    padding: 20px var(--page-gutter) 110px;
  }
}
</style>
