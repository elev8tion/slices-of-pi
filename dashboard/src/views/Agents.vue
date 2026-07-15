<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useAppStore, type Agent } from '@/stores/app'
import NavIsland from '@/components/NavIsland.vue'
import Sidebar from '@/components/Sidebar.vue'
import AgentDetail from '@/components/AgentDetail.vue'

const store = useAppStore()
const selectedAgent = ref<Agent | null>(null)
const search = ref('')
const statusFilter = ref('')
const showCreate = ref(false)
const newName = ref('')

const filteredAgents = computed(() => {
  let list = store.agents
  if (statusFilter.value) list = list.filter(a => a.status === statusFilter.value)
  if (search.value) {
    const q = search.value.toLowerCase()
    list = list.filter(a => a.name.toLowerCase().includes(q) || a.model.toLowerCase().includes(q))
  }
  return list
})

onMounted(() => {
  store.fetchAgents()
  store.connectWebSocket()
})

async function createAgent() {
  if (!newName.value.trim()) return
  await fetch('/api/agents', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name: newName.value.trim() }),
  })
  newName.value = ''
  showCreate.value = false
  store.fetchAgents()
}

async function deleteAgent(id: string) {
  await fetch(`/api/agents/${id}`, { method: 'DELETE' })
  store.fetchAgents()
}

const statusColors: Record<string, string> = {
  idle: 'bg-success/10 text-success border-success/15',
  busy: 'bg-warning/10 text-warning border-warning/15',
  running: 'bg-success/10 text-success border-success/15',
  error: 'bg-danger/10 text-danger border-danger/15',
  stopped: 'bg-gray-500/10 text-gray-400 border-gray-500/15',
  created: 'bg-white/5 text-text-tertiary border-white/8',
}
</script>

<template>
  <NavIsland />
  <div class="dashboard">
    <Sidebar />
    <main class="main">
      <div class="dash-header">
        <div class="dash-title">
          <h1>Agents</h1>
          <p>{{ store.agents.length }} total · {{ store.onlineAgents }} online</p>
        </div>
        <button class="btn-primary" @click="showCreate = !showCreate">
          + New Agent
        </button>
      </div>

      <!-- Create form -->
      <div v-if="showCreate" class="card p-4 mb-4 flex items-center gap-3">
        <input v-model="newName" @keyup.enter="createAgent" placeholder="Agent name..."
          class="input-base flex-1 text-sm" />
        <button @click="createAgent" class="btn-primary text-xs px-4 py-2">Create</button>
        <button @click="showCreate = false" class="text-xs text-text-tertiary hover:text-text-secondary">Cancel</button>
      </div>

      <!-- Filters -->
      <div class="flex items-center gap-3 mb-4">
        <input v-model="search" placeholder="Search agents..." class="input-base w-48 text-xs" />
        <select v-model="statusFilter" class="bg-transparent backdrop-blur-sm border border-white/12 rounded-btn px-2 py-1.5 text-xs text-text-tertiary outline-none">
          <option value="">All statuses</option>
          <option value="idle">Idle</option>
          <option value="busy">Busy</option>
          <option value="error">Error</option>
          <option value="stopped">Stopped</option>
        </select>
      </div>

      <!-- Agent list -->
      <div v-if="store.agents.length === 0" class="card p-8 text-center text-text-tertiary text-sm">
        No agents yet. Create one above.
      </div>

      <div v-else class="flex flex-col gap-2">
        <div
          v-for="agent in filteredAgents"
          :key="agent.id"
          class="card p-4 flex items-center gap-4 cursor-pointer hover:border-accent/20 transition-colors"
          @click="selectedAgent = agent"
        >
          <div class="w-9 h-9 rounded-full flex items-center justify-center text-xs font-bold bg-accent/15 text-[#818CF8] shrink-0">
            {{ agent.name[0].toUpperCase() }}
          </div>
          <div class="flex-1 min-w-0">
            <div class="text-sm font-semibold text-text-primary">{{ agent.name }}</div>
            <div class="text-[11px] text-text-tertiary">{{ agent.model || 'pi default' }} · {{ agent.session_count }} sessions</div>
          </div>
          <span class="text-[10px] font-semibold px-2 py-0.5 rounded-full border shrink-0" :class="statusColors[agent.status] || statusColors.created">
            {{ agent.status }}
          </span>
          <span class="text-xs text-text-muted font-mono shrink-0">{{ agent.tokens_used.toLocaleString() }} tok</span>
          <button @click.stop="deleteAgent(agent.id)" class="text-[11px] text-text-muted hover:text-danger transition-colors shrink-0 ml-2">
            Delete
          </button>
        </div>
      </div>
    </main>
  </div>
  <AgentDetail :agent="selectedAgent" @close="selectedAgent = null" />
</template>

<style scoped>
.dashboard { display: flex; gap: 0; padding: 24px 32px 32px; margin-top: 8px; max-width: 1440px; margin-left: auto; margin-right: auto; }
.main { flex: 1; min-width: 0; }
.dash-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px; }
.dash-title h1 { font-family: 'Clash Display', sans-serif; font-size: 26px; font-weight: 600; letter-spacing: -0.03em; color: #F0F0F2; }
.dash-title p { font-size: 13px; color: rgba(255,255,255,0.3); font-weight: 500; margin-top: 2px; }

@media (max-width: 968px) { .dashboard { padding: 16px; } }
</style>
