// Indicateurs clés de la page Analytics (admin) : valeurs calculées par le backend (GET /v1/kpis).
//  - Mode réel : le backend compte dans la base ; le navigateur ne reçoit que des nombres.
//  - Mode démonstration (VITE_MOCK_AUTH=true) : trois tuiles vides, aucun appel réseau.
import { fetchKpis, isMockAuth } from './api'

const DEMO_KPIS = [
  { key: 'new_patients_7d', label: 'New patients', value: null, hint: 'Demo mode', delta_percent: null, error: false },
  { key: 'admissions_7d', label: 'Admissions', value: null, hint: 'Demo mode', delta_percent: null, error: false },
  { key: 'visits_last_month', label: 'Visits last month', value: null, hint: 'Demo mode', delta_percent: null, error: false },
]

/** @returns {Promise<Array<{key:string,label:string,value:number|null,hint:string,delta_percent:number|null,error:boolean}>>} */
export async function listKpis({ token } = {}) {
  if (isMockAuth) return DEMO_KPIS
  return fetchKpis({ token })
}
