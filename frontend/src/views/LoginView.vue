<script setup>
import { reactive, ref, computed, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { isMockAuth } from '@/services/api'
import BrandLogo from '@/components/BrandLogo.vue'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const form = reactive({ username: '', password: '' })
const touched = reactive({ username: false, password: false })
const showPassword = ref(false)
const loading = ref(false)
const serverError = ref('')
const usernameInput = ref(null)
const passwordInput = ref(null)

const errors = computed(() => {
  const usernameValue = form.username.trim()
  let username = ''
  if (!usernameValue) username = 'Email address is required.'
  else if (usernameValue.includes('@') && !/^\S+@\S+\.\S+$/.test(usernameValue)) {
    username = 'Adresse e-mail invalide.'
  }
  return {
    username,
    password: form.password ? '' : 'Password is required.',
  }
})

async function submit() {
  touched.username = true
  touched.password = true
  serverError.value = ''

  if (errors.value.username) return usernameInput.value?.focus()
  if (errors.value.password) return passwordInput.value?.focus()

  loading.value = true
  try {
    await auth.login(form.username, form.password)
    await router.replace(typeof route.query.redirect === 'string' ? route.query.redirect : '/')
  } catch (error) {
    serverError.value = error.message || 'Connexion impossible.'
    form.password = ''
    await nextTick()
    passwordInput.value?.focus()
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="login">
    <section class="hero" aria-label="Mobile Hilfe Madagaskar e.V.">
      <BrandLogo :size="170" framed />
      <span class="circle c1" aria-hidden="true"></span>
      <span class="circle c2" aria-hidden="true"></span>
    </section>

    <section class="panel">
      <form class="card" novalidate @submit.prevent="submit">
        <h2>Connexion</h2>
        <div v-if="serverError" class="alert" role="alert">
          <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path fill="currentColor" d="M12 2 1 21h22L12 2Zm1 14h-2v-2h2v2Zm0-4h-2V8h2v4Z"/></svg>
          <span>{{ serverError }}</span>
        </div>

        <div class="field">
          <label for="username">Email</label>
          <input
            id="username"
            ref="usernameInput"
            v-model="form.username"
            type="text"
            autocomplete="username"
            inputmode="email"
            placeholder="prenom.nom@mhm.org"
            :class="{ invalid: touched.username && errors.username }"
            :aria-invalid="!!(touched.username && errors.username)"
            aria-describedby="username-error"
            :disabled="loading"
            @blur="touched.username = true"
          />
          <p v-if="touched.username && errors.username" id="username-error" class="error">
            {{ errors.username }}
          </p>
        </div>

        <div class="field">
          <label for="password">Password</label>
          <div class="password-wrap">
            <input
              id="password"
              ref="passwordInput"
              v-model="form.password"
              :type="showPassword ? 'text' : 'password'"
              autocomplete="current-password"
              placeholder="••••••••"
              :class="{ invalid: touched.password && errors.password }"
              :aria-invalid="!!(touched.password && errors.password)"
              aria-describedby="password-error"
              :disabled="loading"
              @blur="touched.password = true"
            />
            <button
              type="button"
              class="toggle"
              :aria-label="showPassword ? 'Masquer le mot de passe' : 'Afficher le mot de passe'"
              :aria-pressed="showPassword"
              @click="showPassword = !showPassword"
            >
              <svg v-if="!showPassword" viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path fill="currentColor" d="M12 5C7 5 2.7 8.1 1 12c1.7 3.9 6 7 11 7s9.3-3.1 11-7c-1.7-3.9-6-7-11-7Zm0 11a4 4 0 1 1 0-8 4 4 0 0 1 0 8Zm0-6.4a2.4 2.4 0 1 0 0 4.8 2.4 2.4 0 0 0 0-4.8Z"/></svg>
              <svg v-else viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path fill="currentColor" d="m3.3 2 18.7 18.7-1.3 1.3-3.2-3.2A11.6 11.6 0 0 1 12 19C7 19 2.7 15.9 1 12a12 12 0 0 1 4.3-5.2L2 3.3 3.3 2Zm8.7 3c5 0 9.3 3.1 11 7a12 12 0 0 1-2.8 4l-3.1-3.1a4 4 0 0 0-5-5L8.5 5.6A11.700 11.700 0 0 1 12 5Z"/></svg>
            </button>
          </div>
          <p v-if="touched.password && errors.password" id="password-error" class="error">
            {{ errors.password }}
          </p>
        </div>

        <button class="btn submit" type="submit" :disabled="loading">
          <span v-if="loading" class="spinner" aria-hidden="true"></span>
          <span>{{ loading ? 'Connexion en cours…' : 'Se connecter' }}</span>
        </button>
        <p v-if="isMockAuth" class="demo">
          Connexion temporaire — identifiant : <strong>demo@mhm.org</strong>, mot de passe :
          <strong>demo1234</strong>
        </p>
      </form>
    </section>
  </main>
</template>

<style scoped src="./LoginView.css"></style>
