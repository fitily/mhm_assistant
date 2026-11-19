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
