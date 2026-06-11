import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { toastBus } from '@/main'

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

export const useAppStore = defineStore('app', () => {
  const agents = ref<Agent[]>([])
  const activities = ref<Activity[]>([])
  const connected = ref(false)
  const sidebarCollapsed = ref(false)
  const ws = ref<WebSocket | null>(null)

  const onlineAgents = computed(() => agents.value.filter(a => a.status === 'idle' || a.status === 'busy').length)
  const busyAgents = computed(() => agents.value.filter(a => a.status === 'busy').length)
  const errorAgents = computed(() => agents.value.filter(a => a.status === 'error').length)

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  async function fetchAgents() {
    try {
      const res = await fetch('/api/agents')
      if (res.ok) agents.value = await res.json()
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
        return true
      }
    } catch { /* silent */ }
    return false
  }

  async function fetchActivities() {
    try {
      const res = await fetch('/api/activities')
      if (res.ok) activities.value = await res.json()
    } catch { /* silent */ }
  }

  function connectWebSocket() {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
    const socket = new WebSocket(`${protocol}//${location.host}/ws/events`)
    socket.onopen = () => { connected.value = true }
    socket.onclose = () => { connected.value = false; setTimeout(connectWebSocket, 3000) }
    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'agent_created' || data.type === 'agent_deleted') fetchAgents()
        fetchActivities()
      } catch { /* silent */ }
    }
    ws.value = socket
  }

  return {
    agents, activities, connected, sidebarCollapsed,
    onlineAgents, busyAgents, errorAgents,
    fetchAgents, fetchAgentDetail, deleteAgent,
    fetchActivities, connectWebSocket, toggleSidebar,
  }
})
