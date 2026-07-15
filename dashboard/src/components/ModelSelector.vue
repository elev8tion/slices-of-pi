<script setup lang="ts">
/**
 * Model picker backed by GET /api/system/models (pi --list-models).
 * Falls back to a small static list only if the API is unreachable.
 */
import { ref, computed, onMounted } from 'vue'

const props = defineProps<{
  modelValue: string
  includeAny?: boolean
  /** Only show vision-capable models (images=yes) */
  imagesOnly?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

interface ModelItem {
  id: string
  label: string
  provider: string
  providerLabel: string
  color: string
  context?: string
  thinking?: boolean
  images?: boolean
}

const FALLBACK: ModelItem[] = [
  { id: 'claude-sonnet-4-5', provider: 'anthropic', providerLabel: 'Anthropic', label: 'Claude Sonnet 4.5', color: '#8B5CF6' },
  { id: 'gemini-2.5-flash', provider: 'google', providerLabel: 'Google', label: 'Gemini 2.5 Flash', color: '#3B82F6' },
]

const models = ref<ModelItem[]>([])
const loading = ref(true)
const error = ref('')
const selectedProvider = ref<string | null>(null)
const search = ref('')

const providers = computed(() => {
  const seen = new Map<string, string>()
  for (const m of models.value) {
    if (!seen.has(m.provider)) seen.set(m.provider, m.providerLabel)
  }
  return [...seen.entries()].map(([id, label]) => ({ id, label }))
})

const filteredModels = computed(() => {
  let list = models.value
  if (selectedProvider.value) {
    list = list.filter(m => m.provider === selectedProvider.value)
  }
  const q = search.value.trim().toLowerCase()
  if (q) {
    list = list.filter(
      m =>
        m.id.toLowerCase().includes(q) ||
        m.label.toLowerCase().includes(q) ||
        m.providerLabel.toLowerCase().includes(q),
    )
  }
  return list
})

const selectedModel = computed(() => models.value.find(m => m.id === props.modelValue))

function select(modelId: string) {
  emit('update:modelValue', modelId)
}

async function loadModels() {
  loading.value = true
  error.value = ''
  try {
    const q = props.imagesOnly ? '?images_only=true' : ''
    const res = await fetch(`/api/system/models${q}`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    if (data.error && (!data.flat || data.flat.length === 0)) {
      error.value = data.error
      models.value = FALLBACK
      return
    }
    const flat: ModelItem[] = (data.flat || []).map((m: any) => ({
      id: m.id,
      label: m.label || m.id,
      provider: m.provider,
      providerLabel: m.providerLabel || m.provider,
      color: m.color || '#6B7280',
      context: m.context,
      thinking: m.thinking,
      images: m.images,
    }))
    // Also flatten groups if flat missing
    if (!flat.length && Array.isArray(data.models)) {
      for (const g of data.models) {
        for (const m of g.models || []) {
          flat.push({
            id: m.id,
            label: m.label || m.id,
            provider: m.provider || g.provider,
            providerLabel: m.providerLabel || g.label || g.provider,
            color: m.color || g.color || '#6B7280',
            context: m.context,
            thinking: m.thinking,
            images: m.images,
          })
        }
      }
    }
    models.value = flat.length ? flat : FALLBACK
    if (!flat.length) error.value = data.error || 'No models from pi'
  } catch (e: any) {
    error.value = e.message || 'Failed to load models'
    models.value = FALLBACK
  } finally {
    loading.value = false
  }
}

onMounted(loadModels)
</script>

<template>
  <div class="model-selector">
    <div class="model-selector-meta">
      <span v-if="loading" class="meta-muted">Loading models from pi…</span>
      <span v-else class="meta-muted">{{ models.length }} models from your .pi config</span>
      <button type="button" class="meta-reload" :disabled="loading" @click="loadModels">Reload</button>
    </div>
    <p v-if="error" class="meta-warn">{{ error }} — showing fallback list</p>

    <input
      v-model="search"
      type="search"
      class="model-search"
      placeholder="Search models…"
    />

    <!-- Provider pills -->
    <div class="flex flex-wrap gap-1.5 mb-2">
      <button
        v-for="p in providers"
        :key="p.id"
        type="button"
        class="text-[10px] px-2.5 py-1 rounded-full border transition-colors"
        :class="selectedProvider === p.id
          ? 'bg-accent/15 border-accent/30 text-accent'
          : 'border-white/8 text-text-tertiary hover:text-text-secondary hover:border-white/16'"
        @click="selectedProvider = selectedProvider === p.id ? null : p.id"
      >{{ p.label }}</button>
      <button
        v-if="selectedProvider"
        type="button"
        class="text-[10px] px-2 py-1 rounded-full text-text-tertiary hover:text-text-secondary transition-colors"
        @click="selectedProvider = null"
      >✕</button>
    </div>

    <div class="grid grid-cols-2 gap-1.5 max-h-48 overflow-y-auto">
      <button
        v-for="m in filteredModels"
        :key="m.provider + '/' + m.id"
        type="button"
        class="flex items-center gap-2 px-3 py-2 rounded-lg border text-left transition-all"
        :class="modelValue === m.id
          ? 'border-accent/40 bg-accent/10'
          : 'border-white/6 bg-white/1 backdrop-blur-sm hover:border-white/12 hover:bg-white/3'"
        @click="select(m.id)"
      >
        <div class="w-2 h-2 rounded-full shrink-0" :style="{ background: m.color }" />
        <div class="min-w-0">
          <div class="text-[11px] font-medium text-text-primary truncate">{{ m.label }}</div>
          <div class="text-[9px] text-text-tertiary truncate">
            {{ m.providerLabel }}
            <span v-if="m.images"> · vision</span>
            <span v-if="m.context"> · {{ m.context }}</span>
          </div>
        </div>
      </button>
    </div>

    <div v-if="!loading && filteredModels.length === 0" class="meta-muted mt-2">
      No models match. Try clearing search/filters or run <code>pi --list-models</code>.
    </div>

    <div v-if="modelValue && !selectedModel" class="mt-2 px-3 py-1.5 rounded-lg bg-warning/8 border border-warning/20 text-[10px] text-warning">
      Custom / not in list: <strong>{{ modelValue }}</strong>
    </div>
  </div>
</template>

<style scoped>
.model-selector-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
  gap: 8px;
}
.meta-muted { font-size: 10px; color: rgba(255,255,255,0.35); }
.meta-warn { font-size: 10px; color: #F59E0B; margin-bottom: 6px; }
.meta-reload {
  font-size: 10px;
  color: #9DD522;
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 0;
}
.model-search {
  width: 100%;
  margin-bottom: 8px;
  padding: 6px 10px;
  border-radius: 8px;
  border: 1px solid rgba(255,255,255,0.1);
  background: rgba(0,0,0,0.25);
  color: #E9ECE0;
  font-size: 11px;
  outline: none;
}
.model-search:focus { border-color: rgba(157,213,34,0.35); }
code { font-size: 10px; color: rgba(211,237,47,0.8); }
</style>
