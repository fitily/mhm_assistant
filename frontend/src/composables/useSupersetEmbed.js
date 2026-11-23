// Monte / démonte un dashboard Superset dans un élément de la page (SDK officiel @superset-ui/embedded-sdk).
//
// Déroulement : 1) on demande un jeton invité au backend (clé du catalogue) ; 2) le SDK crée l'iframe
// et lui transmet le jeton ; 3) le SDK rappelle `fetchGuestToken` tout seul avant l'expiration.
//
// États exposés : idle | loading | ready | error
import { onBeforeUnmount, ref } from 'vue'
import { embedDashboard } from '@superset-ui/embedded-sdk'
import { requestGuestAccess } from '@/services/analytics'

export function useSupersetEmbed({ getToken, onUnauthorized } = {}) {
  const state = ref('idle')
  const error = ref('')

  let handle = null // { unmount } renvoyé par le SDK
  let run = 0 // numéro de la demande en cours : une réponse tardive d'un ancien choix est ignorée

  function unmount() {
    if (handle) {
      try {
        handle.unmount()
      } catch {
        /* l'iframe est déjà partie */
      }
      handle = null
    }
  }

  async function mount(dashboard, el) {
    const me = ++run
    unmount()
    state.value = 'loading'
    error.value = ''

    // Chaque affichage a son propre conteneur : le « unmount » d'un ancien dashboard ne peut pas
    // effacer le nouveau.
    const holder = document.createElement('div')
    holder.style.cssText = 'position:absolute;inset:0'
    el.replaceChildren(holder)

    try {
      const first = await requestGuestAccess({ key: dashboard.key, token: getToken() })
      if (me !== run) return

      let firstUsed = false
      const embedded = await embedDashboard({
        id: first.dashboard_id,
        supersetDomain: first.superset_domain,
        mountPoint: holder,
        iframeTitle: dashboard.title,
        dashboardUiConfig: { hideTitle: true, hideTab: false, hideChartControls: false },
        fetchGuestToken: async () => {
          if (!firstUsed) {
            firstUsed = true
            return first.token // le jeton déjà obtenu sert pour le premier affichage
          }
          return (await requestGuestAccess({ key: dashboard.key, token: getToken() })).token
        },
      })

      if (me !== run) {
        embedded.unmount()
        return
      }
      handle = embedded
      state.value = 'ready'
    } catch (err) {
      if (me !== run) return
      if (err?.status === 401) onUnauthorized?.()
      holder.remove()
      error.value = err?.message || 'Le dashboard n’a pas pu être chargé.'
      state.value = 'error'
    }
  }

  function reset() {
    run++
    unmount()
    state.value = 'idle'
    error.value = ''
  }

  onBeforeUnmount(reset)

  return { state, error, mount, reset }
}
