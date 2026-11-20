// Menu principal de l'application, filtré par rôle.
// Pour ajouter une page : déclarer la route (router/index.js, avec meta.roles) puis une ligne ici.
// Comme pour les rôles, masquer un lien n'est qu'un confort : la vraie protection est dans le router
// (et, pour les données, dans le backend).
import { ROLE_ADMIN, ROLE_DOCTOR } from './roles'

export const NAV_ITEMS = [
  { name: 'home', to: { name: 'home' }, label: 'Home', icon: 'home', roles: [ROLE_ADMIN, ROLE_DOCTOR] },
  { name: 'analytics', to: { name: 'analytics' }, label: 'Analytics', icon: 'chart', roles: [ROLE_ADMIN] },
  { name: 'news', to: { name: 'news' }, label: 'Medical news', icon: 'news', roles: [ROLE_DOCTOR] },
]

export const navFor = (role) => NAV_ITEMS.filter((item) => item.roles.includes(role))
