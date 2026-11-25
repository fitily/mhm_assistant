# MHM Assistant — Frontend (Vue 3)

Interface web de l'assistant IA de MHM : page de connexion, interface principale et bulle de chat flottante.

**Stack** : Vue 3 · Vite · Vue Router · Pinia · marked + DOMPurify (rendu Markdown sécurisé).

## 1. Ajouter le logo MHM

Copier le logo officiel dans :

```
frontend/public/mhm-logo.png
```

Il est utilisé sur la page de connexion, dans l'en-tête et comme icône d'onglet.
Tant que le fichier est absent, une pastille « MHM » s'affiche à la place.

## 2. Lancer en développement

Prérequis : Node.js 18 ou plus récent.

```bash
cd frontend
cp .env.example .env     # puis adapter si besoin
npm install
npm run dev              # http://localhost:5173
```

### Mode démonstration (sans backend)

Avec `VITE_USE_MOCK=true` dans `.env`, l'application utilise de fausses réponses locales :

- identifiant : `demo@mhm.org`
- mot de passe : `demo1234`

Essayer par exemple « Donne-moi un tableau de répartition par région » ou
« Que disent les documents sur la prévention ? » pour voir tableaux, statistiques et sources.

### Brancher le vrai backend

Mettre `VITE_USE_MOCK=false`. En développement, les appels `/api/...` sont redirigés par Vite
vers `VITE_BACKEND_URL` (par défaut `http://localhost:8000`).

## 3. Contrat d'API attendu

Tout est centralisé dans `src/services/api.js` : si votre backend FastAPI utilise d'autres routes
ou d'autres noms de champs, c'est le seul fichier à adapter.

**`POST /api/auth/login`**

```json
// requête
{ "username": "prenom.nom@mhm.org", "password": "..." }
// réponse
{ "access_token": "...", "user": { "name": "Prénom Nom", "email": "..." } }
```

**`POST /api/chat`** (en-tête `Authorization: Bearer <token>`)

```json
// requête
{ "message": "Quelle est la répartition par région ?", "session_id": "abc123" }
// réponse
{
  "session_id": "abc123",
  "answer": "Texte en **Markdown**, avec tableaux si besoin.",
  "stats": [{ "label": "Total", "value": "3 220" }],
  "sources": [{ "title": "Nom du document", "page": 12, "url": null }]
}
```

- `answer` : Markdown (titres, listes, gras, tableaux, citations, code).
- `stats` (optionnel) : cartes de chiffres clés affichées sous la réponse.
- `sources` (optionnel) : références documentaires affichées en pastilles (`url` rend la pastille cliquable).
- Une erreur HTTP 401 sur `/chat` déconnecte l'utilisateur ; les autres erreurs s'affichent dans le chat avec un bouton « Réessayer ».
- Les messages d'erreur sont lus dans `detail` (format FastAPI) ou `message`.

## 4. Docker

```bash
cd frontend
docker build -t mhm-frontend .
docker run -p 8080:80 mhm-frontend      # http://localhost:8080
```

Le conteneur sert l'application avec nginx et transmet `/api/` au service nommé `backend`
(port 8000) : ce nom correspond au service du `docker-compose` du projet. Voir `nginx.conf`.
Pour une image en mode démonstration : `docker build --build-arg VITE_USE_MOCK=true -t mhm-frontend .`

## 5. Structure

```
frontend/
├── public/                  # mhm-logo.png à placer ici
├── src/
│   ├── components/
│   │   ├── BrandLogo.vue    # logo + repli « MHM »
│   │   └── chat/            # widget, en-tête, historique, conversation, messages, saisie
│   ├── router/index.js      # routes + protection (connexion obligatoire)
│   ├── services/            # api.js (appels), mock.js (démo), errors.js
│   ├── stores/              # auth.js (session), chat.js (conversation)
│   ├── styles/main.css      # couleurs MHM #0093D7 et #375D77
│   ├── utils/markdown.js    # Markdown → HTML assaini
│   ├── views/               # LoginView, DashboardView
│   ├── App.vue
│   └── main.js
├── Dockerfile · nginx.conf
└── vite.config.js
```

## 6. Comportement du chat

- Bulle en bas à droite, visible sur toutes les pages une fois connecté ; pastille rouge si une réponse arrive fenêtre fermée.
- **Plein écran** : ouvre une interface dédiée avec l'historique à gauche. Sélectionner un titre recharge la conversation ; « Nouvelle » démarre un nouvel échange.
- **Réduire (−)** : cache la fenêtre en conservant les conversations. **Fermer (×)** : efface la conversation active ; la déconnexion efface tout l'historique.
- Historique conservé pendant la session du navigateur (même après rechargement de la page).
- Entrée envoie le message, Maj+Entrée ajoute un retour à la ligne. Échap repasse du plein écran à la bulle, puis réduit la fenêtre.
- Mobile (≤ 640 px) : la fenêtre passe en plein écran.

## 7. Page d'accueil par rôle

`/` affiche `HomeView.vue`, qui choisit la page selon le rôle de l'utilisateur (champ `role` ou `roles`
renvoyé par Laravel à la connexion ; « medecin », « Médecin » et « doctor » sont équivalents).

| Rôle | Page |
|---|---|
| Médecin | `views/DoctorHomeView.vue` : **Breaking News** (OMS, OMS Afrique) et **Scientific Research** (The Lancet, NEJM) |
| Autres / sans rôle | `views/DashboardView.vue` (accueil standard) |

Ajouter un rôle : créer sa vue, l'enregistrer dans `HomeView.vue`, puis dans `ALIASES` et `ROLE_LABELS` (`utils/roles.js`).

La page Médecin appelle `GET /api/v1/feeds/breaking-news` et `/research` (voir `services/api.js`, `stores/feeds.js`).
Chaque source garde son état : si l'une tombe, un bandeau le dit et les autres restent affichées.

Sans backend : `VITE_MOCK_FEEDS=true` affiche des articles fictifs. Pour essayer un autre rôle avec la connexion
fictive : `VITE_MOCK_ROLE=infirmier`.

```
src/
├── components/feeds/   # FeedSection (en-tête, filtres, états), BreakingNewsSection, ResearchSection, FeedMeta
├── components/layout/  # AppTopbar (barre commune aux accueils)
├── stores/feeds.js     # chargement, cache de 5 min, actualisation
├── utils/              # roles.js, dates.js
└── views/              # HomeView (aiguillage), DoctorHomeView
```
