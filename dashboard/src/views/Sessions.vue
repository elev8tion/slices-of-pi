<script setup lang="ts">
import { onMounted, ref } from 'vue'
import NavIsland from '@/components/NavIsland.vue'
import Sidebar from '@/components/Sidebar.vue'

interface Session {
  id: string
  agent_id: string
  agent_name: string
  status: string
  turns: number
  tokens_in: number
  tokens_out: number
  model: string
  started_at: string
  ended_at?: string
  session_file?: string
}

const sessions = ref<Session[]>([])
const loading = ref(true)
const expanded = ref<string | null>(null)
const messages = ref<any[]>([])

onMounted(async () => {
  await loadSessions()
})

async function loadSessions() {
  try {
    const res = await fetch('/api/sessions')
    sessions.value = await res.json()
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

async function expandSession(id: string) {
  if (expanded.value === id) {
    expanded.value = null
    return
  }
  expanded.value = id
  try {
    const res = await fetch(`/api/sessions/${id}`)
    const data = await res.json()
    messages.value = data.messages || []
  } catch (e) {
    messages.value = []
  }
}

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}
</script>

<template>
  <NavIsland />
  <div class="dashboard">
    <Sidebar />
    <main class="main">
      <div class="dash-header">
        <div class="dash-title">
          <h1>Sessions</h1>
          <p>{{ sessions.length }} recent</p>
        </div>
      </div>

      <div v-if="loading" class="card p-8 text-center text-text-tertiary text-sm">Loading...</div>

      <div v-else-if="sessions.length === 0" class="card p-8 text-center text-text-tertiary text-sm">
        No sessions yet. Start a chat to create one.
      </div>

      <div v-else class="flex flex-col gap-2">
        <div v-for="s in sessions" :key="s.id">
          <div
            class="card p-4 flex items-center gap-4 cursor-pointer hover:border-accent/20 transition-colors"
            @click="expandSession(s.id)"
          >
            <div class="w-2 h-2 rounded-full shrink-0" :class="s.status === 'completed' ? 'bg-success' : s.status === 'error' ? 'bg-danger' : 'bg-warning'" />
            <div class="flex-1 min-w-0">
              <div class="text-sm font-semibold text-text-primary">{{ s.agent_name }}</div>
              <div class="text-[11px] text-text-tertiary">{{ s.turns }} turns · {{ s.tokens_out.toLocaleString() }} tokens · {{ s.model || 'default' }}</div>
            </div>
            <span class="text-[10px] font-semibold px-2 py-0.5 rounded-full border shrink-0"
              :class="s.status === 'completed' ? 'bg-success/10 text-success border-success/15' : 'bg-white/5 text-text-tertiary border-white/8'">
              {{ s.status }}
            </span>
            <span class="text-[11px] text-text-muted shrink-0">{{ timeAgo(s.started_at) }}</span>
          </div>

          <!-- Expanded messages -->
          <div v-if="expanded === s.id" class="ml-6 mt-1 mb-2 border-l border-white/6 pl-4">
            <div v-if="messages.length === 0" class="text-xs text-text-tertiary py-2">No messages captured</div>
            <div v-for="(msg, i) in messages" :key="i" class="py-1">
              <div class="text-[10px] text-text-muted mb-0.5">{{ msg.type }}</div>
              <div v-if="msg.type === 'message_start'" class="text-xs text-text-secondary">
                {{ msg.message?.content?.map((c: any) => c.text).join(' ') || '(empty)' }}
              </div>
              <div v-else-if="msg.type === 'text_delta'" class="text-xs text-text-secondary">
                {{ msg.content }}
              </div>
              <div v-else class="text-[10px] text-text-tertiary font-mono">
                {{ JSON.stringify(msg).slice(0, 120) }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.dashboard { display: flex; gap: 0; padding: 24px 32px 32px; margin-top: 8px; max-width: 1440px; margin-left: auto; margin-right: auto; }
.main { flex: 1; min-width: 0; }
.dash-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px; }
.dash-title h1 { font-family: 'Clash Display', sans-serif; font-size: 26px; font-weight: 600; letter-spacing: -0.03em; color: #F0F0F2; }
.dash-title p { font-size: 13px; color: rgba(255,255,255,0.3); font-weight: 500; margin-top: 2px; }
</style>
