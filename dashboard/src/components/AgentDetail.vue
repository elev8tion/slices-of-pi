<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useAppStore, type Agent } from '@/stores/app'
import { toastBus } from '@/main'
import ChatPanel from './ChatPanel.vue'
import TerminalPanel from './TerminalPanel.vue'
import CredentialsPanel from './CredentialsPanel.vue'
import GitPanel from './GitPanel.vue'
import FileManager from './FileManager.vue'
import VoiceWorkspace from './VoiceWorkspace.vue'
import ModelSelector from './ModelSelector.vue'
import SharingPanel from './SharingPanel.vue'
import InfoPanel from './InfoPanel.vue'
import StatusIndicator from './StatusIndicator.vue'
import SlicePlaysPanel from './SlicePlaysPanel.vue'
import ConnectorsPanel from './ConnectorsPanel.vue'
import FlixzPanel from './FlixzPanel.vue'
import RuntimeBadge from './RuntimeBadge.vue'

interface Skill {
  name: string
  description: string
  location: string
}

const props = defineProps<{ agent: Agent | null; startTab?: string }>()
const emit = defineEmits<{ close: [] }>()

const store = useAppStore()

const activeTab = ref(props.startTab || 'chat')
const showVoice = ref(false)
const isTerminalFullscreen = ref(false)
const detail = ref<any>(null)
const loading = ref(false)

// Edit form fields
const editModel = ref('')
const editPersona = ref('')
const editSystemPrompt = ref('')
const editTools = ref('')
const editSkills = ref<string[]>([])
const editTags = ref<string[]>([])
const editExtensions = ref('')
const editAutoCompact = ref(false)
const editContextWindow = ref(40000)
const newTagInput = ref('')
const saving = ref(false)

// Available skills from the API
const availableSkills = ref<Skill[]>([])
const skillsLoading = ref(false)

// Available tags from the API
const availableTags = ref<{name:string,color:string,agent_count:number}[]>([])

const tabs = ['Info', 'Chat', 'Slice Plays', 'Terminal', 'Files', 'Git', 'Credentials', 'Connectors', 'Flixz', 'Sharing', 'Activity', 'Edit', 'Settings']

const initials = computed(() => props.agent?.name.slice(0, 1).toUpperCase() || '?')

function onOverlayClick(e: MouseEvent) {
  if ((e.target as HTMLElement).classList.contains('overlay')) {
    emit('close')
  }
}

function onKeydown(e: KeyboardEvent) {
  if (isTerminalFullscreen.value && e.key === 'Escape') {
    isTerminalFullscreen.value = false
    return
  }
  if (e.key === 'Escape') emit('close')
}

// Fetch full detail for the edit tab
watch(activeTab, async (tab) => {
  if (tab === 'edit' && props.agent && !detail.value) {
    await loadDetail()
  }
})

onMounted(async () => {
  if (activeTab.value === 'edit' && props.agent) {
    await loadDetail()
  }
})

async function loadDetail() {
  if (!props.agent) return
  loading.value = true
  const [d, skillsRes, tagsRes] = await Promise.all([
    store.fetchAgentDetail(props.agent.id),
    fetch('/api/skills').then(r => r.json()).catch(() => ({ skills: [] })),
    fetch('/api/tags').then(r => r.json()).catch(() => []),
  ])
  if (d) {
    detail.value = d
    editModel.value = d.model || ''
    editPersona.value = d.persona || ''
    editSystemPrompt.value = d.system_prompt || ''
    editTools.value = (d.tools || []).join(', ')
    editSkills.value = d.skills || []
    editTags.value = d.tags || []
    editExtensions.value = (d.extensions || []).join(', ')
    editAutoCompact.value = !!d.auto_compact
    editContextWindow.value = d.context_window ?? 40000
  }
  availableSkills.value = skillsRes.skills || []
  availableTags.value = tagsRes || []
  loading.value = false
}

function addTag() {
  const t = newTagInput.value.trim().toLowerCase().replace(/\s+/g, '-')
  if (t && !editTags.value.includes(t)) {
    editTags.value.push(t)
  }
  newTagInput.value = ''
}

function removeTag(tag: string) {
  editTags.value = editTags.value.filter(t => t !== tag)
}

function toggleSkill(skillName: string) {
  const idx = editSkills.value.indexOf(skillName)
  if (idx >= 0) {
    editSkills.value = editSkills.value.filter(s => s !== skillName)
  } else {
    editSkills.value = [...editSkills.value, skillName]
  }
}

function isSkillSelected(skillName: string): boolean {
  return editSkills.value.includes(skillName)
}

async function saveAgent() {
  if (!props.agent) return
  saving.value = true
  try {
    const body: Record<string, any> = {}
    if (editModel.value !== (detail.value?.model || '')) body.model = editModel.value
    if (editPersona.value !== (detail.value?.persona || '')) body.persona = editPersona.value || null
    if (editSystemPrompt.value !== (detail.value?.system_prompt || '')) body.system_prompt = editSystemPrompt.value || null

    const parsedTools = editTools.value ? editTools.value.split(',').map((s: string) => s.trim()).filter(Boolean) : []
    if (JSON.stringify(parsedTools) !== JSON.stringify(detail.value?.tools || [])) body.tools = parsedTools

    if (JSON.stringify(editSkills.value) !== JSON.stringify(detail.value?.skills || [])) body.skills = editSkills.value

    const parsedExtensions = editExtensions.value ? editExtensions.value.split(',').map((s: string) => s.trim()).filter(Boolean) : []
    if (JSON.stringify(parsedExtensions) !== JSON.stringify(detail.value?.extensions || [])) body.extensions = parsedExtensions
    if (JSON.stringify(editTags.value) !== JSON.stringify(detail.value?.tags || [])) body.tags = editTags.value

    if (editAutoCompact.value !== !!detail.value?.auto_compact) body.auto_compact = editAutoCompact.value
    const ctxWin = editContextWindow.value
    if (ctxWin !== (detail.value?.context_window ?? 40000)) body.context_window = ctxWin

    if (Object.keys(body).length === 0) {
      toastBus.info('No changes to save')
      saving.value = false
      return
    }

    const res = await fetch(`/api/agents/${props.agent.id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Update failed' }))
      throw new Error(err.detail || 'Update failed')
    }

    const updated = await res.json()
    detail.value = updated
    toastBus.success('Agent updated')
    store.fetchAgents()
  } catch (e: any) {
    toastBus.error(e.message || 'Failed to update agent')
  } finally {
    saving.value = false
  }
}

function resetForm() {
  if (!detail.value) return
  editModel.value = detail.value.model || ''
  editPersona.value = detail.value.persona || ''
  editSystemPrompt.value = detail.value.system_prompt || ''
  editTools.value = (detail.value.tools || []).join(', ')
  editSkills.value = detail.value.skills || []
  editExtensions.value = (detail.value.extensions || []).join(', ')
  editTags.value = detail.value.tags || []
  editAutoCompact.value = !!detail.value.auto_compact
  editContextWindow.value = detail.value.context_window ?? 40000
}

function onTabClick(tab: string) {
  activeTab.value = tab.toLowerCase()
}
</script>

<template>
  <Teleport to="body">
    <div
      v-if="agent"
      class="overlay"
      :class="{ open: !!agent }"
      @click="onOverlayClick"
      @keydown="onKeydown"
      tabindex="-1"
    >
      <div class="overlay-panel" @click.stop>
        <!-- Header -->
        <div class="agent-detail-header">
          <div class="w-12 h-12 rounded-full flex items-center justify-center text-xl font-bold bg-accent/15 text-[#9DD522]">
            {{ initials }}
          </div>
          <div class="flex-1">
            <div class="font-display text-[17px] font-semibold tracking-[-0.02em] flex items-center gap-2">
              {{ agent.name }}
              <StatusIndicator :status="agent.status" size="sm" show-label />
            </div>
            <div class="text-xs text-text-tertiary mt-0.5 flex gap-4 items-center">
              <span class="flex items-center gap-1.5">Model: {{ agent.model }} <RuntimeBadge runtime="pi-code" size="sm" /></span>
              <span>Sessions: {{ agent.session_count }}</span>
              <span>Tokens: {{ agent.tokens_used.toLocaleString() }}</span>
            </div>
          </div>
          <div class="flex gap-1.5">
            <button class="action-btn" title="Voice mode" @click="showVoice = true">🎤</button>
            <button class="action-btn" title="Close" @click="emit('close')">✕</button>
          </div>
        </div>
        <!-- Tabs -->
        <div class="agent-tabs">
          <button
            v-for="tab in tabs"
            :key="tab"
            class="agent-tab"
            :class="{ active: activeTab === tab.toLowerCase() }"
            @click="onTabClick(tab)"
          >
            {{ tab }}
          </button>
        </div>
        <!-- Content -->
        <div class="max-h-80 overflow-y-auto">
          <InfoPanel v-if="activeTab === 'info' && agent" :agent-id="agent.id" />
          <ChatPanel v-else-if="activeTab === 'chat' && agent" :agent-id="agent.id" />
          <SlicePlaysPanel v-else-if="activeTab === 'slice plays' && agent" :agent-id="agent.id" :agent-status="agent.status" />
          <TerminalPanel
            v-else-if="activeTab === 'terminal' && agent"
            :agent-id="agent.id"
            :show-fullscreen-toggle="true"
            :fullscreen="isTerminalFullscreen"
            @toggle-fullscreen="isTerminalFullscreen = !isTerminalFullscreen"
          />
          <FileManager v-else-if="activeTab === 'files' && agent" :agent-id="agent.id" />
          <GitPanel v-else-if="activeTab === 'git' && agent" :agent-id="agent.id" />
          <CredentialsPanel v-else-if="activeTab === 'credentials' && agent" :agent-id="agent.id" />
          <ConnectorsPanel v-else-if="activeTab === 'connectors' && agent" :agent-id="agent.id" />
          <FlixzPanel v-else-if="activeTab === 'flixz' && agent" :agent-id="agent.id" />
          <SharingPanel v-else-if="activeTab === 'sharing' && agent" :agent-id="agent.id" />
          <div v-else-if="activeTab === 'activity'" class="text-xs text-text-tertiary text-center py-8">
            Activity log for {{ agent.name }}
          </div>
          <div v-else-if="activeTab === 'edit'" class="p-6">
            <div v-if="loading" class="text-xs text-text-tertiary text-center py-8">Loading agent details...</div>
            <form v-else-if="detail" @submit.prevent="saveAgent" class="edit-form">
              <div class="edit-field">
                <label>Model</label>
                <ModelSelector v-model="editModel" />
              </div>
              <div class="edit-field">
                <label>Persona</label>
                <input v-model="editPersona" placeholder="Persona name (e.g. assistant, coder)" />
              </div>
              <div class="edit-field">
                <label>System Prompt</label>
                <textarea v-model="editSystemPrompt" rows="3" placeholder="Custom system prompt..."></textarea>
              </div>
              <div class="edit-field">
                <label>Tools <span class="text-text-tertiary font-normal">(comma-separated)</span></label>
                <input v-model="editTools" placeholder="read, bash, web_search, edit" />
              </div>
              <div class="edit-field">
                <label>
                  Skills
                  <span class="text-text-tertiary font-normal">({{ editSkills.length }} selected)</span>
                </label>
                <div v-if="availableSkills.length === 0" class="text-xs text-text-tertiary py-2">
                  No skills available. Add skills to <code class="text-accent">~/.pi/agent/skills/</code>.
                </div>
                <div v-else class="skills-grid">
                  <label
                    v-for="skill in availableSkills"
                    :key="skill.name"
                    class="skill-chip"
                    :class="{ selected: isSkillSelected(skill.name) }"
                  >
                    <input
                      type="checkbox"
                      :checked="isSkillSelected(skill.name)"
                      @change="toggleSkill(skill.name)"
                    />
                    <span class="skill-name">{{ skill.name }}</span>
                    <span v-if="skill.description" class="skill-desc">{{ skill.description }}</span>
                  </label>
                </div>
              </div>
              <!-- Tags -->
              <div class="edit-field">
                <label>Tags <span class="text-text-tertiary font-normal">({{ editTags.length }})</span></label>
                <div class="tags-input-row">
                  <div class="tags-list">
                    <span v-for="tag in editTags" :key="tag" class="tag-chip">
                      <span>#{{ tag }}</span>
                      <button class="tag-remove" @click="removeTag(tag)">✕</button>
                    </span>
                  </div>
                  <div class="tags-add-row">
                    <input v-model="newTagInput" @keydown.enter.prevent="addTag" placeholder="add-tag" class="tags-input" />
                    <button v-if="newTagInput.trim()" class="btn-tiny" @click="addTag">+</button>
                  </div>
                </div>
                <div v-if="availableTags.length > 0" class="tags-suggestions">
                  <span
                    v-for="tag in availableTags.filter(t => !editTags.includes(t.name))"
                    :key="tag.name"
                    class="tag-suggestion"
                    @click="editTags.push(tag.name)"
                  >#{{ tag.name }}</span>
                </div>
              </div>
              <div class="edit-field">
                <label>Extensions <span class="text-text-tertiary font-normal">(comma-separated)</span></label>
                <input v-model="editExtensions" placeholder="@ext/something" />
              </div>
              <div class="edit-field">
                <label>Auto Compact</label>
                <label class="toggle-row">
                  <input type="checkbox" v-model="editAutoCompact" class="toggle-checkbox" />
                  <span class="toggle-slider"></span>
                  <span class="toggle-label">{{ editAutoCompact ? 'Enabled' : 'Disabled' }}</span>
                </label>
              </div>
              <div class="edit-field">
                <label>Context Window <span class="text-text-tertiary font-normal">(tokens)</span></label>
                <input type="number" v-model.number="editContextWindow" min="1000" max="200000" step="1000" placeholder="40000" />
              </div>
              <div class="flex items-center gap-3 mt-5">
                <button type="submit" class="btn-primary" :disabled="saving">
                  {{ saving ? 'Saving...' : 'Save Changes' }}
                </button>
                <button type="button" class="btn-secondary" @click="resetForm">Reset</button>
              </div>
            </form>
          </div>
          <div v-else class="text-xs text-text-tertiary text-center py-8">
            <div class="mb-2"><strong class="text-text-secondary">Agent ID:</strong> {{ agent.id }}</div>
            <div><strong class="text-text-secondary">Created:</strong> {{ new Date(agent.created_at).toLocaleString() }}</div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
  <VoiceWorkspace v-if="showVoice && agent" :agent-id="agent.id" :agent-name="agent.name" @close="showVoice = false" />
</template>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  z-index: 200;
  display: none;
  background: rgba(0,0,0,0.7);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
}
.overlay.open {
  display: flex;
  align-items: center;
  justify-content: center;
}
.overlay-panel {
  width: 90vw;
  max-width: 700px;
  max-height: 85vh;
  background: #0C0C10;
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 24px;
  overflow: hidden;
  box-shadow: 0 24px 80px rgba(0,0,0,0.8);
  animation: slideUp 0.4s cubic-bezier(0.32,0.72,0,1);
}
@keyframes slideUp {
  from { opacity: 0; transform: translateY(20px) scale(0.98); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}
.agent-detail-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 18px 24px;
  border-bottom: 1px solid rgba(255,255,255,0.05);
  background: rgba(255,255,255,0.02);
}
.agent-tabs {
  display: flex;
  gap: 2px;
  padding: 0 24px;
  border-bottom: 1px solid rgba(255,255,255,0.04);
}
.agent-tab {
  padding: 12px 18px;
  font-size: 12.5px;
  font-weight: 500;
  color: rgba(255,255,255,0.3);
  background: none;
  border: none;
  cursor: pointer;
  position: relative;
  transition: all 0.3s cubic-bezier(0.32,0.72,0,1);
  border-bottom: 2px solid transparent;
}
.agent-tab:hover { color: rgba(255,255,255,0.5); }
.agent-tab.active {
  color: rgba(255,255,255,0.85);
  border-bottom-color: #9DD522;
}
.action-btn {
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
  transition: all 0.3s cubic-bezier(0.32,0.72,0,1);
}
.action-btn:hover {
  background: rgba(255,255,255,0.06);
  color: rgba(255,255,255,0.7);
}
.edit-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.edit-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.edit-field label {
  font-size: 11.5px;
  font-weight: 600;
  color: rgba(255,255,255,0.5);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.edit-field input,
.edit-field textarea {
  background: transparent;
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
  border: 1px solid rgba(233,236,224,0.15);
  border-radius: 10px;
  padding: 10px 12px;
  font-size: 13px;
  color: #E9ECE0;
  font-family: inherit;
  outline: none;
  transition: border-color 0.2s;
}
.edit-field input:focus,
.edit-field textarea:focus {
  border-color: #9DD522;
}
.edit-field textarea {
  resize: vertical;
  min-height: 60px;
}

.skills-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  max-height: 200px;
  overflow-y: auto;
  padding: 4px 0;
}
.skill-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 10px;
  border: 1px solid rgba(255,255,255,0.08);
  background: rgba(255,255,255,0.03);
  cursor: pointer;
  transition: all 0.2s ease;
  user-select: none;
  font-size: 12px;
}
.skill-chip:hover {
  border-color: rgba(157,213,34,0.3);
  background: rgba(157,213,34,0.06);
}
.skill-chip.selected {
  border-color: rgba(157,213,34,0.5);
  background: rgba(157,213,34,0.1);
}
.skill-chip input[type="checkbox"] {
  appearance: none;
  width: 14px;
  height: 14px;
  border: 1.5px solid rgba(255,255,255,0.2);
  border-radius: 4px;
  background: transparent;
  cursor: pointer;
  flex-shrink: 0;
  position: relative;
  transition: all 0.2s ease;
}
.skill-chip.selected input[type="checkbox"] {
  border-color: #9DD522;
  background: #9DD522;
}
.skill-chip.selected input[type="checkbox"]::after {
  content: '✓';
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 10px;
  font-weight: bold;
}
.skill-name {
  font-weight: 500;
  color: rgba(255,255,255,0.75);
  white-space: nowrap;
}
.skill-desc {
  font-size: 10px;
  color: rgba(255,255,255,0.35);
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 180px;
  white-space: nowrap;
}
/* Toggle switch */
.toggle-row {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  padding: 6px 0;
}
.toggle-checkbox {
  display: none;
}
.toggle-slider {
  position: relative;
  width: 40px;
  height: 22px;
  background: rgba(255,255,255,0.1);
  border-radius: 11px;
  transition: background 0.3s ease;
  flex-shrink: 0;
}
.toggle-slider::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: 18px;
  height: 18px;
  background: #fff;
  border-radius: 50%;
  transition: transform 0.3s cubic-bezier(0.32,0.72,0,1);
}
.toggle-checkbox:checked + .toggle-slider {
  background: #9DD522;
}
.toggle-checkbox:checked + .toggle-slider::after {
  transform: translateX(18px);
}
.toggle-label {
  font-size: 12px;
  color: rgba(255,255,255,0.5);
}

/* Tags UI */
.tags-input-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.tags-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.tag-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border-radius: 9999px;
  font-size: 11px;
  font-weight: 500;
  background: rgba(157,213,34,0.1);
  border: 1px solid rgba(157,213,34,0.2);
  color: #9DD522;
}
.tag-remove {
  background: none;
  border: none;
  color: rgba(255,255,255,0.3);
  cursor: pointer;
  font-size: 10px;
  padding: 0;
}
.tag-remove:hover {
  color: #EF4444;
}
.tags-add-row {
  display: flex;
  align-items: center;
  gap: 6px;
}
.tags-input {
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px;
  padding: 4px 8px;
  font-size: 11px;
  color: rgba(255,255,255,0.7);
  font-family: inherit;
  outline: none;
  width: 120px;
}
.tags-input:focus {
  border-color: rgba(157,213,34,0.4);
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
.tags-suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 4px;
}
.tag-suggestion {
  font-size: 10px;
  color: rgba(255,255,255,0.35);
  cursor: pointer;
  padding: 1px 6px;
  border-radius: 4px;
  transition: all 0.2s;
}
.tag-suggestion:hover {
  color: rgba(255,255,255,0.7);
  background: rgba(255,255,255,0.04);
}
@media (max-width: 768px) {
  .overlay-panel { width: 98vw; max-height: 95vh; border-radius: 20px; }
}
</style>
