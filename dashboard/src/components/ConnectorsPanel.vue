<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { toastBus } from '@/main'

const props = defineProps<{ agentId: string }>()

interface Connector {
  id: string
  agent_id: string
  provider: string
  label: string
  auth_state: string
  container_tags: string[]
  enabled: boolean
  last_sync_at: string | null
  last_sync_status: string | null
  last_error: string | null
  created_at: string
}

interface AvailableConnector {
  provider: string
  display_name: string
  has_schedule: boolean
  schedule: string | null
}

const connectors = ref<Connector[]>([])
const available = ref<AvailableConnector[]>([])
const loading = ref(true)
const showAddModal = ref(false)
const newConnector = ref({ provider: '', label: '', token: '', container_tags: '' })

onMounted(async () => {
  await Promise.all([fetchConnectors(), fetchAvailable()])
  loading.value = false
})

async function fetchConnectors() {
  try {
    const res = await fetch(`/api/connectors?agent_id=${props.agentId}`)
    const data = await res.json()
    connectors.value = data.connectors || []
  } catch (e) {
    console.error(e)
  }
}

async function fetchAvailable() {
  try {
    const res = await fetch('/api/connectors/available')
    const data = await res.json()
    available.value = Object.values(data.connectors || {}) as AvailableConnector[]
  } catch (e) {
    console.error(e)
  }
}

async function addConnector() {
  const tags = newConnector.value.container_tags
    ? newConnector.value.container_tags.split(',').map(t => t.trim()).filter(Boolean)
    : []
  const auth_state: Record<string, string> = {}
  if (newConnector.value.token) auth_state.token = newConnector.value.token

  try {
    const res = await fetch('/api/connectors', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        agent_id: props.agentId,
        provider: newConnector.value.provider,
        label: newConnector.value.label || newConnector.value.provider,
        auth_state,
        container_tags: tags,
      }),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }))
      throw new Error(err.detail || 'Failed to add connector')
    }
    toastBus.success(`Connector added: ${newConnector.value.label}`)
    showAddModal.value = false
    newConnector.value = { provider: '', label: '', token: '', container_tags: '' }
    await fetchConnectors()
  } catch (e: any) {
    toastBus.error(e.message || 'Failed to add connector')
  }
}

async function deleteConnector(id: string, label: string) {
  try {
    const res = await fetch(`/api/connectors/${id}`, { method: 'DELETE' })
    if (!res.ok) throw new Error('Failed to delete connector')
    toastBus.success(`Connector removed: ${label}`)
    await fetchConnectors()
  } catch (e: any) {
    toastBus.error(e.message || 'Failed to delete connector')
  }
}

function getStatusColor(status: string | null): string {
  if (!status) return 'text-text-muted'
  if (status === 'success') return 'text-success'
  if (status === 'error') return 'text-error'
  if (status === 'running') return 'text-lime'
  return 'text-text-muted'
}
</script>

<template>
  <div class="flex flex-col gap-3 p-4">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <h3 class="text-[13px] font-semibold text-text-secondary">Data Connectors</h3>
      <button
        class="text-[11px] font-medium px-3 py-1.5 rounded-lg bg-lime/10 text-lime hover:bg-lime/20 transition-colors"
        @click="showAddModal = true"
      >
        + Add Connector
      </button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="text-xs text-text-tertiary py-8 text-center">Loading connectors...</div>

    <!-- Empty state -->
    <div v-else-if="connectors.length === 0" class="text-xs text-text-tertiary py-8 text-center border border-white/6 rounded-xl">
      <div class="text-2xl mb-2 opacity-30">🔌</div>
      <div class="font-medium mb-1">No connectors configured</div>
      <div class="text-[10px] text-text-muted max-w-xs mx-auto">
        Add a connector to sync external data into this agent's knowledge pool.
      </div>
    </div>

    <!-- Connector list -->
    <div v-else class="flex flex-col gap-2">
      <div
        v-for="c in connectors"
        :key="c.id"
        class="flex items-center gap-3 p-3 rounded-xl border border-white/6 bg-white/[0.02]"
      >
        <div class="w-8 h-8 rounded-lg bg-lime/10 flex items-center justify-center text-sm shrink-0">
          🔌
        </div>
        <div class="flex-1 min-w-0">
          <div class="text-xs font-semibold text-text-secondary">{{ c.label }}</div>
          <div class="text-[10px] text-text-tertiary">
            {{ c.provider }}
            <span v-if="c.container_tags?.length" class="ml-1">
              · tags: {{ (typeof c.container_tags === 'string' ? JSON.parse(c.container_tags) : c.container_tags).join(', ') }}
            </span>
          </div>
          <div class="flex items-center gap-2 mt-1">
            <span class="text-[10px]" :class="getStatusColor(c.last_sync_status)">
              {{ c.last_sync_status || 'never synced' }}
            </span>
            <span v-if="c.last_sync_at" class="text-[9px] text-text-muted">
              {{ new Date(c.last_sync_at).toLocaleString() }}
            </span>
          </div>
        </div>
        <button
          class="text-[10px] text-text-muted hover:text-error transition-colors px-2 py-1 rounded hover:bg-error/10"
          @click="deleteConnector(c.id, c.label)"
        >
          Remove
        </button>
      </div>
    </div>

    <!-- Add Connector Modal -->
    <Teleport to="body">
      <div v-if="showAddModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm" @click.self="showAddModal = false">
        <div class="w-full max-w-sm p-6 rounded-2xl border border-white/10 bg-[#121A11] shadow-2xl">
          <h3 class="text-sm font-semibold text-text-primary mb-4">Add Connector</h3>

          <div class="flex flex-col gap-3">
            <div>
              <label class="text-[10px] font-medium text-text-muted block mb-1">Provider</label>
              <select
                v-model="newConnector.provider"
                class="w-full bg-transparent backdrop-blur-sm border border-white/12 rounded-btn px-3 py-2 text-xs text-text-secondary outline-none focus:border-lime"
              >
                <option value="" disabled>Select a provider...</option>
                <option v-for="a in available" :key="a.provider" :value="a.provider">
                  {{ a.display_name }}
                </option>
              </select>
            </div>

            <div>
              <label class="text-[10px] font-medium text-text-muted block mb-1">Label</label>
              <input
                v-model="newConnector.label"
                type="text"
                class="input-base w-full text-xs"
                placeholder="My Google Drive"
              />
            </div>

            <div>
              <label class="text-[10px] font-medium text-text-muted block mb-1">API Key / Token</label>
              <input
                v-model="newConnector.token"
                type="password"
                class="input-base w-full text-xs"
                placeholder="sm_... or OAuth token"
              />
            </div>

            <div>
              <label class="text-[10px] font-medium text-text-muted block mb-1">Tags (comma-separated)</label>
              <input
                v-model="newConnector.container_tags"
                type="text"
                class="input-base w-full text-xs"
                placeholder="frontend, infra, docs"
              />
            </div>
          </div>

          <div class="flex items-center gap-2 mt-5">
            <button
              class="flex-1 text-xs font-medium py-2 rounded-lg border border-white/10 text-text-secondary hover:bg-white/5 transition-colors"
              @click="showAddModal = false"
            >Cancel</button>
            <button
              class="flex-1 text-xs font-medium py-2 rounded-lg bg-lime text-black hover:bg-lime/90 transition-colors disabled:opacity-40"
              :disabled="!newConnector.provider || !newConnector.token"
              @click="addConnector"
            >Connect</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
