import { ApiError } from './errors'

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

// Comptes de démonstration (mot de passe : demo1234)
const DEMO_ACCOUNTS = {
  'demo@mhm.org': { name: 'Fitily', role: 'admin' },
  'medecin@mhm.org': { name: 'Doctor demo', role: 'doctor' },
}

export async function login(username, password) {
  await sleep(900)
  const email = username.trim().toLowerCase()
  const account = DEMO_ACCOUNTS[email]
  if (account && password === 'demo1234') {
    return { token: 'mock-token', user: { name: account.name, email, role: account.role } }
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
