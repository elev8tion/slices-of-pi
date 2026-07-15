<script setup lang="ts">
import { ref, nextTick } from 'vue'
import ChatMessages from './chat/ChatMessages.vue'
import ChatInput from './chat/ChatInput.vue'
import ChatHistoryDropdown from './chat/ChatHistoryDropdown.vue'
import type { ToolCallBlock } from './chat/ChatBubble.vue'

interface ChatMessage {
  role: 'user' | 'agent'
  textParts: string[]
  toolBlocks: ToolCallBlock[]
  timestamp: number
}

const props = defineProps<{ agentId: string }>()

const messages = ref<ChatMessage[]>([])
const streaming = ref(false)
const streamText = ref('')
const streamTools = ref<ToolCallBlock[]>([])
const thinking = ref(false)
const loading = ref(true)
const resumeMode = ref(true)
const currentSessionId = ref<string | undefined>(undefined)
const sessionName = ref('')
const messagesLoading = ref(false)

// ── Load initial messages ───────────────────────────────────────

async function loadMessages() {
  loading.value = true
  try {
    const res = await fetch(`/api/sessions?agent_id=${encodeURIComponent(props.agentId)}&limit=1`)
    if (res.ok) {
      const sessions = await res.json()
      if (sessions && sessions.length > 0) {
        currentSessionId.value = sessions[0].id
        sessionName.value = sessions[0].name || ''
      }
    }
  } catch {
    // No previous sessions — start fresh
  } finally {
    loading.value = false
  }
}

loadMessages()

// ── Send ────────────────────────────────────────────────────────

async function send(text: string) {
  if (!text || streaming.value) return

  messages.value.push({ role: 'user', textParts: [text], toolBlocks: [], timestamp: Date.now() })
  streaming.value = true
  thinking.value = true
  streamText.value = ''
  streamTools.value = []

  try {
    const body: Record<string, any> = { message: text }
    if (resumeMode.value && currentSessionId.value) {
      body.resume = true
      body.session_id = currentSessionId.value
    }
    if (sessionName.value) {
      body.name = sessionName.value
    }

    const res = await fetch(`/api/agents/${props.agentId}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })

    const reader = res.body?.getReader()
    if (!reader) throw new Error('No reader')

    const decoder = new TextDecoder()
    let buffer = ''
    let pendingTool: Partial<ToolCallBlock> = {}

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        try {
          const chunk = JSON.parse(line.slice(6))
          if (chunk.type === 'text_delta') {
            thinking.value = false
            streamText.value += chunk.content || ''
          } else if (chunk.type === 'tool_call') {
            thinking.value = false
            pendingTool = {
              type: 'tool_call',
              name: chunk.tool_name || '',
              input: JSON.stringify(chunk.tool_input || {}).slice(0, 200),
            }
          } else if (chunk.type === 'tool_result') {
            if (pendingTool.type) {
              streamTools.value.push({
                type: 'tool_call',
                name: pendingTool.name || chunk.tool_name || '',
                input: pendingTool.input,
                truncated: (chunk.content || '').length > 500,
                fullSize: (chunk.content || '').length,
              })
              streamTools.value.push({
                type: 'tool_result',
                name: chunk.tool_name || '',
                result: (chunk.content || '').slice(0, 500),
                truncated: (chunk.content || '').length > 500,
                fullSize: (chunk.content || '').length,
              })
              pendingTool = {}
            }
          } else if (chunk.type === 'thinking_delta' || chunk.type === 'thinking_start') {
            thinking.value = true
          } else if (chunk.type === 'text_start') {
            thinking.value = false
          }
        } catch { /* skip malformed chunks */ }
      }
    }
  } catch (e) {
    streamText.value += `\n[Error: ${e}]`
  }

  if (streamText.value || streamTools.value.length) {
    messages.value.push({
      role: 'agent',
      textParts: streamText.value ? [streamText.value] : [],
      toolBlocks: [...streamTools.value],
      timestamp: Date.now(),
    })
  }
  streamText.value = ''
  streamTools.value = []
  thinking.value = false
  streaming.value = false
}

// ── Session switching ────────────────────────────────────────────

function switchSession(sessionId: string) {
  currentSessionId.value = sessionId
  messages.value = []
  messagesLoading.value = true
  // Reload messages for this session
  fetch(`/api/sessions/${sessionId}`)
    .then(r => r.json())
    .then(data => {
      sessionName.value = data.name || ''
    })
    .catch(() => {})
    .finally(() => { messagesLoading.value = false })
}

function newSession() {
  currentSessionId.value = undefined
  sessionName.value = ''
  messages.value = []
}

function updateSessionName(name: string) {
  sessionName.value = name
}

// ── File attach ──────────────────────────────────────────────────

function attachFile(file: File) {
  messages.value.push({
    role: 'user',
    textParts: [`📎 ${file.name}`],
    toolBlocks: [],
    timestamp: Date.now(),
  })
  send(`I've attached a file: ${file.name}. Please read it from the workspace.`)
}
</script>

<template>
  <div class="flex flex-col h-full">
    <!-- Session header -->
    <div class="flex items-center justify-between px-4 pt-3 pb-1">
      <ChatHistoryDropdown
        :agent-id="agentId"
        :current-session-id="currentSessionId"
        :session-name="sessionName"
        @switch-session="switchSession"
        @new-session="newSession"
        @update:session-name="updateSessionName"
      />
    </div>

    <!-- Messages -->
    <ChatMessages
      :messages="messages"
      :streaming="streaming"
      :stream-text="streamText"
      :stream-tools="streamTools"
      :thinking="thinking"
      :loading="loading || messagesLoading"
    />

    <!-- Input -->
    <ChatInput
      :disabled="streaming"
      :resume-mode="resumeMode"
      @send="send"
      @attach="attachFile"
      @update:resume-mode="resumeMode = $event"
    />
  </div>
</template>
