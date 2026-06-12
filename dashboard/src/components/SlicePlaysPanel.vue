<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { toastBus } from '@/main'

interface SkillParam {
  type: string
  required?: boolean
  default?: any
  description?: string
}

interface Skill {
  name: string
  description: string
  location: string
  category?: string
  triggers?: string[]
  inputs?: Record<string, SkillParam>
  outputs?: Record<string, SkillParam>
}

const props = defineProps<{
  agentId: string
  agentStatus: string
}>()

const skills = ref<Skill[]>([])
const loading = ref(true)
const error = ref('')
const searchQuery = ref('')
const runningSlicePlay = ref<string | null>(null)
const configuring = ref<Skill | null>(null)
const formValues = ref<Record<string, any>>({})

onMounted(async () => {
  await fetchSkills()
})

async function fetchSkills() {
  loading.value = true
  error.value = ''
  try {
    const res = await fetch('/api/skills')
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    skills.value = (data.skills || data || []).map((s: Skill) => ({
      ...s,
      category: s.category || s.name.split('-')[0] || 'general',
    }))
  } catch (e: any) {
    error.value = e.message || 'Failed to load slice plays'
  } finally {
    loading.value = false
  }
}

const filteredSkills = computed(() => {
  if (!searchQuery.value.trim()) return skills.value
  const q = searchQuery.value.toLowerCase()
  return skills.value.filter(
    s =>
      s.name.toLowerCase().includes(q) ||
      (s.description || '').toLowerCase().includes(q) ||
      (s.triggers || []).some(t => t.toLowerCase().includes(q))
  )
})

const groupedSkills = computed(() => {
  const groups: Record<string, Skill[]> = {}
  for (const s of filteredSkills.value) {
    const cat = s.category || 'general'
    if (!groups[cat]) groups[cat] = []
    groups[cat].push(s)
  }
  return Object.entries(groups).sort(([a], [b]) => a.localeCompare(b))
})

const groupedSkillsCount = computed(() => filteredSkills.value.length)

function openConfig(skill: Skill) {
  configuring.value = skill
  formValues.value = {}
  if (skill.inputs) {
    for (const [key, param] of Object.entries(skill.inputs)) {
      formValues.value[key] = param.default ?? (param.type === 'boolean' ? false : param.type === 'number' ? 0 : '')
    }
  }
}

function closeConfig() {
  configuring.value = null
  formValues.value = {}
}

async function runSlicePlay(skill: Skill, values?: Record<string, any>) {
  if (runningSlicePlay.value) return
  runningSlicePlay.value = skill.name

  const trigger = skill.triggers?.[0] || `/${skill.name}`
  let message: string

  if (values && Object.keys(values).length > 0) {
    const params = Object.entries(values)
      .map(([k, v]) => `${k}=${v}`)
      .join(', ')
    message = `Run ${trigger} with ${params}`
  } else {
    message = trigger
  }

  toastBus.info(`Running slice play: ${skill.name}`)

  try {
    const res = await fetch(`/api/agents/${props.agentId}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }))
      throw new Error(err.detail || 'Failed to run slice play')
    }
    toastBus.success(`Slice play started: ${skill.name}`)
    closeConfig()
  } catch (e: any) {
    toastBus.error(e.message || `Failed to run ${skill.name}`)
  } finally {
    runningSlicePlay.value = null
  }
}

function getCategoryName(cat: string): string {
  return cat.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

function hasInputs(skill: Skill): boolean {
  return !!(skill.inputs && Object.keys(skill.inputs).length > 0)
}
</script>

<template>
  <div class="slice-plays-panel">
    <div v-if="agentStatus !== 'idle' && agentStatus !== 'busy' && agentStatus !== 'running'" class="slice-plays-empty">
      <div class="text-3xl mb-3 opacity-30">▶</div>
      <div class="text-sm font-medium text-text-secondary">Agent is not running</div>
      <div class="text-xs text-text-tertiary mt-1 max-w-xs mx-auto">
        Start a chat session with this agent to run slice plays.
      </div>
    </div>

    <template v-else>
      <div class="slice-plays-search-row">
        <svg class="w-3.5 h-3.5 text-text-tertiary shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        <input v-model="searchQuery" type="text" class="slice-plays-search" placeholder="Search slice plays..." />
        <span v-if="skills.length > 0" class="text-[10px] text-text-tertiary shrink-0">{{ groupedSkillsCount }} / {{ skills.length }}</span>
      </div>

      <div v-if="loading" class="slice-plays-grid">
        <div v-for="i in 4" :key="i" class="slice-plays-skeleton">
          <div class="skeleton-line skeleton-name" /><div class="skeleton-line skeleton-desc" /><div class="skeleton-line skeleton-desc short" /><div class="skeleton-line skeleton-trigger" />
        </div>
      </div>

      <div v-else-if="error" class="slice-plays-empty">
        <div class="text-2xl mb-2 opacity-30">⚠</div>
        <div class="text-sm text-text-tertiary">{{ error }}</div>
        <button class="slice-plays-retry-btn" @click="fetchSkills">Retry</button>
      </div>

      <div v-else-if="filteredSkills.length === 0" class="slice-plays-empty">
        <div class="text-2xl mb-2 opacity-30">🔍</div>
        <div class="text-sm text-text-tertiary">No slice plays match <strong>"{{ searchQuery }}"</strong></div>
      </div>

      <!-- Skills grid (no inputs = simple Run button) -->
      <div v-else class="slice-plays-scroll">
        <div v-for="[category, catSkills] in groupedSkills" :key="category" class="slice-plays-category">
          <div class="slice-plays-category-label">{{ getCategoryName(category) }}</div>
          <div class="slice-plays-grid">
            <div v-for="skill in catSkills" :key="skill.name" class="slice-plays-card">
              <div class="slice-plays-card-top">
                <div class="slice-plays-card-name">{{ skill.name }}</div>
                <div v-if="skill.description" class="slice-plays-card-desc">{{ skill.description }}</div>
                <div v-if="skill.outputs && Object.keys(skill.outputs).length > 0" class="slice-plays-outputs-hint">
                  → {{ Object.keys(skill.outputs).join(', ') }}
                </div>
              </div>
              <div class="slice-plays-card-bottom">
                <span v-if="skill.triggers?.[0]" class="slice-plays-trigger">{{ skill.triggers[0] }}</span>
                <button
                  v-if="!hasInputs(skill)"
                  class="slice-plays-run-btn"
                  :class="{ running: runningSlicePlay === skill.name }"
                  :disabled="!!runningSlicePlay"
                  @click="runSlicePlay(skill)"
                >{{ runningSlicePlay === skill.name ? 'Running…' : 'Run' }}</button>
                <button
                  v-else
                  class="slice-plays-run-btn"
                  :class="{ configure: true }"
                  @click="openConfig(skill)"
                >Configure</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- Parameter Config Modal -->
    <Teleport to="body">
      <div v-if="configuring" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm" @click.self="closeConfig">
        <div class="w-full max-w-sm p-6 rounded-2xl border border-white/10 bg-[#121A11] shadow-2xl">
          <h3 class="text-sm font-semibold text-text-primary mb-1">{{ configuring.name }}</h3>
          <p v-if="configuring.description" class="text-[11px] text-text-tertiary mb-4">{{ configuring.description }}</p>

          <div class="flex flex-col gap-3">
            <div v-for="(param, key) in configuring.inputs" :key="key">
              <label class="text-[10px] font-medium text-text-muted block mb-1">
                {{ key }}
                <span v-if="param.required" class="text-error ml-0.5">*</span>
                <span v-if="param.description" class="text-text-muted font-normal ml-1">— {{ param.description }}</span>
              </label>

              <input
                v-if="param.type === 'string' || param.type === 'text'"
                v-model="formValues[key]"
                type="text"
                class="input-base w-full text-xs"
                :placeholder="param.default ? String(param.default) : key"
              />
              <input
                v-else-if="param.type === 'number'"
                v-model.number="formValues[key]"
                type="number"
                class="input-base w-full text-xs"
                :placeholder="param.default !== undefined ? String(param.default) : '0'"
              />
              <label v-else-if="param.type === 'boolean'" class="flex items-center gap-2 text-xs text-text-secondary">
                <input v-model="formValues[key]" type="checkbox" class="accent-lime" />
                {{ param.description || key }}
              </label>
              <textarea
                v-else
                v-model="formValues[key]"
                class="input-base w-full text-xs resize-none"
                rows="2"
                :placeholder="param.default ? String(param.default) : key"
              ></textarea>
            </div>
          </div>

          <div class="flex items-center gap-2 mt-5">
            <button class="flex-1 text-xs font-medium py-2 rounded-lg border border-white/10 text-text-secondary hover:bg-white/5 transition-colors" @click="closeConfig">Cancel</button>
            <button
              class="flex-1 text-xs font-medium py-2 rounded-lg bg-lime text-black hover:bg-lime/90 transition-colors disabled:opacity-40"
              :disabled="!!runningSlicePlay"
              @click="runSlicePlay(configuring, formValues)"
            >{{ runningSlicePlay ? 'Running…' : 'Run' }}</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.slice-plays-panel { display: flex; flex-direction: column; gap: 10px; padding: 14px; min-height: 120px; }
.slice-plays-search-row { display: flex; align-items: center; gap: 8px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 8px 12px; flex-shrink: 0; }
.slice-plays-search { flex: 1; background: none; border: none; outline: none; font-size: 12px; color: rgba(255,255,255,0.6); font-family: inherit; }
.slice-plays-search::placeholder { color: rgba(255,255,255,0.2); }
.slice-plays-scroll { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 16px; max-height: 280px; }
.slice-plays-category-label { font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; color: rgba(255,255,255,0.25); margin-bottom: 6px; padding-left: 2px; }
.slice-plays-category { display: flex; flex-direction: column; }
.slice-plays-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; }
.slice-plays-card { display: flex; flex-direction: column; justify-content: space-between; gap: 8px; padding: 12px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.06); background: rgba(255,255,255,0.02); transition: all 0.25s cubic-bezier(0.32,0.72,0,1); }
.slice-plays-card:hover { border-color: rgba(157,213,34,0.2); background: rgba(157,213,34,0.04); transform: translateY(-1px); }
.slice-plays-card-top { display: flex; flex-direction: column; gap: 3px; }
.slice-plays-card-name { font-size: 12px; font-weight: 600; color: #9DD522; line-height: 1.3; }
.slice-plays-card-desc { font-size: 10.5px; color: rgba(255,255,255,0.35); line-height: 1.45; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.slice-plays-outputs-hint { font-size: 9px; color: rgba(157,213,34,0.3); font-family: 'JetBrains Mono', monospace; margin-top: 2px; }
.slice-plays-card-bottom { display: flex; align-items: center; justify-content: space-between; gap: 6px; }
.slice-plays-trigger { font-family: 'JetBrains Mono', Menlo, monospace; font-size: 9.5px; padding: 2px 6px; border-radius: 4px; background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.06); color: rgba(255,255,255,0.3); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100px; }
.slice-plays-run-btn { font-size: 10px; font-weight: 600; padding: 4px 12px; border-radius: 8px; border: none; background: rgba(157,213,34,0.12); color: #9DD522; cursor: pointer; transition: all 0.2s ease; white-space: nowrap; font-family: inherit; }
.slice-plays-run-btn:hover:not(:disabled) { background: rgba(157,213,34,0.2); }
.slice-plays-run-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.slice-plays-run-btn.running { background: rgba(34,197,94,0.12); color: #22C55E; }
.slice-plays-run-btn.configure { background: rgba(157,213,34,0.08); }
.slice-plays-empty { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 32px 16px; text-align: center; color: rgba(255,255,255,0.3); }
.slice-plays-retry-btn { margin-top: 10px; font-size: 11px; font-weight: 500; padding: 5px 14px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1); background: rgba(255,255,255,0.03); color: rgba(255,255,255,0.5); cursor: pointer; font-family: inherit; transition: all 0.2s; }
.slice-plays-retry-btn:hover { background: rgba(255,255,255,0.06); color: rgba(255,255,255,0.7); }
.slice-plays-skeleton { padding: 12px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.04); background: rgba(255,255,255,0.01); display: flex; flex-direction: column; gap: 6px; }
.skeleton-line { background: rgba(255,255,255,0.04); border-radius: 4px; animation: shimmer 1.5s ease-in-out infinite; }
.skeleton-name { height: 14px; width: 70%; }
.skeleton-desc { height: 10px; width: 100%; }
.skeleton-desc.short { width: 55%; }
.skeleton-trigger { height: 10px; width: 40%; margin-top: 4px; }
@keyframes shimmer { 0%, 100% { opacity: 0.3; } 50% { opacity: 0.6; } }
.slice-plays-scroll::-webkit-scrollbar { width: 4px; }
.slice-plays-scroll::-webkit-scrollbar-track { background: transparent; }
.slice-plays-scroll::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.06); border-radius: 2px; }
@media (max-width: 600px) { .slice-plays-grid { grid-template-columns: 1fr; } }
</style>
