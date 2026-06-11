<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { toastBus } from '@/main'

interface McpKey {
  id: string
  name: string
  value: string
  created_at: string
}

const keys = ref<McpKey[]>([])
const loading = ref(true)
const error = ref('')
const showAddForm = ref(false)
const newName = ref('')
const newValue = ref('')
const adding = ref(false)
const deleting = ref<Set<string>>(new Set())
const deletingConfirm = ref<string | null>(null)

onMounted(async () => {
  await fetchKeys()
})

async function fetchKeys() {
  loading.value = true
  error.value = ''
  try {
    const res = await fetch('/api/mcp-keys')
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    keys.value = data.keys || []
  } catch (e: any) {
    error.value = e.message || 'Failed to load MCP keys'
  } finally {
    loading.value = false
  }
}

async function addKey() {
  if (!newName.value.trim() || !newValue.value.trim()) return
  adding.value = true
  try {
    const res = await fetch('/api/mcp-keys', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: newName.value.trim(), value: newValue.value.trim() }),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Add failed' }))
      throw new Error(err.detail || 'Add failed')
    }
    const created = await res.json()
    keys.value.unshift(created)
    newName.value = ''
    newValue.value = ''
    showAddForm.value = false
    toastBus.success(`MCP key "${created.name}" added`)
  } catch (e: any) {
    toastBus.error(e.message || 'Failed to add key')
  } finally {
    adding.value = false
  }
}

async function deleteKey(id: string) {
  if (deleting.value.has(id)) return
  deleting.value = new Set(deleting.value).add(id)
  deletingConfirm.value = null
  try {
    const res = await fetch(`/api/mcp-keys/${id}`, { method: 'DELETE' })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    keys.value = keys.value.filter(k => k.id !== id)
    toastBus.success('MCP key deleted')
  } catch (e: any) {
    toastBus.error(`Delete failed: ${e.message}`)
  } finally {
    const next = new Set(deleting.value)
    next.delete(id)
    deleting.value = next
  }
}

function copyValue(name: string) {
  // Find the key and fetch its actual value
  // Since the API masks values, we can't copy from the list
  toastBus.info(`Use the API to retrieve the key value for "${name}"`)
}
</script>

<template>
  <div class="space-y-3">
    <!-- Loading -->
    <div v-if="loading && keys.length === 0" class="card p-6 text-center text-text-tertiary text-sm">
      <div class="animate-pulse">Loading MCP keys...</div>
    </div>

    <!-- Error -->
    <div v-else-if="error && keys.length === 0" class="card p-6 text-center">
      <div class="text-danger text-sm mb-2">{{ error }}</div>
      <button @click="fetchKeys" class="text-xs font-medium px-3 py-1.5 rounded-btn bg-accent/10 text-accent border border-accent/20 hover:bg-accent/20 transition-all">
        Retry
      </button>
    </div>

    <!-- Empty state -->
    <div v-else-if="keys.length === 0 && !showAddForm" class="card p-6 text-center">
      <div class="text-text-tertiary text-sm mb-3">No MCP keys configured</div>
      <button @click="showAddForm = true" class="text-xs font-medium px-4 py-2 rounded-btn bg-accent text-white hover:bg-accent-hover transition-all">
        + Add Key
      </button>
    </div>

    <!-- Key list -->
    <template v-else>
      <!-- Add button (when list exists) -->
      <div class="flex justify-end mb-1">
        <button v-if="!showAddForm" @click="showAddForm = true"
          class="text-xs font-medium px-3 py-1.5 rounded-btn bg-accent/10 text-accent border border-accent/20 hover:bg-accent/20 transition-all">
          + Add Key
        </button>
      </div>

      <!-- Add form -->
      <div v-if="showAddForm" class="card p-4">
        <div class="flex items-center gap-3">
          <input v-model="newName" placeholder="Key name (e.g. OPENAI_API_KEY)"
            class="input-base flex-1 text-xs font-mono" />
          <input v-model="newValue" type="password" placeholder="Value"
            class="input-base flex-1 text-xs font-mono" />
          <button @click="addKey" :disabled="adding || !newName.trim() || !newValue.trim()"
            class="text-xs font-medium px-4 py-2 rounded-btn bg-accent text-white hover:bg-accent-hover transition-all disabled:opacity-30 shrink-0">
            {{ adding ? 'Adding...' : 'Add' }}
          </button>
          <button @click="showAddForm = false; newName = ''; newValue = ''"
            class="text-xs px-3 py-2 rounded-btn text-text-tertiary hover:text-text-secondary transition-all">
            Cancel
          </button>
        </div>
      </div>

      <!-- Key items -->
      <div class="space-y-1">
        <div v-for="key in keys" :key="key.id"
          class="card p-3 flex items-center justify-between group hover:border-white/10 transition-all">
          <div class="flex items-center gap-3 min-w-0">
            <div class="w-7 h-7 rounded-full bg-accent/10 flex items-center justify-center text-[11px] font-bold text-accent shrink-0">K</div>
            <div class="min-w-0">
              <div class="text-sm font-medium text-text-primary truncate">{{ key.name }}</div>
              <div class="text-[11px] text-text-tertiary font-mono">••••••••</div>
            </div>
          </div>
          <div class="flex items-center gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
            <!-- Delete confirmation -->
            <template v-if="deletingConfirm === key.id">
              <span class="text-[10px] text-danger/80">Delete?</span>
              <button @click="deleteKey(key.id)" :disabled="deleting.has(key.id)"
                class="text-[10px] font-semibold px-2 py-1 rounded bg-danger text-white hover:bg-red-700 transition-all">
                {{ deleting.has(key.id) ? '...' : 'Yes' }}
              </button>
              <button @click="deletingConfirm = null"
                class="text-[10px] px-2 py-1 rounded bg-white/5 text-text-tertiary hover:text-text-secondary transition-all">No</button>
            </template>
            <button v-else @click="deletingConfirm = key.id"
              class="text-[11px] px-2 py-1 rounded text-danger/60 hover:text-danger hover:bg-danger/10 transition-all"
              title="Delete key">✕</button>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>
