<script setup>
defineProps({
  conversations: { type: Array, required: true },
  activeId: { type: String, default: null },
})

defineEmits(['new', 'select'])

function formatDate(timestamp) {
  return new Date(timestamp).toLocaleDateString('fr-FR', {
    day: 'numeric',
    month: 'short',
  })
}
</script>

<template>
  <aside class="history" aria-label="Historique des conversations">
    <div class="history-heading">
      <h2>Conversations</h2>
      <button type="button" class="new-chat" @click="$emit('new')">
        <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path fill="currentColor" d="M11 5h2v6h6v2h-6v6h-2v-6H5v-2h6V5Z"/></svg>
        New
      </button>
    </div>

    <p v-if="!conversations.length" class="empty-history">
      Your conversations appear here.
    </p>
    <nav v-else class="conversation-list" aria-label="Conversations précédentes">
      <button
        v-for="conversation in conversations"
        :key="conversation.id"
        type="button"
        class="conversation-item"
        :class="{ active: conversation.id === activeId }"
        :aria-current="conversation.id === activeId ? 'page' : undefined"
        @click="$emit('select', conversation.id)"
      >
        <span class="conversation-title">{{ conversation.title }}</span>
        <time :datetime="new Date(conversation.updatedAt).toISOString()">
          {{ formatDate(conversation.updatedAt) }}
        </time>
      </button>
    </nav>
  </aside>
</template>

<style scoped>
.history {
  flex: none;
  width: 270px;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding: 22px 14px;
  border-right: 1px solid var(--border);
  background: var(--surface);
}
.history-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 18px;
}
.history-heading h2 {
  margin: 0;
  color: var(--mhm-slate);
  font-size: 0.95rem;
}
.new-chat {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 7px 9px;
  border: 1px solid var(--mhm-blue-100);
  border-radius: 9px;
  background: var(--mhm-blue-50);
  color: var(--mhm-slate);
  font-size: 0.8rem;
  font-weight: 600;
}
.new-chat:hover {
  border-color: var(--mhm-blue);
}
.empty-history {
  margin: 0;
  color: var(--muted);
  font-size: 0.85rem;
}
.conversation-list {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 5px;
  min-height: 0;
  overflow-y: auto;
}
.conversation-item {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 11px;
  border: 1px solid transparent;
  border-radius: 10px;
  background: transparent;
  text-align: left;
}
.conversation-item:hover {
  background: var(--mhm-blue-50);
}
.conversation-item.active {
  border-color: var(--mhm-blue-100);
  background: var(--mhm-blue-50);
}
.conversation-title {
  overflow: hidden;
  color: var(--text);
  font-size: 0.86rem;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.conversation-item time {
  color: var(--muted);
  font-size: 0.72rem;
}

@media (max-width: 640px) {
  .history {
    width: 100%;
    height: 170px;
    padding: 12px 14px;
    border-right: 0;
    border-bottom: 1px solid var(--border);
  }
  .history-heading {
    margin-bottom: 8px;
  }
  .conversation-list {
    gap: 2px;
  }
  .conversation-item {
    padding: 7px 9px;
  }
}
</style>
