<script setup>
import { useAuthStore } from '@/stores/auth'
import BrandLogo from '@/components/BrandLogo.vue'

const auth = useAuthStore()
</script>

<template>
  <header class="topbar">
    <div class="topbar-inner">
      <BrandLogo :size="36" />
      <div class="user">
        <span class="avatar" aria-hidden="true">{{ auth.displayName.charAt(0).toUpperCase() }}</span>
        <span class="who">
          <span class="name">{{ auth.displayName }}</span>
          <span v-if="auth.roleLabel" class="role">{{ auth.roleLabel }}</span>
        </span>
        <button class="btn btn-ghost logout" type="button" @click="auth.logout()">
          Se déconnecter
        </button>
      </div>
    </div>
  </header>
</template>

<style scoped>
.topbar {
  position: sticky;
  top: 0;
  z-index: 10;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
}
.topbar-inner {
  max-width: 1100px;
  margin: 0 auto;
  padding: 10px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.user {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.avatar {
  flex: none;
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: var(--mhm-slate);
  color: #fff;
  font-weight: 700;
}
.who {
  display: flex;
  flex-direction: column;
  min-width: 0;
  line-height: 1.2;
}
.name {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 600;
  color: var(--mhm-slate);
}
.role {
  font-size: 0.78rem;
  color: var(--muted);
}
.logout {
  padding: 8px 14px;
}
@media (max-width: 520px) {
  .who {
    display: none;
  }
}
</style>
