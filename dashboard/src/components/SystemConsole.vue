<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick, watch } from 'vue'

const props = defineProps<{
  initialLines?: number
}>()

const logContainer = ref<HTMLElement | null>(null)
const consoleLogs = ref<string[]>([])
const connected = ref(false)
const autoScroll = ref(true)
const lineFilter = ref('')
const fontSize = ref(12)
const userScrolledUp = ref(false)

let ws: WebSocket | null = null
let wsReconnectTimer: ReturnType<typeof setTimeout> | null = null

// ── Scroll handling ──────────────────────────────────────────────

function scrollToBottom() {
  if (!logContainer.value || !autoScroll.value) return
  nextTick(() => {
    if (logContainer.value) {
      logContainer.value.scrollTop = logContainer.value.scrollHeight
    }
  })
}

function onLogScroll() {
  if (!logContainer.value) return
  const el = logContainer.value
  const atBottom = el.scrollTop + el.clientHeight >= el.scrollHeight - 40
  userScrolledUp.value = !atBottom
  // If the user scrolls up manually, pause auto-scroll
  if (!atBottom && autoScroll.value) {
    autoScroll.value = false
  }
}

function toggleAutoScroll() {
  autoScroll.value = !autoScroll.value
  if (autoScroll.value) {
    scrollToBottom()
  }
}

// ── Filtered lines ──────────────────────────────────────────────

const filteredLogs = ref<string[]>([])

watch([consoleLogs, lineFilter], () => {
  if (!lineFilter.value) {
    filteredLogs.value = consoleLogs.value
  } else {
    const q = lineFilter.value.toLowerCase()
    filteredLogs.value = consoleLogs.value.filter(l => l.toLowerCase().includes(q))
  }
}, { immediate: true })

// ── WebSocket lifecycle ─────────────────────────────────────────

async function connectWs() {
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return

  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:'

  // Fetch a single-use ticket
  let ticket: string
  try {
    const res = await fetch('/api/ws/ticket', { method: 'POST' })
    if (!res.ok) throw new Error('Failed to get ticket')
    const data = await res.json()
    ticket = data.ticket
  } catch {
    // Retry after 3s
    wsReconnectTimer = setTimeout(connectWs, 3000)
    return
  }

  ws = new WebSocket(`${protocol}//${location.host}/ws/logs?ticket=${encodeURIComponent(ticket)}`)

  ws.onopen = () => {
    connected.value = true
  }

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data)

      if (msg.type === 'snapshot') {
        // Initial batch of recent lines
        consoleLogs.value = msg.lines || []
        scrollToBottom()
      } else if (msg.type === 'line') {
        // Single new log line
        consoleLogs.value.push(msg.text)
        // Cap at 10,000 lines to avoid memory issues
        if (consoleLogs.value.length > 10000) {
          consoleLogs.value = consoleLogs.value.slice(-5000)
        }
        if (autoScroll.value) {
          scrollToBottom()
        }
      } else if (msg.type === 'pong') {
        // Keepalive response
      }
    } catch {
      // Ignore parse errors
    }
  }

  ws.onclose = () => {
    connected.value = false
    ws = null
    // Reconnect after 3 seconds
    wsReconnectTimer = setTimeout(connectWs, 3000)
  }

  ws.onerror = () => {
    // onclose will fire after onerror and trigger reconnect
  }
}

function disconnectWs() {
  if (wsReconnectTimer) {
    clearTimeout(wsReconnectTimer)
    wsReconnectTimer = null
  }
  if (ws) {
    ws.close()
    ws = null
  }
  connected.value = false
}

// ── Controls ─────────────────────────────────────────────────────

function clearLogs() {
  consoleLogs.value = []
  filteredLogs.value = []
}

function copyLogs() {
  const text = filteredLogs.value.join('\n')
  navigator.clipboard.writeText(text).catch(() => {
    // Fallback
    const ta = document.createElement('textarea')
    ta.value = text
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
  })
}

function decreaseFont() {
  fontSize.value = Math.max(9, fontSize.value - 1)
}

function increaseFont() {
  fontSize.value = Math.min(20, fontSize.value + 1)
}

function resetFont() {
  fontSize.value = 12
}

// ── Lifecycle ────────────────────────────────────────────────────

onMounted(() => {
  connectWs()
})

onUnmounted(() => {
  disconnectWs()
})
</script>

<template>
  <div class="console">
    <!-- Toolbar -->
    <div class="console-toolbar">
      <div class="flex items-center gap-3">
        <div
          class="console-dot"
          :class="connected ? 'connected' : 'disconnected'"
        />
        <span class="console-status">{{ connected ? 'Streaming' : 'Disconnected' }}</span>
      </div>

      <div class="flex items-center gap-2">
        <!-- Filter -->
        <input
          v-model="lineFilter"
          type="text"
          class="console-filter"
          placeholder="Filter lines..."
        />

        <!-- Auto-scroll toggle -->
        <button
          class="console-btn"
          :class="{ active: autoScroll }"
          @click="toggleAutoScroll"
          title="Auto-scroll to bottom"
        >
          <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 14l-7 7m0 0l-7-7m7 7V3" />
          </svg>
        </button>

        <!-- Font size -->
        <button class="console-btn" @click="decreaseFont" title="Smaller font">T-</button>
        <button class="console-btn" @click="increaseFont" title="Larger font">T+</button>
        <button class="console-btn" @click="resetFont" title="Reset font size">{{ fontSize }}px</button>

        <div class="console-sep" />

        <!-- Clear -->
        <button class="console-btn" @click="clearLogs" title="Clear">✕</button>

        <!-- Copy -->
        <button class="console-btn" @click="copyLogs" title="Copy all">⎘</button>

        <!-- Line count -->
        <span class="console-count">{{ filteredLogs.length.toLocaleString() }} lines</span>
      </div>
    </div>

    <!-- Logs area -->
    <div
      ref="logContainer"
      class="console-logs"
      :style="{ fontSize: fontSize + 'px' }"
      @scroll="onLogScroll"
    >
      <div v-if="filteredLogs.length === 0 && consoleLogs.length === 0" class="console-empty">
        <div class="text-3xl mb-3 opacity-30">⟐</div>
        <div>Waiting for log output...</div>
        <div class="console-empty-sub">The system console will appear here once the orchestrator starts logging.</div>
      </div>
      <div v-else-if="filteredLogs.length === 0 && lineFilter" class="console-empty">
        No lines match <strong>"{{ lineFilter }}"</strong>
      </div>
      <template v-else>
        <div
          v-for="(line, i) in filteredLogs"
          :key="i"
          class="log-line"
          :class="{
            'log-error': line.includes('ERROR'),
            'log-warn': line.includes('WARNING') || line.includes('WARN'),
            'log-info': line.includes('INFO'),
          }"
        >{{ line }}</div>
      </template>
      <!-- Auto-scroll anchor -->
      <div ref="scrollAnchor" />
    </div>

    <!-- Connection indicator -->
    <div v-if="!connected" class="console-banner">
      Reconnecting...
      <button class="console-banner-btn" @click="connectWs">Retry now</button>
    </div>
  </div>
</template>

<style scoped>
.console {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #0A0A0E;
  border: 1px solid rgba(255,255,255,0.04);
  border-radius: 16px;
  overflow: hidden;
}

.console-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 14px;
  background: rgba(255,255,255,0.02);
  border-bottom: 1px solid rgba(255,255,255,0.04);
  flex-shrink: 0;
}

.console-dot {
  width: 7px;
  height: 7px;
  border-radius: 9999px;
  flex-shrink: 0;
}
.console-dot.connected {
  background: #22C55E;
  box-shadow: 0 0 6px rgba(34,197,94,0.4);
  animation: pulseDot 2s ease-in-out infinite;
}
.console-dot.disconnected {
  background: #6B7280;
}
@keyframes pulseDot {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.console-status {
  font-size: 11px;
  font-weight: 500;
  color: rgba(255,255,255,0.35);
  white-space: nowrap;
}

.console-filter {
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 8px;
  padding: 4px 10px;
  font-size: 11px;
  color: rgba(255,255,255,0.7);
  font-family: inherit;
  outline: none;
  width: 140px;
  transition: border-color 0.2s;
}
.console-filter:focus {
  border-color: rgba(157,213,34,0.4);
}
.console-filter::placeholder {
  color: rgba(255,255,255,0.2);
}

.console-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 2px;
  padding: 4px 8px;
  border-radius: 6px;
  border: none;
  background: rgba(255,255,255,0.03);
  color: rgba(255,255,255,0.4);
  font-size: 10.5px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}
.console-btn:hover {
  background: rgba(255,255,255,0.07);
  color: rgba(255,255,255,0.7);
}
.console-btn.active {
  background: rgba(157,213,34,0.12);
  color: #9DD522;
}

.console-sep {
  width: 1px;
  height: 18px;
  background: rgba(255,255,255,0.06);
}

.console-count {
  font-size: 10px;
  color: rgba(255,255,255,0.25);
  white-space: nowrap;
  margin-left: 4px;
}

.console-logs {
  flex: 1;
  overflow-y: auto;
  padding: 10px 14px;
  font-family: 'JetBrains Mono', Menlo, 'Courier New', monospace;
  line-height: 1.55;
  scroll-behavior: smooth;
}

.console-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: rgba(255,255,255,0.25);
  font-size: 13px;
}
.console-empty-sub {
  font-size: 11px;
  color: rgba(255,255,255,0.15);
  margin-top: 6px;
}

.log-line {
  padding: 1px 0;
  white-space: pre-wrap;
  word-break: break-all;
  color: rgba(255,255,255,0.5);
}
.log-info {
  color: rgba(255,255,255,0.65);
}
.log-warn {
  color: #F59E0B;
}
.log-error {
  color: #EF4444;
}
.log-line:hover {
  background: rgba(255,255,255,0.02);
}

.console-banner {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 6px 14px;
  background: rgba(245,158,11,0.08);
  border-top: 1px solid rgba(245,158,11,0.12);
  color: #F59E0B;
  font-size: 11px;
  flex-shrink: 0;
}
.console-banner-btn {
  background: rgba(245,158,11,0.12);
  border: none;
  color: #F59E0B;
  font-size: 10px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
  cursor: pointer;
}
.console-banner-btn:hover {
  background: rgba(245,158,11,0.2);
}

/* Scrollbar styling */
.console-logs::-webkit-scrollbar {
  width: 6px;
}
.console-logs::-webkit-scrollbar-track {
  background: transparent;
}
.console-logs::-webkit-scrollbar-thumb {
  background: rgba(255,255,255,0.06);
  border-radius: 3px;
}
.console-logs::-webkit-scrollbar-thumb:hover {
  background: rgba(255,255,255,0.1);
}
</style>
