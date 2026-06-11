<script setup lang="ts">
import { onMounted, ref } from 'vue'
import NavIsland from '@/components/NavIsland.vue'
import Sidebar from '@/components/Sidebar.vue'
import ReplayTimeline from '@/components/ReplayTimeline.vue'

interface Session {
  id: string
  agent_id: string
  agent_name: string
  status: string
  turns: number
  tokens_in: number
  tokens_out: number
  model: string
  name?: string
  started_at: string
  ended_at?: string
}

const sessions = ref<Session[]>([])
const loading = ref(true)

async function fetchSessions() {
  try {
    const res = await fetch('/api/sessions')
    sessions.value = await res.json()
  } catch (e) {
    console.error('Failed to load sessions', e)
  } finally {
    loading.value = false
  }
}

onMounted(fetchSessions)
</script>

<template>
  <NavIsland />
  <div class="replay-page">
    <Sidebar />
    <main class="main">
      <div class="replay-header fade-up">
        <div class="replay-title">
          <h1>Session Replay</h1>
          <p>Timeline of all agent activity</p>
        </div>
        <button
          class="refresh-btn"
          @click="fetchSessions"
          :disabled="loading"
          title="Refresh sessions"
        >
          <svg class="w-3.5 h-3.5" :class="{ 'animate-spin': loading }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </button>
      </div>
      <div v-if="loading" class="replay-loading fade-up fade-up-d2">
        <div class="animate-pulse text-text-tertiary text-sm">Loading sessions...</div>
      </div>
      <div v-else-if="sessions.length === 0" class="replay-empty fade-up fade-up-d2">
        <div class="text-3xl mb-3 opacity-30">⟐</div>
        <div class="text-text-tertiary text-sm">No sessions yet</div>
        <div class="text-text-muted text-xs mt-1">Start a chat with an agent to create a session</div>
      </div>
      <div v-else class="replay-body fade-up fade-up-d2">
        <ReplayTimeline :sessions="sessions" :loading="loading" />
      </div>
    </main>
  </div>
</template>

<style scoped>
.replay-page {
  display: flex;
  gap: 0;
  padding: 24px 32px 32px;
  margin-top: 8px;
  max-width: 1440px;
  margin-left: auto;
  margin-right: auto;
  height: calc(100vh - 60px);
}
.main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.replay-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.replay-title h1 {
  font-family: 'Clash Display', sans-serif;
  font-size: 26px;
  font-weight: 600;
  letter-spacing: -0.03em;
  color: #E9ECE0;
}
.replay-title p {
  font-size: 13px;
  color: rgba(233,236,224,0.3);
  font-weight: 500;
  margin-top: 2px;
}
.refresh-btn {
  background: rgba(233,236,224,0.04);
  border: 1px solid rgba(233,236,224,0.08);
  border-radius: 12px;
  color: rgba(233,236,224,0.45);
  padding: 8px 10px;
  cursor: pointer;
  transition: all 0.3s ease;
}
.refresh-btn:hover {
  color: rgba(233,236,224,0.7);
  background: rgba(233,236,224,0.07);
}
.replay-body {
  flex: 1;
  min-height: 0;
  background: rgba(10,10,10,0.5);
  border: 1px solid rgba(233,236,224,0.04);
  border-radius: 16px;
  overflow: hidden;
  padding: 16px;
}
.replay-loading,
.replay-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(10,10,10,0.5);
  border: 1px solid rgba(233,236,224,0.04);
  border-radius: 16px;
}
.fade-up {
  opacity: 0;
  transform: translateY(16px);
  animation: fadeUp 0.7s cubic-bezier(0.32,0.72,0,1) forwards;
}
.fade-up-d2 { animation-delay: 0.1s; }
@keyframes fadeUp {
  to { opacity: 1; transform: translateY(0); }
}
@media (max-width: 968px) {
  .replay-page { padding: 16px; flex-direction: column; }
}
</style>
