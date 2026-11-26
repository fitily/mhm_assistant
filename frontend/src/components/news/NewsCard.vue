<script setup>
// Article d'actualité, présenté comme sur la page « News » de l'OMS : image à gauche, texte à droite.
//   catégorie · source · date  /  titre (lien)  /  résumé (2 lignes)
// Sans image (revues, image absente ou qui ne se charge pas) : vignette de remplacement aux couleurs MHM.
// Sans `url`, le titre n'est pas cliquable. Format attendu : voir le contrat dans services/news.js.
import { computed, ref, watch } from 'vue'
import AppIcon from '@/components/ui/AppIcon.vue'
import { formatDate } from '@/utils/format'

const props = defineProps({ article: { type: Object, required: true } })

const META = {
  breaking: { label: 'Breaking', icon: 'alert' },
  research: { label: 'Research', icon: 'flask' },
  update: { label: 'Update', icon: 'news' },
}
const meta = computed(() => META[props.article.category] || META.update)
const date = computed(() => formatDate(props.article.published_at))

// Image : uniquement en https (le backend ne transmet déjà que des images des sources connues).
const failed = ref(false)
watch(() => props.article.image, () => (failed.value = false))
const image = computed(() => (!failed.value && /^https:\/\//i.test(props.article.image || '') ? props.article.image : null))
</script>

<template>
  <article class="news" :class="article.category">
    <component
      :is="article.url ? 'a' : 'div'"
      class="thumb"
      v-bind="article.url ? { href: article.url, target: '_blank', rel: 'noopener noreferrer', tabindex: -1, 'aria-hidden': 'true' } : {}"
    >
      <img
        v-if="image"
        :src="image"
        alt=""
        loading="lazy"
        decoding="async"
        referrerpolicy="no-referrer"
        @error="failed = true"
      />
      <span v-else class="placeholder"><AppIcon :name="meta.icon" :size="34" /></span>
    </component>

    <div class="body">
      <p class="meta">
        <span class="cat">{{ meta.label }}</span>
        <template v-if="article.source">
          <span aria-hidden="true">·</span>
          <span>{{ article.source }}</span>
        </template>
        <template v-if="date">
          <span aria-hidden="true">·</span>
          <time :datetime="article.published_at">{{ date }}</time>
        </template>
      </p>
      <h3>
        <a v-if="article.url" :href="article.url" target="_blank" rel="noopener noreferrer">
          <span>{{ article.title }}</span>
          <AppIcon name="external" :size="14" />
        </a>
        <template v-else>{{ article.title }}</template>
      </h3>
      <p v-if="article.summary" class="summary">{{ article.summary }}</p>
    </div>
  </article>
</template>

<style scoped>
.news {
  --accent: var(--mhm-slate);
  display: grid;
  grid-template-columns: 200px minmax(0, 1fr);
  gap: 20px;
  padding: 18px 0;
  border-bottom: 1px solid var(--border);
}
.news.breaking {
  --accent: var(--danger);
}
.news.research {
  --accent: var(--mhm-blue);
}

/* image à gauche (rapport 16/10), coins arrondis ; léger zoom au survol de l'article */
.thumb {
  position: relative;
  display: block;
  align-self: start;
  aspect-ratio: 16 / 10;
  overflow: hidden;
  border-radius: 10px;
  background: var(--mhm-blue-50);
}
.thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.35s ease;
}
.news:hover .thumb img {
  transform: scale(1.04);
}
/* vignette de remplacement : dégradé MHM + icône de la catégorie */
.placeholder {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  color: rgba(255, 255, 255, 0.92);
  background: linear-gradient(135deg, var(--mhm-blue), var(--mhm-slate));
}

.body {
  min-width: 0;
}
.meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin: 0 0 6px;
  font-size: 0.78rem;
  color: var(--muted);
}
.cat {
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--accent);
}
h3 {
  margin: 0;
  font-size: 1.1rem;
  line-height: 1.35;
  font-weight: 700;
  color: var(--mhm-slate-dark);
}
h3 a {
  color: inherit;
  text-decoration: none;
}
h3 a svg {
  display: inline-block;
  margin-left: 6px;
  vertical-align: -1px;
  opacity: 0;
  transition: opacity 0.15s;
}
h3 a:hover,
h3 a:focus-visible,
.news:hover h3 a {
  color: var(--mhm-blue-dark);
}
.news:hover h3 a svg,
h3 a:focus-visible svg {
  opacity: 0.8;
}
h3 a:focus-visible {
  outline: 3px solid var(--mhm-blue-100);
  outline-offset: 2px;
  border-radius: 4px;
}
.summary {
  display: -webkit-box;
  margin: 8px 0 0;
  overflow: hidden;
  font-size: 0.92rem;
  line-height: 1.55;
  color: var(--muted);
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
}

@media (max-width: 720px) {
  .news {
    grid-template-columns: 150px minmax(0, 1fr);
    gap: 14px;
  }
  h3 {
    font-size: 1rem;
  }
  .summary {
    -webkit-line-clamp: 2;
  }
}
@media (max-width: 520px) {
  .news {
    grid-template-columns: minmax(0, 1fr); /* mobile : image au-dessus du texte */
    gap: 12px;
  }
  .thumb {
    aspect-ratio: 16 / 9;
  }
}
@media (prefers-reduced-motion: reduce) {
  .thumb img {
    transition: none;
  }
  .news:hover .thumb img {
    transform: none;
  }
}
</style>
