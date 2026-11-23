// Point d'entrée unique des données « analytics » (tableaux de bord Superset).
//
//  - Mode réel : le catalogue et les jetons invités viennent du backend (/v1/superset/..., admin uniquement).
//    Le navigateur ne reçoit qu'un jeton invité limité à UN dashboard et de courte durée : jamais de secret.
//  - Mode démonstration (VITE_MOCK_AUTH=true) : trois emplacements vides, aucun appel réseau.
import { fetchDashboards, fetchGuestAccess, isMockAuth } from './api'

export const SUPERSET_LIVE = !isMockAuth

const PLACEHOLDER_DASHBOARDS = [
  { key: 'dashboard-1', title: 'Dashboard 1', description: 'Reserved slot', available: false },
  { key: 'dashboard-2', title: 'Dashboard 2', description: 'Reserved slot', available: false },
  { key: 'dashboard-3', title: 'Dashboard 3', description: 'Reserved slot', available: false },
]

/** @returns {Promise<Array<{key:string,title:string,description:string,available:boolean}>>} */
export async function listDashboards({ token } = {}) {
  if (isMockAuth) return PLACEHOLDER_DASHBOARDS
  return fetchDashboards({ token })
}

/** Jeton invité + informations d'intégration pour le dashboard `key`. */
export function requestGuestAccess({ key, token }) {
  return fetchGuestAccess({ key, token })
}
