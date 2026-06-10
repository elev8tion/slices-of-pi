<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import type { Agent } from '@/stores/app'
import ChatPanel from './ChatPanel.vue'

const props = defineProps<{ agent: Agent | null }>()
const emit = defineEmits<{ close: [] }>()

const activeTab = ref('chat')

const tabs = ['Chat', 'Activity', 'Settings']

const initials = computed(() => props.agent?.name.slice(0, 1).toUpperCase() || '?')

function onOverlayClick(e: MouseEvent) {
  if ((e.target as HTMLElement).classList.contains('overlay')) {
    emit('close')
  }
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') emit('close')
}
</script>

<template>
  <Teleport to="body">
    <div
      v-if="agent"
      class="overlay"
      :class="{ open: !!agent }"
      @click="onOverlayClick"
      @keydown="onKeydown"
      tabindex="-1"
    >
      <div class="overlay-panel" @click.stop>
        <!-- Header -->
        <div class="agent-detail-header">
          <div class="w-12 h-12 rounded-full flex items-center justify-center text-xl font-bold bg-accent/15 text-[#818CF8]">
            {{ initials }}
          </div>
          <div class="flex-1">
            <div class="font-display text-[17px] font-semibold tracking-[-0.02em] flex items-center gap-2">
              {{ agent.name }}
              <span class="text-[10px] font-semibold px-2 py-0.5 rounded-full border" :class="agent.status === 'idle' ? 'bg-success/10 text-success border-success/15' : agent.status === 'error' ? 'bg-danger/10 text-danger border-danger/15' : 'bg-white/5 text-text-tertiary border-white/8'">
                ● {{ agent.status }}
              </span>
            </div>
            <div class="text-xs text-text-tertiary mt-0.5 flex gap-4">
              <span>Model: {{ agent.model }}</span>
              <span>Sessions: {{ agent.session_count }}</span>
              <span>Tokens: {{ agent.tokens_used.toLocaleString() }}</span>
            </div>
          </div>
          <div class="flex gap-1.5">
            <button class="action-btn" title="Close" @click="emit('close')">✕</button>
          </div>
        </div>
        <!-- Tabs -->
        <div class="agent-tabs">
          <button
            v-for="tab in tabs"
            :key="tab"
            class="agent-tab"
            :class="{ active: activeTab === tab.toLowerCase() }"
            @click="activeTab = tab.toLowerCase()"
          >
            {{ tab }}
          </button>
        </div>
        <!-- Content -->
        <div class="max-h-80 overflow-y-auto">
          <ChatPanel v-if="activeTab === 'chat' && agent" :agent-id="agent.id" />
          <div v-else-if="activeTab === 'activity'" class="text-xs text-text-tertiary text-center py-8">
            Activity log for {{ agent.name }}
          </div>
          <div v-else class="text-xs text-text-tertiary text-center py-8">
            <div class="mb-2"><strong class="text-text-secondary">Agent ID:</strong> {{ agent.id }}</div>
            <div><strong class="text-text-secondary">Created:</strong> {{ new Date(agent.created_at).toLocaleString() }}</div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  z-index: 200;
  display: none;
  background: rgba(0,0,0,0.7);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
}
.overlay.open {
  display: flex;
  align-items: center;
  justify-content: center;
}
.overlay-panel {
  width: 90vw;
  max-width: 700px;
  max-height: 85vh;
  background: #0C0C10;
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 24px;
  overflow: hidden;
  box-shadow: 0 24px 80px rgba(0,0,0,0.8);
  animation: slideUp 0.4s cubic-bezier(0.32,0.72,0,1);
}
@keyframes slideUp {
  from { opacity: 0; transform: translateY(20px) scale(0.98); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}
.agent-detail-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 18px 24px;
  border-bottom: 1px solid rgba(255,255,255,0.05);
  background: rgba(255,255,255,0.02);
}
.agent-tabs {
  display: flex;
  gap: 2px;
  padding: 0 24px;
  border-bottom: 1px solid rgba(255,255,255,0.04);
}
.agent-tab {
  padding: 12px 18px;
  font-size: 12.5px;
  font-weight: 500;
  color: rgba(255,255,255,0.3);
  background: none;
  border: none;
  cursor: pointer;
  position: relative;
  transition: all 0.3s cubic-bezier(0.32,0.72,0,1);
  border-bottom: 2px solid transparent;
}
.agent-tab:hover { color: rgba(255,255,255,0.5); }
.agent-tab.active {
  color: rgba(255,255,255,0.85);
  border-bottom-color: #6366F1;
}
.action-btn {
  width: 34px;
  height: 34px;
  border-radius: 12px;
  border: 1px solid rgba(255,255,255,0.06);
  background: rgba(255,255,255,0.03);
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(255,255,255,0.4);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.32,0.72,0,1);
}
.action-btn:hover {
  background: rgba(255,255,255,0.06);
  color: rgba(255,255,255,0.7);
}
@media (max-width: 768px) {
  .overlay-panel { width: 98vw; max-height: 95vh; border-radius: 20px; }
}
</style>
