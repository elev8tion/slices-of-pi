<script setup lang="ts">
import { ref, computed } from 'vue'
import ModelSelector from './ModelSelector.vue'

const emit = defineEmits<{
  close: []
  create: [config: { name: string; model: string; tools: string[]; skills: string[] }]
}>()

const show = defineModel<boolean>('show', { default: false })

const agentName = ref('')
const selectedModel = ref('')
const selectedTools = ref<string[]>(['read', 'bash', 'edit', 'write', 'web_search'])
const skillInput = ref('')
const selectedSkills = ref<string[]>([])

const allTools = ['read', 'bash', 'edit', 'write', 'web_search', 'web_scrape', 'analyze_image', 'grep', 'find', 'ls']

function toggleTool(tool: string) {
  const idx = selectedTools.value.indexOf(tool)
  if (idx >= 0) {
    selectedTools.value = selectedTools.value.filter(t => t !== tool)
  } else {
    selectedTools.value = [...selectedTools.value, tool]
  }
}

function addSkill() {
  const s = skillInput.value.trim()
  if (s && !selectedSkills.value.includes(s)) {
    selectedSkills.value = [...selectedSkills.value, s]
  }
  skillInput.value = ''
}

function removeSkill(skill: string) {
  selectedSkills.value = selectedSkills.value.filter(s => s !== skill)
}

// Model-based context window lookup
const modelContextMap: Record<string, number> = {
  'claude': 200000,
  'gpt-4': 128000,
  'gpt-3.5': 16385,
  'deepseek': 128000,
  'gemini': 1000000,
  'command': 128000,
  'llama': 128000,
  'mistral': 128000,
}

const inferredModel = computed(() => selectedModel.value.toLowerCase())

const contextWindow = computed(() => {
  for (const [key, val] of Object.entries(modelContextMap)) {
    if (inferredModel.value.includes(key)) return val
  }
  return 100000
})

const estimatedRam = computed(() => {
  const base = 128
  const perTool = 32 * selectedTools.value.length
  const perSkill = 64 * selectedSkills.value.length
  const modelFactor = Math.max(1, contextWindow.value / 100000) * 64
  return base + perTool + perSkill + modelFactor
})

const estimatedDisk = computed(() => {
  const base = 50
  const perSkill = 10 * selectedSkills.value.length
  const perTool = 5 * selectedTools.value.length
  return base + perSkill + perTool
})

function reset() {
  agentName.value = ''
  selectedModel.value = ''
  selectedTools.value = ['read', 'bash', 'edit', 'write', 'web_search']
  skillInput.value = ''
  selectedSkills.value = []
}

function handleCreate() {
  emit('create', {
    name: agentName.value.trim() || `agent-${Date.now()}`,
    model: selectedModel.value,
    tools: [...selectedTools.value],
    skills: [...selectedSkills.value],
  })
  reset()
  show.value = false
}

function handleClose() {
  reset()
  show.value = false
  emit('close')
}
</script>

<template>
  <Teleport to="body">
    <div v-if="show" class="resource-overlay" @click.self="handleClose">
      <div class="resource-panel" @click.stop>
        <!-- Header -->
        <div class="resource-header">
          <h2 class="resource-title">Estimate Resources</h2>
          <button class="resource-close" @click="handleClose">✕</button>
        </div>

        <!-- Form -->
        <div class="resource-body">
          <!-- Agent Name -->
          <div class="resource-field">
            <label class="resource-label">Agent Name</label>
            <input
              v-model="agentName"
              placeholder="e.g. my-agent"
              class="resource-input"
            />
          </div>

          <!-- Model -->
          <div class="resource-field">
            <label class="resource-label">Model</label>
            <ModelSelector v-model="selectedModel" />
          </div>

          <!-- Tools -->
          <div class="resource-field">
            <label class="resource-label">Tools <span class="text-text-tertiary font-normal">({{ selectedTools.length }} selected)</span></label>
            <div class="tools-checklist">
              <label
                v-for="tool in allTools"
                :key="tool"
                class="tool-chip"
                :class="{ selected: selectedTools.includes(tool) }"
              >
                <input
                  type="checkbox"
                  :checked="selectedTools.includes(tool)"
                  @change="toggleTool(tool)"
                />
                <span>{{ tool }}</span>
              </label>
            </div>
          </div>

          <!-- Skills -->
          <div class="resource-field">
            <label class="resource-label">Skills <span class="text-text-tertiary font-normal">({{ selectedSkills.length }})</span></label>
            <div class="skills-add-row">
              <input
                v-model="skillInput"
                @keydown.enter.prevent="addSkill"
                placeholder="skill-name"
                class="resource-input-sm"
              />
              <button v-if="skillInput.trim()" class="btn-tiny" @click="addSkill">+</button>
            </div>
            <div v-if="selectedSkills.length" class="skills-chips">
              <span v-for="skill in selectedSkills" :key="skill" class="skill-chip-badge">
                <span>{{ skill }}</span>
                <button class="skill-chip-remove" @click="removeSkill(skill)">✕</button>
              </span>
            </div>
          </div>

          <!-- Estimates -->
          <div class="estimates-grid">
            <div class="estimate-card">
              <div class="estimate-icon" style="background: rgba(157,213,34,0.12); color: #9DD522;">🧠</div>
              <div class="estimate-value">{{ estimatedRam }}<span class="estimate-unit"> MB</span></div>
              <div class="estimate-label">RAM</div>
            </div>
            <div class="estimate-card">
              <div class="estimate-icon" style="background: rgba(34,197,94,0.12); color: #22C55E;">💾</div>
              <div class="estimate-value">{{ estimatedDisk }}<span class="estimate-unit"> MB</span></div>
              <div class="estimate-label">Disk</div>
            </div>
            <div class="estimate-card">
              <div class="estimate-icon" style="background: rgba(245,158,11,0.12); color: #F59E0B;">📐</div>
              <div class="estimate-value">{{ (contextWindow / 1000).toFixed(0) }}<span class="estimate-unit">K</span></div>
              <div class="estimate-label">Context Window</div>
            </div>
          </div>
        </div>

        <!-- Footer -->
        <div class="resource-footer">
          <button class="btn-secondary" @click="handleClose">Close</button>
          <button class="btn-primary" @click="handleCreate">Create Agent</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.resource-overlay {
  position: fixed;
  inset: 0;
  z-index: 300;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0,0,0,0.7);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  animation: fadeIn 0.2s ease;
}
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
.resource-panel {
  width: 520px;
  max-height: 85vh;
  background: #0C0C10;
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 24px;
  overflow: hidden;
  box-shadow: 0 24px 80px rgba(0,0,0,0.8);
  animation: slideUp 0.3s cubic-bezier(0.32,0.72,0,1);
}
@keyframes slideUp {
  from { opacity: 0; transform: translateY(20px) scale(0.98); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}
.resource-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 24px;
  border-bottom: 1px solid rgba(255,255,255,0.05);
  background: rgba(255,255,255,0.02);
}
.resource-title {
  font-family: 'Clash Display', sans-serif;
  font-size: 17px;
  font-weight: 600;
  color: #F0F0F2;
}
.resource-close {
  width: 34px;
  height: 34px;
  border-radius: 12px;
  border: 1px solid rgba(255,255,255,0.06);
  background: rgba(255,255,255,0.03);
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(255,255,255,0.4);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.3s ease;
}
.resource-close:hover {
  background: rgba(255,255,255,0.06);
  color: rgba(255,255,255,0.7);
}
.resource-body {
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
  max-height: 55vh;
}
.resource-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.resource-label {
  font-size: 11.5px;
  font-weight: 600;
  color: rgba(255,255,255,0.5);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.resource-input {
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 10px;
  padding: 10px 12px;
  font-size: 13px;
  color: #F0F0F2;
  font-family: inherit;
  outline: none;
  transition: border-color 0.2s;
}
.resource-input:focus {
  border-color: rgba(157,213,34,0.4);
}
.resource-input-sm {
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px;
  padding: 6px 10px;
  font-size: 12px;
  color: rgba(255,255,255,0.7);
  font-family: inherit;
  outline: none;
  width: 160px;
}
.resource-input-sm:focus {
  border-color: rgba(157,213,34,0.4);
}
.tools-checklist {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.tool-chip {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 5px 10px;
  border-radius: 8px;
  border: 1px solid rgba(255,255,255,0.08);
  background: rgba(255,255,255,0.03);
  cursor: pointer;
  font-size: 11px;
  color: rgba(255,255,255,0.55);
  transition: all 0.2s;
  user-select: none;
}
.tool-chip:hover {
  border-color: rgba(157,213,34,0.3);
  background: rgba(157,213,34,0.06);
}
.tool-chip.selected {
  border-color: rgba(157,213,34,0.5);
  background: rgba(157,213,34,0.1);
  color: #9DD522;
}
.tool-chip input {
  display: none;
}
.skills-add-row {
  display: flex;
  align-items: center;
  gap: 6px;
}
.btn-tiny {
  background: rgba(157,213,34,0.15);
  border: none;
  color: #9DD522;
  font-size: 14px;
  width: 22px;
  height: 22px;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}
.btn-tiny:hover {
  background: rgba(157,213,34,0.25);
}
.skills-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 4px;
}
.skill-chip-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 9999px;
  font-size: 10px;
  font-weight: 500;
  background: rgba(157,213,34,0.1);
  border: 1px solid rgba(157,213,34,0.2);
  color: #9DD522;
}
.skill-chip-remove {
  background: none;
  border: none;
  color: rgba(255,255,255,0.3);
  cursor: pointer;
  font-size: 9px;
  padding: 0;
}
.skill-chip-remove:hover {
  color: #EF4444;
}
.estimates-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-top: 4px;
}
.estimate-card {
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.05);
  border-radius: 14px;
  padding: 16px 12px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  text-align: center;
}
.estimate-icon {
  width: 32px;
  height: 32px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
}
.estimate-value {
  font-size: 20px;
  font-weight: 700;
  color: #F0F0F2;
  font-family: 'JetBrains Mono', monospace;
}
.estimate-unit {
  font-size: 12px;
  font-weight: 500;
  color: rgba(255,255,255,0.3);
}
.estimate-label {
  font-size: 10px;
  font-weight: 600;
  color: rgba(255,255,255,0.3);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.resource-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  padding: 14px 24px;
  border-top: 1px solid rgba(255,255,255,0.05);
  background: rgba(255,255,255,0.02);
}
.btn-primary {
  background: #9DD522; color: #fff; border: none; border-radius: 12px;
  font-size: 12.5px; font-weight: 500; font-family: inherit; cursor: pointer;
  padding: 10px 20px; transition: all 0.3s ease;
  box-shadow: 0 2px 12px rgba(157,213,34,0.25);
}
.btn-primary:hover { background: #8BC01E; }
.btn-secondary {
  background: rgba(255,255,255,0.04); color: rgba(255,255,255,0.5);
  border: 1px solid rgba(255,255,255,0.08); border-radius: 12px;
  font-size: 12.5px; font-weight: 500; font-family: inherit; cursor: pointer;
  padding: 10px 20px; transition: all 0.3s ease;
}
.btn-secondary:hover { background: rgba(255,255,255,0.08); color: rgba(255,255,255,0.7); }
</style>
