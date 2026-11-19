import { marked } from 'marked'
import DOMPurify from 'dompurify'

const renderer = new marked.Renderer()

// Tableaux enveloppés dans un conteneur pour permettre le défilement horizontal
renderer.table = (header, body) =>
  `<div class="table-wrap"><table><thead>${header}</thead><tbody>${body}</tbody></table></div>`

marked.setOptions({ gfm: true, breaks: true, renderer })

// Les liens s'ouvrent dans un nouvel onglet
DOMPurify.addHook('afterSanitizeAttributes', (node) => {
  if (node.tagName === 'A') {
    node.setAttribute('target', '_blank')
    node.setAttribute('rel', 'noopener noreferrer')
  }
})

export function renderMarkdown(text) {
  const html = marked.parse(text || '')
  return DOMPurify.sanitize(html, { ADD_ATTR: ['target'] })
}
