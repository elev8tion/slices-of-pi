<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'

interface SessionSummary {
  id: string
  agent_name: string
  status: string
  turns: number
  tokens_out: number
  model: string
  name?: string
  started_at: string
}

const props = defineProps<{
  agentId: string
  currentSessionId?: string
  sessionName?: string
}>()

const emit = defineEmits<{
  'switch-session': [sessionId: string]
  'new-session': []
  'update:session-name': [name: string]
}>()

const open = ref(false)
const sessions = ref<SessionSummary[]>([])
const loading = ref(false)
const error = ref('')

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

async function fetchSessions() {
  loading.value = true
  error.value = ''
  try {
    const res = await fetch(`/api/sessions?agent_id=${encodeURIComponent(props.agentId)}&limit=20`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    sessions.value = await res.json()
  } catch (e: any) {
    error.value = e.message || 'Failed to load sessions'
  } finally {
    loading.value = false
  }
}

function toggle() {
  open.value = !open.value
  if (open.value) {
    fetchSessions()
  }
}

function selectSession(id: string) {
  emit('switch-session', id)
  open.value = false
}

function newSession() {
  emit('new-session')
  open.value = false
}

function onClickOutside(e: MouseEvent) {
  const target = e.target as HTMLElement
  if (!target.closest('[data-chat-history-dropdown]')) {
    open.value = false
  }
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') {
    open.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', onClickOutside)
  document.addEventListener('keydown', onKeydown)
})

onUnmounted(() => {
  document.removeEventListener('click', onClickOutside)
  document.removeEventListener('keydown', onKeydown)
})

const editingName = ref(false)
const nameInput = ref('')

const currentLabel = computed(() => {
  if (!props.currentSessionId) return 'New Session'
  if (props.sessionName) return props.sessionName
  const found = sessions.value.find(s => s.id === props.currentSessionId)
  if (found?.name) return found.name
  return `Session #${sessions.value.findIndex(s => s.id === props.currentSessionId) + 1 || ''}`
})

function startEditName() {
  if (!props.currentSessionId) return
  editingName.value = true
  nameInput.value = props.sessionName || ''
  setTimeout(() => {
    const el = document.getElementById('session-name-input')
    el?.focus()
    el?.select()
  }, 50)
}

function saveName() {
  editingName.value = false
  const trimmed = nameInput.value.trim()
  emit('update:session-name', trimmed)
}

function onNameKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter') {
    e.preventDefault()
    saveName()
  }
  if (e.key === 'Escape') {
    editingName.value = false
  }
}
</script>

<template>
  <div data-chat-history-dropdown class="relative inline-block">
    <!-- Trigger button -->
    <button
      class="flex items-center gap-1.5 text-[11px] font-medium px-2.5 py-1 rounded-lg transition-colors"
      :class="open
        ? 'bg-accent/15 text-accent border border-accent/20'
        : 'bg-transparent backdrop-blur-sm text-text-tertiary border border-white/10 hover:bg-white/4 hover:text-text-secondary'"
      @click="toggle"
    >
      <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <span class="truncate max-w-[100px]">{{ currentLabel }}</span>
      <svg class="w-2.5 h-2.5 transition-transform" :class="{ 'rotate-180': open }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
      </svg>
    </button>

    <!-- Dropdown (teleported to body in ChatPanel via position fixed) -->
    <div
      v-if="open"
      class="absolute left-0 top-full mt-1 z-[300] min-w-[240px] max-w-[300px] max-h-[300px] overflow-y-auto rounded-xl bg-[#141418] border border-white/8 shadow-2xl shadow-black/60"
    >
      <!-- New Session button -->
      <button
        class="w-full flex items-center gap-2 px-3 py-2.5 text-xs font-medium text-accent hover:bg-accent/10 border-b border-white/5 transition-colors sticky top-0 bg-[#141418] z-10"
        @click="newSession"
      >
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
        New Session
      </button>

      <!-- Inline session name (only when session is active) -->
      <div v-if="currentSessionId" class="px-3 py-2 border-b border-white/5">
        <div v-if="!editingName" class="flex items-center gap-1.5">
          <span class="text-xs text-text-secondary truncate flex-1">{{ props.sessionName || 'Unnamed session' }}</span>
          <button
            class="p-1 rounded hover:bg-white/6 text-text-muted hover:text-text-secondary transition-colors shrink-0"
            @click="startEditName"
            title="Rename session"
          >
            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
            </svg>
          </button>
        </div>
        <div v-else class="flex items-center gap-1.5">
          <input
            id="session-name-input"
            v-model="nameInput"
            class="input-base w-full text-xs"
            placeholder="Name this session..."
            maxlength="128"
            @keydown="onNameKeydown"
            @blur="saveName"
          />
          <button class="p-1 rounded hover:bg-white/6 text-accent transition-colors shrink-0" @click="saveName" title="Save name">
            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
            </svg>
          </button>
        </div>
      </div>

      <!-- Loading -->
      <div v-if="loading" class="flex items-center justify-center py-6">
        <div class="w-4 h-4 border-2 border-accent/30 border-t-accent rounded-full animate-spin" />
      </div>

      <!-- Error -->
      <div v-else-if="error" class="text-[11px] text-danger text-center py-4 px-3">{{ error }}</div>

      <!-- Empty -->
      <div v-else-if="sessions.length === 0" class="text-[11px] text-text-tertiary text-center py-4 px-3">
        No previous sessions
      </div>

      <!-- Session list -->
      <template v-else>
        <button
          v-for="s in sessions"
          :key="s.id"
          class="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-white/2 transition-colors border-b border-white/3 last:border-b-0"
          :class="s.id === currentSessionId ? 'bg-accent/8' : ''"
          @click="selectSession(s.id)"
        >
          <div class="w-1.5 h-1.5 rounded-full shrink-0 mt-0.5"
            :class="s.status === 'completed' ? 'bg-success' : s.status === 'error' ? 'bg-danger' : 'bg-warning'" />
          <div class="flex-1 min-w-0">
            <div class="text-xs font-medium text-text-secondary truncate">{{ s.name || `Session #${sessions.findIndex(x => x.id === s.id) + 1}` }}</div>
            <div class="flex items-center gap-2 text-[10px] text-text-muted mt-0.5">
              <span>{{ s.turns }} turns</span>
              <span>{{ timeAgo(s.started_at) }}</span>
            </div>
          </div>
          <div class="text-[9px] text-text-muted shrink-0 px-1.5 py-0.5 rounded bg-white/5">{{ s.tokens_out.toLocaleString() }} tok</div>
        </button>
      </template>
    </div>
  </div>
</template>
