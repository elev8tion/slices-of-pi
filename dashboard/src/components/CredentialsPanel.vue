<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { toastBus } from '@/main'

const props = defineProps<{
  agentId: string
  agentStatus?: string
}>()

interface Credential {
  id: string
  agent_id: string
  name: string
  value: string
  created_at: string
  updated_at: string
}

const credentials = ref<Credential[]>([])
const loading = ref(true)
const showAddForm = ref(false)
const newName = ref('')
const newValue = ref('')
const saving = ref(false)
const revealedValues = ref<Record<string, string>>({})
const revealing = ref(false)

const BASE = (id: string) => `/api/agents/${id}/credentials`

onMounted(async () => {
  await loadCredentials()
})

async function loadCredentials() {
  loading.value = true
  try {
    const res = await fetch(BASE(props.agentId))
    if (res.ok) {
      const data = await res.json()
      credentials.value = data.credentials || []
    }
  } catch {
    // ignore
  } finally {
    loading.value = false
  }
}

async function toggleReveal() {
  if (revealing.value) {
    revealedValues.value = {}
    revealing.value = false
    return
  }
  revealing.value = true
  try {
    const res = await fetch(`${BASE(props.agentId)}/values?reveal=1`)
    if (res.ok) {
      revealedValues.value = await res.json()
    } else {
      const err = await res.json().catch(() => ({}))
      toastBus.error(err.detail || 'Failed to reveal credentials')
      revealing.value = false
    }
  } catch {
    toastBus.error('Failed to reveal credentials')
  }
}

async function saveCredential() {
  if (!newName.value.trim() || !newValue.value.trim()) return
  saving.value = true
  try {
    const res = await fetch(BASE(props.agentId), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: newName.value.trim(), value: newValue.value.trim() }),
    })
    if (res.ok) {
      newName.value = ''
      newValue.value = ''
      showAddForm.value = false
      toastBus.success('Credential saved')
      await loadCredentials()
    } else {
      const err = await res.json().catch(() => ({ detail: 'Failed' }))
      toastBus.error(err.detail || 'Failed to save credential')
    }
  } catch {
    toastBus.error('Failed to save credential')
  } finally {
    saving.value = false
  }
}

async function deleteCredential(name: string) {
  try {
    const res = await fetch(`${BASE(props.agentId)}/${encodeURIComponent(name)}`, { method: 'DELETE' })
    if (res.ok) {
      toastBus.success('Credential deleted')
      delete revealedValues.value[name]
      await loadCredentials()
    }
  } catch {
    toastBus.error('Failed to delete credential')
  }
}

const knownTypes = [
  { name: 'ANTHROPIC_API_KEY', desc: 'Anthropic Claude API key' },
  { name: 'OPENAI_API_KEY', desc: 'OpenAI API key' },
  { name: 'GOOGLE_API_KEY', desc: 'Google/Gemini API key' },
  { name: 'DEEPSEEK_API_KEY', desc: 'DeepSeek API key' },
  { name: 'GITHUB_TOKEN', desc: 'GitHub personal access token' },
  { name: 'HUGGINGFACE_TOKEN', desc: 'Hugging Face token' },
]
</script>

<template>
  <div class="credentials-panel">
    <!-- Header -->
    <div class="flex items-center justify-between mb-4">
      <div>
        <h3 class="text-sm font-semibold text-text-primary">Credentials</h3>
        <p class="text-[11px] text-text-tertiary mt-0.5">API keys stored encrypted at rest</p>
      </div>
      <div class="flex items-center gap-2">
        <button
          v-if="credentials.length > 0"
          class="text-[10px] font-medium px-2.5 py-1.5 rounded-lg border transition-colors"
          :class="revealing
            ? 'border-accent/30 text-accent bg-accent/8'
            : 'border-white/8 text-text-tertiary hover:text-text-secondary'"
          @click="toggleReveal"
        >
          {{ revealing ? 'Hide' : 'Reveal All' }}
        </button>
        <button
          v-if="!showAddForm"
          class="text-[10px] font-semibold px-2.5 py-1.5 rounded-lg border border-accent/25 text-accent hover:bg-accent/10 transition-colors"
          @click="showAddForm = true"
        >
          + Add Key
        </button>
      </div>
    </div>

    <!-- Add form -->
    <div v-if="showAddForm" class="mb-4 p-3 rounded-xl bg-transparent backdrop-blur-sm border border-white/8">
      <div class="mb-2">
        <label class="text-[10px] font-medium text-text-tertiary uppercase tracking-wider">Name</label>
        <div class="flex flex-wrap gap-1.5 mt-1 mb-1.5">
          <button
            v-for="kt in knownTypes"
            :key="kt.name"
            class="text-[10px] px-2 py-0.5 rounded-full border border-white/8 text-text-tertiary hover:border-accent/30 hover:text-accent transition-colors"
            :class="{ 'border-accent/40 text-accent bg-accent/8': newName === kt.name }"
            @click="newName = kt.name"
            :title="kt.desc"
          >{{ kt.name }}</button>
        </div>
        <input
          v-model="newName"
          class="input-base w-full text-xs font-mono"
          placeholder="e.g. ANTHROPIC_API_KEY"
        />
      </div>
      <div class="mb-3">
        <label class="text-[10px] font-medium text-text-tertiary uppercase tracking-wider">Value</label>
        <input
          v-model="newValue"
          type="password"
          class="input-base w-full text-xs font-mono mt-1"
          placeholder="sk-ant-..."
        />
      </div>
      <div class="flex gap-2">
        <button
          class="flex-1 text-[11px] font-semibold py-2 rounded-lg bg-accent text-void hover:bg-accent/90 transition-colors disabled:opacity-40"
          :disabled="saving || !newName.trim() || !newValue.trim()"
          @click="saveCredential"
        >
          {{ saving ? 'Saving...' : 'Save' }}
        </button>
        <button
          class="px-3 text-[11px] font-medium py-2 rounded-lg bg-white/4 text-text-tertiary hover:text-text-secondary transition-colors"
          @click="showAddForm = false"
        >Cancel</button>
      </div>
    </div>

    <!-- List -->
    <div v-if="loading" class="text-xs text-text-tertiary text-center py-6">Loading...</div>
    <div v-else-if="credentials.length === 0 && !showAddForm" class="text-xs text-text-tertiary text-center py-6">
      No credentials configured. Add API keys for your agents to use.
    </div>
    <div v-else class="flex flex-col gap-1.5">
      <div
        v-for="cred in credentials"
        :key="cred.id"
        class="flex items-center gap-3 px-3 py-2.5 rounded-xl bg-transparent backdrop-blur-sm border border-white/6 hover:border-white/10 transition-colors"
      >
        <div class="w-7 h-7 rounded-lg bg-accent/10 flex items-center justify-center text-[11px] font-bold text-accent shrink-0">
          {{ cred.name.slice(0, 2) }}
        </div>
        <div class="flex-1 min-w-0">
          <div class="text-xs font-medium text-text-primary truncate">{{ cred.name }}</div>
          <div class="text-[10px] text-text-tertiary font-mono">
            {{ revealedValues[cred.name] || '••••••••' }}
          </div>
        </div>
        <button
          class="text-[10px] text-danger/60 hover:text-danger px-2 py-1 rounded transition-colors"
          @click="deleteCredential(cred.name)"
        >
          Delete
        </button>
      </div>
    </div>
  </div>
</template>
