// Point d'entrée unique des données « analytics » (tableaux de bord Superset).
// ÉTAT ACTUEL : emplacements réservés, aucun appel réseau, rien n'est connecté à Superset.
//
// CONTRAT pour l'intégration (étape suivante) — il suffit de remplacer le corps de `listDashboards` :
//   GET /v1/superset/dashboards  (admin uniquement) -> [{ key, title, description, available }]
//   `key` est un identifiant court choisi par nous ; l'UUID d'intégration et le jeton invité restent
//   côté backend (POST /v1/superset/guest-token), le navigateur ne manipule jamais de secret.
// Le montage de l'iframe se fera dans l'élément exposé par <DashboardViewport> (`mountEl`).

export const SUPERSET_CONNECTED = false

const PLACEHOLDER_DASHBOARDS = [
  { key: 'dashboard-1', title: 'Dashboard 1', description: 'Reserved slot', available: false },
  { key: 'dashboard-2', title: 'Dashboard 2', description: 'Reserved slot', available: false },
  { key: 'dashboard-3', title: 'Dashboard 3', description: 'Reserved slot', available: false },
]

/** @returns {Promise<Array<{key:string,title:string,description:string,available:boolean}>>} */
export async function listDashboards() {
  return PLACEHOLDER_DASHBOARDS
}
