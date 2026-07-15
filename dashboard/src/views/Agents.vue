<script setup lang="ts">
import { onMounted, ref, computed, watch } from 'vue'
import { useAppStore, type Agent } from '@/stores/app'
import AppShell from '@/components/AppShell.vue'
import PageHeader from '@/components/PageHeader.vue'
import AgentDetail from '@/components/AgentDetail.vue'
import ResourceModal from '@/components/ResourceModal.vue'

const store = useAppStore()
const selectedAgent = ref<Agent | null>(null)
const startTab = ref<string | undefined>(undefined)
const search = ref('')
const statusFilter = ref('')
const showCreate = ref(false)

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
  store.fetchActivities()
  store.connectWebSocket()
})

async function onCreateAgent(config: { name: string; model: string; tools: string[]; skills: string[] }) {
  const agent = await store.createAgent(config)
  if (agent) selectedAgent.value = agent
}

async function deleteAgent(id: string) {
  await store.deleteAgent(id)
}

function openDetail(agent: Agent, tab?: string) {
  selectedAgent.value = agent
  startTab.value = tab
}
function closeDetail() {
  selectedAgent.value = null
  startTab.value = undefined
}

watch(() => store.commandOpenAgentId, (id) => {
  if (!id) return
  const agent = store.agents.find(a => a.id === id)
  if (agent) openDetail(agent, store.commandOpenTab || 'chat')
  store.clearCommandOpenAgent()
})
watch(() => store.requestCreateAgent, (v) => {
  if (v) {
    showCreate.value = true
    store.clearRequestCreateAgent()
  }
})

const statusColors: Record<string, string> = {
  idle: 'bg-success/10 text-success border-success/15',
  busy: 'bg-warning/10 text-warning border-warning/15',
  running: 'bg-success/10 text-success border-success/15',
  error: 'bg-danger/10 text-danger border-danger/15',
  stopped: 'bg-gray-500/10 text-gray-400 border-gray-500/15',
  created: 'bg-white/5 text-text-tertiary border-white/8',
}

const rowGlow = (agent: Agent) => {
  const classes: string[] = []
  if (agent.status === 'busy' || agent.status === 'running') classes.push('agent-card-glow-busy')
  if (agent.status === 'error') classes.push('agent-card-glow-error')
  if (store.statusFlash[agent.id]) classes.push('agent-card-glow-flash')
  return classes
}
</script>

<template>
  <AppShell>
    <PageHeader
      title="Agents"
      :subtitle="`${store.agents.length} total · ${store.onlineAgents} online`"
    >
      <template #actions>
        <button class="btn-primary" @click="showCreate = true">
          + New agent
        </button>
      </template>
    </PageHeader>

    <!-- Filters -->
    <div class="flex items-center gap-3 mb-4 fade-up fade-up-d3">
      <input v-model="search" placeholder="Search agents..." class="input-base w-48 text-xs" />
      <select v-model="statusFilter" class="input-base text-xs text-text-tertiary">
        <option value="">All statuses</option>
        <option value="idle">Idle</option>
        <option value="busy">Busy</option>
        <option value="error">Error</option>
        <option value="stopped">Stopped</option>
      </select>
    </div>

    <!-- Agent list -->
    <div v-if="store.agents.length === 0" class="card p-8 text-center text-text-tertiary text-sm fade-up fade-up-d4">
      <p class="mb-3">No local agents yet.</p>
      <button type="button" class="btn-primary text-xs px-4 py-2" @click="showCreate = true">
        Create your first agent
      </button>
    </div>

    <div v-else class="flex flex-col gap-2 fade-up fade-up-d4">
      <div
        v-for="agent in filteredAgents"
        :key="agent.id"
        class="card p-4 flex items-center gap-4 cursor-pointer hover:border-accent/20 transition-colors"
        :class="rowGlow(agent)"
        @click="openDetail(agent)"
      >
        <div class="w-9 h-9 rounded-full flex items-center justify-center text-xs font-bold bg-accent/15 text-accent shrink-0">
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
  </AppShell>
  <AgentDetail :agent="selectedAgent" :start-tab="startTab" @close="closeDetail" />
  <ResourceModal v-model:show="showCreate" @create="onCreateAgent" />
</template>
