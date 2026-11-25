import { ApiError } from './errors'

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

export async function login(username, password) {
  await sleep(900)
  if (username.trim().toLowerCase() === 'demo@mhm.org' && password === 'demo1234') {
    return {
      token: 'mock-token',
      // VITE_MOCK_ROLE permet d'essayer une autre page d'accueil (ex. « infirmier »).
      user: {
        name: 'Utilisateur démo',
        email: 'demo@mhm.org',
        role: import.meta.env.VITE_MOCK_ROLE || 'medecin',
      },
    }
  }
  throw new ApiError('Identifiant ou mot de passe incorrect.', 401)
}

// Les réponses imitent exactement le format du backend (/v1/chat).
export async function sendMessage({ message }) {
  await sleep(1400)
  const q = message.toLowerCase()

  if (/(tableau|répartition|region|région|statist|combien|nombre|taux)/.test(q)) {
    return {
      text: [
        '**Mode démonstration** : les chiffres du tableau sont fictifs et servent uniquement à tester l’affichage.',
        '',
        'Voici la répartition par région :',
      ].join('\n'),
      sender: 'IA’mbovo',
      mode: 'SQL',
      notes: ['Résultats fictifs (mode démonstration).'],
      sources: [],
      data: {
        columns: ['Région', 'Effectif', 'Part (%)'],
        rows: [
          ['Analamanga', '1 240', '38,5'],
          ['Vakinankaratra', '860', '26,7'],
          ['Haute Matsiatra', '640', '19,9'],
          ['Autres', '480', '14,9'],
        ],
      },
    }
  }

  if (/(document|rapport|pdf|prévention|prevention|traitement|source|politique)/.test(q)) {
    return {
      text: [
        '**Mode démonstration** : exemple de réponse issue des documents.',
        '',
        'D’après les documents indexés, on peut retenir trois points :',
        '',
        '1. La prévention repose sur plusieurs leviers complémentaires.',
        '2. L’accès au dépistage et au traitement reste un enjeu central.',
        '3. Le suivi régulier améliore les résultats à long terme.',
      ].join('\n'),
      sender: 'IA’mbovo',
      mode: 'DOCS',
      notes: [],
      sources: [
        { score: 0.82, label: 'Rapport national (exemple), p. 12' },
        { score: 0.74, label: 'Guide de prise en charge (exemple), p. 34' },
      ],
      data: null,
    }
  }

  return {
    text: [
      'Bonjour ! Je suis l’assistant IA de MHM (**mode démonstration**).',
      '',
      'Je peux :',
      '',
      '- répondre à des questions chiffrées sur les données ;',
      '- rechercher des informations dans les documents ;',
      '- citer mes sources.',
      '',
      'Essayez : *« Donne-moi un tableau de répartition par région »* ou *« Que disent les documents sur la prévention ? »*',
    ].join('\n'),
    sender: 'IA’mbovo',
    mode: 'CHAT',
    notes: [],
    sources: [],
    data: null,
  }
}

// Données de démonstration des flux de veille (même format que GET /v1/feeds/...).
// Les titres sont des exemples fictifs : ils servent uniquement à tester l'affichage.
const ago = (hours) => new Date(Date.now() - hours * 3600 * 1000).toISOString()

function demoItem(id, sourceId, sourceName, hours, title, summary, tag = null) {
  return {
    id: `demo-${id}`,
    title: `Exemple : ${title}`,
    summary,
    url: `https://example.org/demo/${id}`,
    published_at: ago(hours),
    source_id: sourceId,
    source_name: sourceName,
    tag,
  }
}

const DEMO_FEEDS = {
  'breaking-news': {
    items: [
      demoItem('n1', 'afro', 'OMS Afrique', 3, 'riposte à une flambée de choléra dans plusieurs districts',
        'Les équipes de surveillance renforcent le dépistage, la prise en charge et l’approvisionnement en eau potable dans les zones touchées.', 'alerte'),
      demoItem('n2', 'who', 'OMS', 9, 'nouvelles recommandations pour la prise en charge de l’hypertension',
        'L’organisation actualise ses orientations pour les soins primaires, avec un accent sur le traitement combiné à dose fixe.'),
      demoItem('n3', 'who', 'OMS', 26, 'campagne de vaccination contre la rougeole',
        'Plusieurs pays lancent une campagne de rattrapage pour les enfants non vaccinés.'),
      demoItem('n4', 'afro', 'OMS Afrique', 31, 'point de situation sur la fièvre de la vallée du Rift',
        'Mise à jour épidémiologique et mesures de prévention recommandées pour les professionnels de santé.', 'alerte'),
      demoItem('n5', 'who', 'OMS', 52, 'rapport sur la résistance aux antimicrobiens',
        'Un nouveau rapport mondial fait le point sur les tendances de résistance des principales bactéries.'),
      demoItem('n6', 'who', 'OMS', 80, 'lancement d’un guide sur la santé maternelle et néonatale',
        'Le guide rassemble les pratiques essentielles avant, pendant et après l’accouchement.'),
    ],
    sources: [
      { id: 'who', name: 'OMS', status: 'ok', via: 'rss', fetched_at: ago(0.1), count: 4 },
      { id: 'afro', name: 'OMS Afrique', status: 'ok', via: 'rss', fetched_at: ago(0.1), count: 2 },
    ],
  },
  research: {
    items: [
      demoItem('r1', 'nejm', 'NEJM', 5, 'essai de phase 3 d’un nouveau traitement de la néphropathie à IgA',
        'Analyse intermédiaire d’un essai randomisé chez des adultes à risque de progression.'),
      demoItem('r2', 'lancet', 'The Lancet', 12, 'efficacité d’une stratégie de dépistage du paludisme en zone endémique',
        'Essai en grappes comparant deux approches de dépistage et de traitement.'),
      demoItem('r3', 'nejm', 'NEJM', 30, 'vaccin thérapeutique et mélanome opéré',
        'Résultats d’un essai combinant vaccin à ARNm et immunothérapie après résection.'),
      demoItem('r4', 'lancet', 'The Lancet', 48, 'charge mondiale des maladies cardiovasculaires 1990-2025',
        'Estimations par pays et par facteur de risque.'),
      demoItem('r5', 'lancet', 'The Lancet', 70, 'antibiothérapie courte dans la pneumonie de l’enfant',
        'Méta-analyse de données individuelles issues de plusieurs essais.'),
      demoItem('r6', 'nejm', 'NEJM', 96, 'thérapie génique sous-rétinienne dans la rétinoschisis liée à l’X',
        'Série de cas avec suivi à douze mois.'),
    ],
    sources: [
      { id: 'lancet', name: 'The Lancet', status: 'ok', via: 'rss', fetched_at: ago(0.1), count: 3 },
      { id: 'nejm', name: 'NEJM', status: 'ok', via: 'rss', fetched_at: ago(0.1), count: 3 },
    ],
  },
}

export async function getFeed(kind) {
  await sleep(700)
  return { ...DEMO_FEEDS[kind], generated_at: new Date().toISOString() }
}
