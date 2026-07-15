import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { toastBus } from '@/main'
import { useNotificationStore } from '@/stores/notifications'

export interface Agent {
  id: string
  name: string
  persona?: string
  status: 'created' | 'running' | 'idle' | 'busy' | 'stopped' | 'error'
  model: string
  tokens_used: number
  session_count: number
  last_active?: string
  created_at: string
}

export interface Activity {
  id: number
  agent_id: string
  agent_name?: string
  event_type: string
  event_data?: string
  created_at: string
}

export interface Session {
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
}

const PULSE_BUCKETS = 12
const FLASH_TTL_MS = 2500

export const useAppStore = defineStore('app', () => {
  const agents = ref<Agent[]>([])
  const activities = ref<Activity[]>([])
  const connected = ref(false)
  const sidebarCollapsed = ref(false)
  const ws = ref<WebSocket | null>(null)

  /** Per-agent activity intensity bars (0–1), length PULSE_BUCKETS — real data, not random */
  const activityPulse = ref<Record<string, number[]>>({})
  /** Brief flash after status change: agentId → 'busy' | 'error' */
  const statusFlash = ref<Record<string, 'busy' | 'error' | null>>({})
  const flashTimers: Record<string, ReturnType<typeof setTimeout>> = {}

  /** Command palette / cross-view flags */
  const commandOpenAgentId = ref<string | null>(null)
  const requestCreateAgent = ref(false)
  const commandOpenTab = ref<string | null>(null)

  const onlineAgents = computed(() => agents.value.filter(a => a.status === 'idle' || a.status === 'busy').length)
  const busyAgents = computed(() => agents.value.filter(a => a.status === 'busy').length)
  const errorAgents = computed(() => agents.value.filter(a => a.status === 'error').length)

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  function emptyPulse(): number[] {
    return Array.from({ length: PULSE_BUCKETS }, () => 0)
  }

  function ensurePulse(agentId: string): number[] {
    if (!activityPulse.value[agentId] || activityPulse.value[agentId].length !== PULSE_BUCKETS) {
      activityPulse.value[agentId] = emptyPulse()
    }
    return activityPulse.value[agentId]
  }

  /** Rebuild pulse series from activity timestamps (last ~N events bucketed). */
  function rebuildPulseFromActivities() {
    const byAgent: Record<string, number[]> = {}
    const now = Date.now()
    const windowMs = 60 * 60 * 1000 // 1h window
    const bucketMs = windowMs / PULSE_BUCKETS

    for (const a of agents.value) {
      byAgent[a.id] = emptyPulse()
    }

    for (const act of activities.value) {
      const id = act.agent_id
      if (!id) continue
      if (!byAgent[id]) byAgent[id] = emptyPulse()
      const t = new Date(act.created_at).getTime()
      if (Number.isNaN(t)) continue
      const age = now - t
      if (age < 0 || age > windowMs) continue
      const idx = Math.min(PULSE_BUCKETS - 1, Math.floor((windowMs - age) / bucketMs))
      byAgent[id][idx] += 1
    }

    // Normalize to 0–1 per agent
    for (const id of Object.keys(byAgent)) {
      const max = Math.max(1, ...byAgent[id])
      byAgent[id] = byAgent[id].map(v => Math.min(1, v / max))
    }
    activityPulse.value = byAgent
  }

  function bumpPulse(agentId: string) {
    if (!agentId) return
    const series = [...ensurePulse(agentId)]
    // Shift left, spike latest bucket
    series.shift()
    series.push(1)
    // Decay older peaks slightly so series stays readable
    for (let i = 0; i < series.length - 1; i++) {
      series[i] = Math.max(0, series[i] * 0.92)
    }
    activityPulse.value = { ...activityPulse.value, [agentId]: series }
  }

  function setStatusFlash(agentId: string, kind: 'busy' | 'error') {
    if (flashTimers[agentId]) clearTimeout(flashTimers[agentId])
    statusFlash.value = { ...statusFlash.value, [agentId]: kind }
    flashTimers[agentId] = setTimeout(() => {
      statusFlash.value = { ...statusFlash.value, [agentId]: null }
      delete flashTimers[agentId]
    }, FLASH_TTL_MS)
  }

  function getAgentPulse(agentId: string): number[] {
    return activityPulse.value[agentId] || emptyPulse()
  }

  function openAgentFromCommand(id: string, tab?: string) {
    commandOpenAgentId.value = id
    commandOpenTab.value = tab || null
  }

  function requestNewAgent() {
    requestCreateAgent.value = true
  }

  function clearCommandOpenAgent() {
    commandOpenAgentId.value = null
    commandOpenTab.value = null
  }

  function clearRequestCreateAgent() {
    requestCreateAgent.value = false
  }

  async function fetchAgents() {
    try {
      const prev = new Map(agents.value.map(a => [a.id, a.status]))
      const res = await fetch('/api/agents')
      if (res.ok) {
        const next: Agent[] = await res.json()
        for (const a of next) {
          const old = prev.get(a.id)
          if (old && old !== a.status) {
            if (a.status === 'busy' || a.status === 'running') setStatusFlash(a.id, 'busy')
            if (a.status === 'error') setStatusFlash(a.id, 'error')
          }
        }
        agents.value = next
      }
    } catch { /* silent */ }
  }

  async function fetchAgentDetail(id: string) {
    try {
      const res = await fetch(`/api/agents/${id}`)
      if (res.ok) return await res.json()
    } catch { /* silent */ }
    return null
  }

  async function deleteAgent(id: string) {
    try {
      const res = await fetch(`/api/agents/${id}`, { method: 'DELETE' })
      if (res.ok) {
        agents.value = agents.value.filter(a => a.id !== id)
        toastBus.success('Agent deleted')
        return true
      }
    } catch { /* silent */ }
    return false
  }

  async function createAgent(config: {
    name: string
    model?: string
    tools?: string[]
    skills?: string[]
  }): Promise<Agent | null> {
    const name = (config.name || '').trim()
    if (!/^[a-zA-Z0-9_-]+$/.test(name) || name.length < 1 || name.length > 64) {
      toastBus.error('Name: letters, numbers, _ or - only (max 64)')
      return null
    }
    try {
      const res = await fetch('/api/agents', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name,
          model: config.model || '',
          tools: config.tools || ['read', 'bash', 'web_search'],
          skills: config.skills || [],
        }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        toastBus.error(err.detail || 'Failed to create agent')
        return null
      }
      const agent = await res.json()
      await fetchAgents()
      toastBus.success(`Created local agent: ${agent.name}`)
      return agent
    } catch {
      toastBus.error('Failed to create agent')
      return null
    }
  }

  async function fetchActivities() {
    try {
      const res = await fetch('/api/activities')
      if (res.ok) {
        activities.value = await res.json()
        rebuildPulseFromActivities()
      }
    } catch { /* silent */ }
  }

  function connectWebSocket() {
    if (ws.value && (ws.value.readyState === WebSocket.OPEN || ws.value.readyState === WebSocket.CONNECTING)) {
      return
    }
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
    const socket = new WebSocket(`${protocol}//${location.host}/ws/events`)
    socket.onopen = () => { connected.value = true }
    socket.onclose = () => {
      connected.value = false
      ws.value = null
      setTimeout(connectWebSocket, 3000)
    }
    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        try {
          useNotificationStore().handleWsEvent(data)
        } catch { /* store may not be ready */ }

        const agentId = data.agent_id || data.agentId || data.id
        if (agentId && typeof agentId === 'string') {
          bumpPulse(agentId)
        }

        if (data.type === 'agent_created' || data.type === 'agent_deleted' || data.type === 'agent_updated') {
          fetchAgents()
        }
        if (data.type === 'agent_status' || data.type === 'status_changed') {
          const st = data.status || data.event_data
          if (agentId && st === 'error') setStatusFlash(agentId, 'error')
          if (agentId && (st === 'busy' || st === 'running')) setStatusFlash(agentId, 'busy')
          fetchAgents()
        }
        fetchActivities()
      } catch { /* silent */ }
    }
    ws.value = socket
  }

  return {
    agents, activities, connected, sidebarCollapsed,
    onlineAgents, busyAgents, errorAgents,
    activityPulse, statusFlash,
    commandOpenAgentId, requestCreateAgent, commandOpenTab,
    fetchAgents, fetchAgentDetail, createAgent, deleteAgent,
    fetchActivities, connectWebSocket, toggleSidebar,
    getAgentPulse, bumpPulse, setStatusFlash,
    openAgentFromCommand, requestNewAgent,
    clearCommandOpenAgent, clearRequestCreateAgent,
  }
})
