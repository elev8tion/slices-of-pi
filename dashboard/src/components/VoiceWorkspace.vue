<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import VoiceOrb from './VoiceOrb.vue'

const props = defineProps<{
  agentId: string
  agentName: string
}>()

const isSystem = computed(() => props.agentId === '__system__')

const emit = defineEmits<{
  close: []
}>()

// ── State ─────────────────────────────────────────────────────────

const orbState = ref<'idle' | 'listening' | 'processing' | 'speaking' | 'error'>('idle')
const statusText = ref('Click the orb or press Space to start')
const transcript = ref('')
const lastResponse = ref('')
const toolCall = ref<{ name: string; input: string } | null>(null)
const errorMsg = ref('')
const isListening = ref(false)

// Speech recognition
let recognition: SpeechRecognition | null = null
let synth: SpeechSynthesis | null = null
let currentUtterance: SpeechSynthesisUtterance | null = null
let ws: WebSocket | null = null

// ── Computed ──────────────────────────────────────────────────────

const statusClass = computed(() => {
  switch (orbState.value) {
    case 'listening': return 'text-blue-400'
    case 'processing': return 'text-amber-400'
    case 'speaking': return 'text-emerald-400'
    case 'error': return 'text-red-400'
    default: return 'text-text-tertiary'
  }
})

// ── WebSocket connection ──────────────────────────────────────────

async function connectWs() {
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
  // Fetch a single-use ticket
  let ticket: string
  try {
    const res = await fetch('/api/ws/ticket', { method: 'POST' })
    if (!res.ok) throw new Error('Failed to get ticket')
    const data = await res.json()
    ticket = data.ticket
  } catch {
    return
  }
  const wsPath = isSystem.value ? '__system__' : props.agentId
  ws = new WebSocket(`${protocol}//${location.host}/ws/voice/${wsPath}?ticket=${encodeURIComponent(ticket)}`)

  ws.onopen = () => {
    console.log('[Voice] WS connected')
  }

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data)
      if (msg.type === 'pong') return
    } catch { /* ignore */ }
  }

  ws.onclose = () => {
    ws = null
    // Reconnect after 3s if still in voice mode
    setTimeout(() => {
      if (!ws) connectWs()
    }, 3000)
  }

  ws.onerror = () => { /* onclose fires */ }
}

function sendWs(msg: Record<string, any>) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(msg))
  }
}

// ── Speech Recognition ────────────────────────────────────────────

function initSpeech() {
  const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
  if (!SpeechRecognition) {
    errorMsg.value = 'Speech recognition not supported in this browser. Try Chrome or Edge.'
    orbState.value = 'error'
    return false
  }

  synth = window.speechSynthesis
  recognition = new SpeechRecognition()
  recognition.continuous = true
  recognition.interimResults = true
  recognition.lang = 'en-US'

  recognition.onresult = (event: SpeechRecognitionEvent) => {
    let finalText = ''
    let interimText = ''

    for (let i = event.resultIndex; i < event.results.length; i++) {
      const result = event.results[i]
      if (result.isFinal) {
        finalText += result[0].transcript
      } else {
        interimText += result[0].transcript
      }
    }

    if (finalText) {
      transcript.value = finalText
      // Send the transcription to pi
      sendToPi(finalText)
    }
  }

  recognition.onerror = (event: any) => {
    console.error('[Voice] Recognition error:', event.error)
    if (event.error === 'not-allowed') {
      errorMsg.value = 'Microphone access denied. Allow mic access and try again.'
      orbState.value = 'error'
      stopListening()
    } else if (event.error === 'no-speech') {
      // No speech detected, just restart silently
      if (isListening.value) {
        try { recognition?.start() } catch { /* ignore */ }
      }
    } else {
      errorMsg.value = `Speech error: ${event.error}`
      orbState.value = 'error'
      stopListening()
    }
  }

  recognition.onend = () => {
    if (isListening.value) {
      // Restart if we're still supposed to be listening
      try { recognition?.start() } catch { /* ignore */ }
    }
  }

  return true
}

// ── Send to pi ────────────────────────────────────────────────────

async function sendToPi(text: string) {
  orbState.value = 'processing'
  statusText.value = 'Thinking...'
  sendWs({ type: 'transcript', text })

  try {
    const chatUrl = isSystem.value ? '/api/system/chat' : `/api/agents/${props.agentId}/chat`
    const res = await fetch(chatUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text }),
    })

    if (!res.ok) throw new Error(`HTTP ${res.status}`)

    let responseText = ''

    if (isSystem.value) {
      // System chat returns JSON directly, not SSE
      const data = await res.json()
      responseText = data.response || data.text || JSON.stringify(data)
      lastResponse.value = responseText

      // Handle navigation actions from system voice
      if (data.navigate) {
        const { useRouter } = await import('vue-router')
        const router = useRouter()
        router.push(data.navigate)
      }

      if (responseText.trim()) {
        speakResponse(responseText.trim())
      } else {
        orbState.value = 'listening'
        statusText.value = 'Listening...'
      }
    } else {
      // Agent chat returns SSE stream
      const reader = res.body?.getReader()
      if (!reader) throw new Error('No reader')

      const decoder = new TextDecoder()
      let buffer = ''

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
              responseText += chunk.content || ''
              lastResponse.value = responseText
            } else if (chunk.type === 'tool_call') {
              toolCall.value = {
                name: chunk.tool_name || '',
                input: JSON.stringify(chunk.tool_input || {}).slice(0, 200),
              }
            } else if (chunk.type === 'turn_end') {
              if (responseText.trim()) {
                speakResponse(responseText.trim())
              } else {
                orbState.value = 'listening'
                statusText.value = 'Listening...'
              }
            }
          } catch { /* skip */ }
        }
      }
    }
  } catch (e: any) {
    errorMsg.value = `Error: ${e.message}`
    orbState.value = 'error'
    statusText.value = 'Error'
    setTimeout(() => {
      if (isListening.value) {
        orbState.value = 'listening'
        statusText.value = 'Listening...'
      } else {
        orbState.value = 'idle'
        statusText.value = 'Click the orb to start'
      }
    }, 2000)
  }
}

// ── Speech Synthesis ──────────────────────────────────────────────

function speakResponse(text: string) {
  if (!synth) return

  // Cancel any ongoing speech
  synth.cancel()
  toolCall.value = null

  orbState.value = 'speaking'
  statusText.value = 'Speaking...'

  currentUtterance = new SpeechSynthesisUtterance(text)
  currentUtterance.rate = 1.1
  currentUtterance.pitch = 1.0
  currentUtterance.volume = 1.0

  // Find a good voice
  const voices = synth.getVoices()
  const preferred = voices.find(v => v.lang.startsWith('en') && v.name.includes('Premium')) ||
                    voices.find(v => v.lang.startsWith('en') && v.name.includes('Enhanced')) ||
                    voices.find(v => v.lang.startsWith('en') && v.name.includes('Google')) ||
                    voices.find(v => v.lang.startsWith('en-US'))
  if (preferred) currentUtterance.voice = preferred

  currentUtterance.onstart = () => {
    // Already set to 'speaking'
  }

  currentUtterance.onend = () => {
    currentUtterance = null
    if (isListening.value) {
      orbState.value = 'listening'
      statusText.value = 'Listening...'
    } else {
      orbState.value = 'idle'
      statusText.value = 'Click the orb or press Space to start'
    }
  }

  currentUtterance.onerror = () => {
    currentUtterance = null
    if (isListening.value) {
      orbState.value = 'listening'
      statusText.value = 'Listening...'
    }
  }

  synth.speak(currentUtterance)
}

// ── Start / Stop listening ────────────────────────────────────────

function startListening() {
  if (!recognition && !initSpeech()) return

  errorMsg.value = ''
  isListening.value = true
  orbState.value = 'listening'
  statusText.value = 'Listening...'
  toolCall.value = null

  try {
    recognition?.start()
  } catch (e) {
    // Already started
  }

  sendWs({ type: 'status', status: 'listening' })
}

function stopListening() {
  isListening.value = false
  try { recognition?.stop() } catch { /* ignore */ }

  if (currentUtterance) {
    synth?.cancel()
    currentUtterance = null
  }

  orbState.value = 'idle'
  statusText.value = 'Click the orb or press Space to start'
  sendWs({ type: 'status', status: 'idle' })
}

function toggleListening() {
  if (isListening.value) {
    stopListening()
  } else {
    startListening()
  }
}

// ── Keyboard shortcuts ────────────────────────────────────────────

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') {
    emit('close')
  } else if (e.key === ' ' && e.target === document.body) {
    e.preventDefault()
    toggleListening()
  }
}

// ── Lifecycle ────────────────────────────────────────────────────

onMounted(() => {
  connectWs()
  document.addEventListener('keydown', onKeydown)

  // Pre-load voices
  if (synth) {
    synth.getVoices() // Trigger async load
    synth.onvoiceschanged = () => synth?.getVoices()
  }
})

onUnmounted(() => {
  stopListening()
  if (ws) { ws.close(); ws = null }
  document.removeEventListener('keydown', onKeydown)
  if (synth) synth.cancel()
})
</script>

<template>
  <div class="voice-workspace" @keydown="onKeydown">
    <!-- Background gradient -->
    <div class="voice-bg" />

    <!-- Exit button -->
    <button class="voice-exit" @click="emit('close')" title="Exit voice mode (Esc)">
      <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
      </svg>
    </button>

    <!-- Header info -->
    <div class="voice-header">
      <div class="voice-agent-name">{{ agentName }}</div>
      <div class="voice-instruction">Press Space to toggle, Esc to exit</div>
    </div>

    <!-- Orb area -->
    <div class="voice-orb-area">
      <VoiceOrb
        :state="orbState"
        :size="280"
        @toggle="toggleListening"
      />

      <!-- Status text -->
      <div class="voice-status" :class="statusClass">{{ statusText }}</div>

      <!-- Error -->
      <div v-if="errorMsg" class="voice-error">{{ errorMsg }}</div>
    </div>

    <!-- Tool call display -->
    <div v-if="toolCall" class="voice-tool-call">
      <div class="tool-call-name">🔧 {{ toolCall.name }}</div>
      <div class="tool-call-input">{{ toolCall.input }}</div>
    </div>

    <!-- Transcript area -->
    <div class="voice-transcript">
      <div v-if="transcript" class="voice-user-text">
        <span class="voice-label">You:</span> {{ transcript }}
      </div>
      <div v-if="lastResponse" class="voice-agent-text">
        <span class="voice-label">{{ agentName }}:</span> {{ lastResponse }}
      </div>
      <div v-if="!transcript && !lastResponse" class="voice-placeholder">
        Your conversation will appear here
      </div>
    </div>
  </div>
</template>

<style scoped>
.voice-workspace {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: #08080C;
  overflow: hidden;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

/* Animated background */
.voice-bg {
  position: absolute;
  inset: -50%;
  background:
    radial-gradient(ellipse at 20% 50%, rgba(99, 102, 241, 0.04) 0%, transparent 50%),
    radial-gradient(ellipse at 80% 20%, rgba(168, 85, 247, 0.03) 0%, transparent 50%),
    radial-gradient(ellipse at 50% 80%, rgba(34, 197, 94, 0.02) 0%, transparent 50%);
  animation: bg-drift 20s ease-in-out infinite alternate;
}

@keyframes bg-drift {
  0% { transform: translate(0, 0) rotate(0deg); }
  100% { transform: translate(2%, 1%) rotate(3deg); }
}

/* Exit button */
.voice-exit {
  position: absolute;
  top: 20px;
  right: 20px;
  z-index: 10;
  width: 40px;
  height: 40px;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  background: rgba(255, 255, 255, 0.03);
  color: rgba(255, 255, 255, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s ease;
}
.voice-exit:hover {
  background: rgba(255, 255, 255, 0.06);
  color: rgba(255, 255, 255, 0.7);
}

/* Header */
.voice-header {
  position: absolute;
  top: 24px;
  left: 50%;
  transform: translateX(-50%);
  text-align: center;
  z-index: 5;
}
.voice-agent-name {
  font-size: 20px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.8);
  letter-spacing: -0.02em;
}
.voice-instruction {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.2);
  margin-top: 4px;
}

/* Orb area */
.voice-orb-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 24px;
  z-index: 5;
}

.voice-status {
  font-size: 15px;
  font-weight: 500;
  letter-spacing: 0.04em;
  transition: all 0.3s ease;
}

.voice-error {
  font-size: 12px;
  color: #EF4444;
  max-width: 400px;
  text-align: center;
  padding: 8px 16px;
  background: rgba(239, 68, 68, 0.06);
  border-radius: 8px;
}

/* Tool call */
.voice-tool-call {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  margin-top: 160px;
  z-index: 5;
  text-align: center;
  max-width: 400px;
}
.tool-call-name {
  font-size: 11px;
  font-weight: 600;
  color: #F59E0B;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
.tool-call-input {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.3);
  margin-top: 4px;
  font-family: 'JetBrains Mono', Menlo, monospace;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Transcript */
.voice-transcript {
  position: absolute;
  bottom: 60px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 5;
  width: 90%;
  max-width: 600px;
  text-align: center;
}
.voice-user-text,
.voice-agent-text {
  font-size: 14px;
  line-height: 1.6;
  color: rgba(255, 255, 255, 0.7);
  margin-bottom: 8px;
}
.voice-label {
  font-weight: 600;
  color: rgba(255, 255, 255, 0.35);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.voice-placeholder {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.15);
}
</style>
