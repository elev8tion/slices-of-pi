<script setup lang="ts">
import { ref, computed } from 'vue'

const props = defineProps<{
  modelValue: string
  includeAny?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const models = [
  // Anthropic
  { id: 'claude-sonnet-4-20250514', provider: 'Anthropic', label: 'Claude Sonnet 4', color: '#CC7833' },
  { id: 'claude-opus-4-20250514', provider: 'Anthropic', label: 'Claude Opus 4', color: '#CC7833' },
  { id: 'claude-haiku-3-5', provider: 'Anthropic', label: 'Claude Haiku 3.5', color: '#CC7833' },
  // OpenAI
  { id: 'gpt-4o', provider: 'OpenAI', label: 'GPT-4o', color: '#10A37F' },
  { id: 'gpt-4o-mini', provider: 'OpenAI', label: 'GPT-4o Mini', color: '#10A37F' },
  { id: 'o3', provider: 'OpenAI', label: 'o3', color: '#10A37F' },
  { id: 'o4-mini', provider: 'OpenAI', label: 'o4-mini', color: '#10A37F' },
  // DeepSeek
  { id: 'deepseek-v4-pro', provider: 'DeepSeek', label: 'DeepSeek V4 Pro', color: '#4F6BF5' },
  { id: 'deepseek-v4-flash', provider: 'DeepSeek', label: 'DeepSeek V4 Flash', color: '#4F6BF5' },
  // Google
  { id: 'gemini-2.5-pro', provider: 'Google', label: 'Gemini 2.5 Pro', color: '#4285F4' },
  { id: 'gemini-2.5-flash', provider: 'Google', label: 'Gemini 2.5 Flash', color: '#4285F4' },
  // Meta
  { id: 'llama-4', provider: 'Meta', label: 'Llama 4', color: '#0866FF' },
  // Open source
  { id: 'qwen-2.5-72b', provider: 'Open Source', label: 'Qwen 2.5 72B', color: '#9747FF' },
  { id: 'deepseek-v3', provider: 'Open Source', label: 'DeepSeek V3', color: '#9747FF' },
]

const providers = [...new Set(models.map(m => m.provider))]

const selectedProvider = ref<string | null>(null)

const filteredModels = computed(() => {
  if (!selectedProvider.value) return models
  return models.filter(m => m.provider === selectedProvider.value)
})

const selectedModel = computed(() => models.find(m => m.id === props.modelValue))

function select(modelId: string) {
  emit('update:modelValue', modelId)
}
</script>

<template>
  <div class="model-selector">
    <!-- Quick provider pills -->
    <div class="flex flex-wrap gap-1.5 mb-2">
      <button
        v-for="p in providers"
        :key="p"
        class="text-[10px] px-2.5 py-1 rounded-full border transition-colors"
        :class="selectedProvider === p
          ? 'bg-accent/15 border-accent/30 text-accent'
          : 'border-white/8 text-text-tertiary hover:text-text-secondary hover:border-white/16'"
        @click="selectedProvider = selectedProvider === p ? null : p"
      >{{ p }}</button>
      <button
        v-if="selectedProvider"
        class="text-[10px] px-2 py-1 rounded-full text-text-tertiary hover:text-text-secondary transition-colors"
        @click="selectedProvider = null"
      >✕</button>
    </div>

    <!-- Model grid -->
    <div class="grid grid-cols-2 gap-1.5 max-h-40 overflow-y-auto">
      <button
        v-for="m in filteredModels"
        :key="m.id"
        class="flex items-center gap-2 px-3 py-2 rounded-lg border text-left transition-all"
        :class="modelValue === m.id
          ? 'border-accent/40 bg-accent/10'
          : 'border-white/6 bg-white/1 backdrop-blur-sm hover:border-white/12 hover:bg-white/3'"
        @click="select(m.id)"
      >
        <div
          class="w-2 h-2 rounded-full shrink-0"
          :style="{ background: m.color }"
        />
        <div class="min-w-0">
          <div class="text-[11px] font-medium text-text-primary truncate">{{ m.label }}</div>
          <div class="text-[9px] text-text-tertiary">{{ m.provider }}</div>
        </div>
      </button>
    </div>

    <!-- Custom input -->
    <div v-if="modelValue && !selectedModel" class="mt-2 px-3 py-1.5 rounded-lg bg-warning/8 border border-warning/20 text-[10px] text-warning">
      Custom model: <strong>{{ modelValue }}</strong>
    </div>
  </div>
</template>
