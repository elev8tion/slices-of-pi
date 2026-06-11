<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { Terminal } from 'xterm'
import { FitAddon } from '@xterm/addon-fit'
import { WebglAddon } from '@xterm/addon-webgl'
import { CanvasAddon } from '@xterm/addon-canvas'
import { WebLinksAddon } from '@xterm/addon-web-links'
import { toastBus } from '@/main'
import 'xterm/css/xterm.css'

const props = defineProps<{
  agentId: string
  fullscreen?: boolean
  showFullscreenToggle?: boolean
}>()

const emit = defineEmits<{
  'toggle-fullscreen': []
}>()

const terminalEl = ref<HTMLElement | null>(null)
const errorMessage = ref('')
const mode = ref('pi')
let term: Terminal | null = null
let fit: FitAddon | null = null
let webgl: WebglAddon | null = null
let canvas: CanvasAddon | null = null
let ws: WebSocket | null = null
const connectionStatus = ref<'disconnected' | 'connecting' | 'connected'>('disconnected')
const connected = computed(() => connectionStatus.value === 'connected')

onMounted(() => {
  if (!terminalEl.value) return

  term = new Terminal({
    cursorBlink: true,
    fontSize: 13,
    fontFamily: '"JetBrains Mono", Menlo, monospace',
    scrollback: 10000,
    theme: {
      background: '#0C0C10',
      foreground: '#E0E0E2',
      cursor: '#9DD522',
      selectionBackground: 'rgba(157,213,34,0.3)',
      black: '#1a1a2e',
      red: '#EF4444',
      green: '#22C55E',
      yellow: '#F59E0B',
      blue: '#9DD522',
      magenta: '#a855f7',
      cyan: '#22D3EE',
      white: '#E0E0E2',
      brightBlack: '#4a4a5e',
    },
    allowProposedApi: true,
  })

  fit = new FitAddon()
  term.loadAddon(fit)
  term.loadAddon(new WebLinksAddon())
  term.open(terminalEl.value)

  loadRenderer()

  // Fit after a frame to allow CSS layout to settle
  requestAnimationFrame(() => {
    fit?.fit()
    sendResize()
  })

  // Resize when container changes
  const resizeObserver = new ResizeObserver(() => {
    requestAnimationFrame(() => {
      fit?.fit()
      sendResize()
    })
  })
  resizeObserver.observe(terminalEl.value)

  connect()

  onUnmounted(() => {
    resizeObserver.disconnect()

    // Close WebSocket first
    if (ws) {
      try { ws.close() } catch {}
      ws = null
    }

    // Dispose addons before terminal (order matters)
    if (webgl) {
      try { webgl.dispose() } catch {}
      webgl = null
    }
    if (canvas) {
      try { canvas.dispose() } catch {}
      canvas = null
    }

    // Dispose terminal last
    if (term) {
      try { term.dispose() } catch {}
      term = null
    }
  })
})

function sendResize() {
  if (!term || !ws || ws.readyState !== WebSocket.OPEN) return
  const dims = fit?.proposeDimensions?.()
  if (dims) {
    // Send resize escape sequence: ESC[8;<rows>;<cols>t
    ws.send(`\x1b[8;${dims.rows};${dims.cols}t`)
  }
}

async function connect() {
  if (ws) return
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
  connectionStatus.value = 'connecting'
  ws = new WebSocket(`${protocol}//${location.host}/ws/terminal/${props.agentId}?ticket=${encodeURIComponent(ticket)}&mode=${mode.value}`)

  ws.onopen = () => {
    connectionStatus.value = 'connected'
    errorMessage.value = ''
    toastBus.success('Terminal connected')
    // Send initial size after connection
    requestAnimationFrame(() => {
      fit?.fit()
      sendResize()
    })
  }

  ws.onclose = (event) => {
    connectionStatus.value = 'disconnected'
    toastBus.info('Terminal disconnected')

    // Set human-readable error message based on close code
    if (event.code === 4001) {
      errorMessage.value = 'Authentication failed. Please log in again.'
    } else if (event.code === 4004) {
      errorMessage.value = event.reason || 'Terminal not available.'
    } else if (event.code !== 1000 && event.code !== 1005) {
      errorMessage.value = event.reason || `Connection lost (code ${event.code})`
    } else {
      errorMessage.value = ''
    }
  }

  ws.onerror = () => {
    connectionStatus.value = 'disconnected'
    toastBus.error('Terminal connection error')
    errorMessage.value = 'Connection error. Please try again.'
  }

  ws.onmessage = (event) => {
    // xterm.js write handles both string and Uint8Array
    term?.write(typeof event.data === 'string' ? event.data : new Uint8Array(event.data))
  }

  // Forward keystrokes to WebSocket
  term?.onData((data) => {
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(data)
    }
  })
}

// ── WebGL renderer with Canvas fallback ──────────────────────────
function loadRenderer() {
  if (!term) return
  try {
    webgl = new WebglAddon()
    webgl.onContextLoss(() => {
      console.warn('WebGL context lost, falling back to canvas')
      webgl?.dispose()
      webgl = null
      loadCanvasFallback()
    })
    term.loadAddon(webgl)
    console.log('Terminal using WebGL renderer')
  } catch (e) {
    console.warn('WebGL not available, using canvas fallback:', e)
    loadCanvasFallback()
  }
}

function loadCanvasFallback() {
  if (!term) return
  try {
    canvas = new CanvasAddon()
    term.loadAddon(canvas)
    console.log('Terminal using Canvas renderer')
  } catch (e) {
    console.warn('Canvas addon failed, using DOM renderer:', e)
  }
}

function disconnect() {
  ws?.close()
  ws = null
  webgl?.dispose()
  webgl = null
  canvas?.dispose()
  canvas = null
  term?.dispose()
  term = null
}
</script>

<template>
  <div :class="[fullscreen ? 'fixed inset-0 z-50 bg-void flex flex-col' : 'flex flex-col h-full']">
    <!-- Status bar -->
    <div class="flex items-center gap-3 px-4 py-1.5 border-b border-white/5 bg-white/1 backdrop-blur-sm">
      <div class="w-2 h-2 rounded-full" :class="{
        'bg-[#6B7280]': connectionStatus === 'disconnected',
        'bg-[#F59E0B] animate-pulse': connectionStatus === 'connecting',
        'bg-[#22C55E]': connectionStatus === 'connected'
      }" />
      <span class="text-[10px] text-text-tertiary font-medium">{{
        connectionStatus === 'connecting' ? 'Connecting...' :
        connectionStatus === 'connected' ? 'Connected' : 'Disconnected'
      }}</span>
      <div class="flex bg-white/5 rounded-lg p-0.5">
        <button @click="mode='pi'" :disabled="connected" :class="[
          'px-3 py-1 text-xs font-medium rounded-md transition-colors',
          mode === 'pi' ? 'bg-accent text-void' : 'text-text-tertiary hover:text-text-secondary'
        ]">Pi</button>
        <button @click="mode='bash'" :disabled="connected" :class="[
          'px-3 py-1 text-xs font-medium rounded-md transition-colors',
          mode === 'bash' ? 'bg-accent text-void' : 'text-text-tertiary hover:text-text-secondary'
        ]">Bash</button>
      </div>
      <div class="ml-auto flex items-center gap-2">
        <button
          v-if="showFullscreenToggle"
          @click="emit('toggle-fullscreen')"
          class="flex items-center justify-center w-7 h-7 rounded-lg text-text-tertiary hover:text-text-secondary transition-colors"
          :title="fullscreen ? 'Exit fullscreen (Esc)' : 'Fullscreen'"
        >
          <svg v-if="!fullscreen" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
          </svg>
          <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 9V4.5M9 9H4.5M9 9L3.75 3.75M9 15v4.5M9 15H4.5M9 15l-5.25 5.25M15 9h4.5M15 9V4.5M15 9l5.25-5.25M15 15h4.5M15 15v4.5m0-4.5l5.25 5.25" />
          </svg>
        </button>
        <button v-if="connectionStatus === 'disconnected'" @click="connect" class="text-[10px] text-accent font-medium hover:underline">Reconnect</button>
      </div>
    </div>
    <!-- Terminal -->
    <div ref="terminalEl" class="flex-1 overflow-hidden" />
    <!-- Error bar -->
    <div v-if="errorMessage" class="px-4 py-2 bg-danger/10 border-t border-danger/20 text-danger text-xs">
      {{ errorMessage }}
    </div>
  </div>
</template>
