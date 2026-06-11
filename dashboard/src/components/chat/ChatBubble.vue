<script setup lang="ts">
import { ref, computed } from 'vue'

export interface ToolCallBlock {
  type: 'tool_call' | 'tool_result'
  name: string
  input?: string
  result?: string
  truncated?: boolean
  fullSize?: number
}

const props = defineProps<{
  role: 'user' | 'agent'
  content: string
  timestamp: number
  toolCalls?: ToolCallBlock[]
  streaming?: boolean
  thinking?: boolean
}>()

const expandedTools = ref<Set<number>>(new Set())

function toggleTool(idx: number) {
  if (expandedTools.value.has(idx)) {
    expandedTools.value.delete(idx)
  } else {
    expandedTools.value.add(idx)
  }
}

// ── Relative timestamp ────────────────────────────────────────────

const relativeTime = computed(() => {
  const diff = Date.now() - props.timestamp
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  if (days < 30) return `${days}d ago`
  return new Date(props.timestamp).toLocaleDateString()
})

// ── Simple markdown renderer ──────────────────────────────────────

function renderMarkdown(text: string): string {
  let html = escapeHtml(text)

  // Code blocks (```) — must be processed before inline code
  html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, (_match, lang: string, code: string) => {
    const langClass = lang ? ` class="language-${escapeHtml(lang)}"` : ''
    const encoded = escapeHtml(code.trim())
    // The copy button is added via DOM — we'll use a data attribute
    return `<pre class="code-block"><div class="code-header"><span class="code-lang">${escapeHtml(lang || 'code')}</span><button class="copy-btn" data-code="${encodeURIComponent(encoded)}">Copy</button></div><code${langClass}>${encoded}</code></pre>`
  })

  // Inline code
  html = html.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>')

  // Bold
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')

  // Italic
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>')

  // Links [text](url)
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a class="chat-link" href="$2" target="_blank" rel="noopener">$1</a>')

  // Convert line breaks to paragraphs
  const lines = html.split('\n')
  const result: string[] = []
  let inList: string | null = null

  for (const line of lines) {
    const trimmed = line.trim()

    // Unordered list
    const ulMatch = trimmed.match(/^[-*+]\s+(.+)/)
    if (ulMatch) {
      if (inList !== 'ul') {
        if (inList) result.push(`</${inList}>`)
        result.push('<ul class="chat-list">')
        inList = 'ul'
      }
      result.push(`<li>${ulMatch[1]}</li>`)
      continue
    }

    // Ordered list
    const olMatch = trimmed.match(/^\d+\.\s+(.+)/)
    if (olMatch) {
      if (inList !== 'ol') {
        if (inList) result.push(`</${inList}>`)
        result.push('<ol class="chat-list">')
        inList = 'ol'
      }
      result.push(`<li>${olMatch[1]}</li>`)
      continue
    }

    // Close list if we were in one
    if (inList) {
      result.push(`</${inList}>`)
      inList = null
    }

    // Empty line = paragraph break
    if (!trimmed) {
      result.push('</p><p>')
      continue
    }

    // Regular paragraph
    result.push(trimmed + '<br/>')
  }

  if (inList) result.push(`</${inList}>`)
  return `<p>${result.join('')}</p>`
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

const renderedContent = computed(() => {
  if (!props.content) return ''
  if (props.role === 'user') return escapeHtml(props.content)
  return renderMarkdown(props.content)
})

// ── Copy handler for code blocks ──────────────────────────────────

function handleContainerClick(e: MouseEvent) {
  const target = e.target as HTMLElement
  if (target.classList.contains('copy-btn')) {
    const encoded = target.getAttribute('data-code')
    if (encoded) {
      const code = decodeURIComponent(encoded)
      navigator.clipboard.writeText(code).catch(() => {
        // Fallback
        const ta = document.createElement('textarea')
        ta.value = code
        document.body.appendChild(ta)
        ta.select()
        document.execCommand('copy')
        document.body.removeChild(ta)
      })
      target.textContent = 'Copied!'
      setTimeout(() => { target.textContent = 'Copy' }, 2000)
    }
  }
}
</script>

<template>
  <div
    class="flex gap-2 items-start"
    :class="role === 'user' ? 'flex-row-reverse' : 'flex-row'"
  >
    <!-- Avatar -->
    <div
      class="chat-avatar shrink-0"
      :class="role === 'agent' ? 'bg-accent/15 text-[#9DD522]' : 'bg-white/6 text-text-tertiary'"
    >
      {{ role === 'agent' ? 'A' : 'U' }}
    </div>

    <!-- Bubble container -->
    <div class="max-w-[80%] space-y-1.5 min-w-0">
      <!-- Thinking state -->
      <div
        v-if="thinking"
        class="chat-bubble chat-bubble-agent"
      >
        <div class="flex gap-1.5 py-1">
          <span class="thinking-dot" style="animation-delay:0ms" />
          <span class="thinking-dot" style="animation-delay:200ms" />
          <span class="thinking-dot" style="animation-delay:400ms" />
        </div>
      </div>

      <!-- Content bubble -->
      <div
        v-else-if="content"
        class="chat-bubble"
        :class="role === 'user' ? 'chat-bubble-user' : 'chat-bubble-agent'"
        @click="handleContainerClick"
      >
        <span
          v-if="role === 'user'"
          class="whitespace-pre-wrap break-words"
        >{{ content }}</span>
        <span
          v-else
          class="rendered-markdown"
          v-html="renderedContent"
        />
        <!-- Streaming cursor -->
        <span
          v-if="streaming"
          class="streaming-cursor"
        />
      </div>

      <!-- Tool calls -->
      <div
        v-for="(tc, idx) in toolCalls"
        :key="idx"
        class="tool-chip"
        :class="tc.type === 'tool_call' ? 'tool-chip-call' : 'tool-chip-result'"
      >
        <div class="flex items-center gap-1.5">
          <span class="shrink-0">{{ tc.type === 'tool_call' ? '🔧' : '✓' }}</span>
          <span class="font-medium truncate">{{ tc.name }}</span>
          <span
            v-if="tc.type === 'tool_result' && !expandedTools.has(idx) && tc.result"
            class="truncate flex-1 text-text-muted text-[10px]"
          >{{ tc.result.slice(0, 60) }}</span>
          <button
            v-if="tc.type === 'tool_result' && tc.truncated"
            class="tool-expand-btn"
            @click="toggleTool(idx)"
          >
            {{ expandedTools.has(idx) ? '▲ Less' : '▼ More' }}
          </button>
        </div>
        <div
          v-if="expandedTools.has(idx)"
          class="mt-1.5 pt-1.5 border-t border-white/5 font-mono text-[10px] whitespace-pre-wrap break-all max-h-60 overflow-y-auto"
        >
          <template v-if="tc.type === 'tool_call' && tc.input">{{ tc.input }}</template>
          <template v-else-if="tc.type === 'tool_result' && tc.result">{{ tc.result }}</template>
        </div>
      </div>

      <!-- Timestamp -->
      <div
        class="text-[10px] text-text-muted px-1"
        :class="role === 'user' ? 'text-right' : 'text-left'"
      >{{ relativeTime }}</div>
    </div>
  </div>
</template>

<style scoped>
.chat-avatar {
  width: 24px;
  height: 24px;
  border-radius: 9999px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 700;
  margin-top: 4px;
}

.chat-bubble {
  border-radius: 16px;
  padding: 8px 12px;
  font-size: 12px;
  line-height: 1.6;
}

.chat-bubble-user {
  background: rgba(99, 102, 241, 0.12);
  border: 1px solid rgba(99, 102, 241, 0.15);
  color: #F0F0F2;
  border-bottom-right-radius: 6px;
}

.chat-bubble-agent {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.05);
  color: rgba(255, 255, 255, 0.65);
  border-bottom-left-radius: 6px;
}

/* ── Thinking dots ─────────────────────────────────────────────── */

.thinking-dot {
  width: 6px;
  height: 6px;
  border-radius: 9999px;
  background: rgba(255, 255, 255, 0.35);
  animation: thinkPulse 1.4s ease-in-out infinite;
}

@keyframes thinkPulse {
  0%, 60%, 100% { opacity: 0.3; transform: scale(1); }
  30% { opacity: 1; transform: scale(1.3); }
}

/* ── Streaming cursor ──────────────────────────────────────────── */

.streaming-cursor {
  display: inline-block;
  width: 2px;
  height: 14px;
  background: #9DD522;
  margin-left: 2px;
  vertical-align: middle;
  animation: blink 1s step-end infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

/* ── Tool chips ────────────────────────────────────────────────── */

.tool-chip {
  border-radius: 10px;
  padding: 5px 10px;
  font-size: 11px;
  border: 1px solid;
}

.tool-chip-call {
  background: rgba(245, 158, 11, 0.08);
  border-color: rgba(245, 158, 11, 0.15);
  color: rgba(251, 191, 36, 0.8);
}

.tool-chip-result {
  background: rgba(34, 197, 94, 0.08);
  border-color: rgba(34, 197, 94, 0.15);
  color: rgba(74, 222, 128, 0.7);
}

.tool-expand-btn {
  margin-left: auto;
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 4px;
  border: 1px solid currentColor;
  opacity: 0.6;
  cursor: pointer;
  background: transparent;
  transition: opacity 0.2s;
  white-space: nowrap;
  color: inherit;
}

.tool-expand-btn:hover {
  opacity: 1;
}

/* ── Rendered markdown ─────────────────────────────────────────── */

:deep(.chat-link) {
  color: #9DD522;
  text-decoration: underline;
}

:deep(.inline-code) {
  background: rgba(255, 255, 255, 0.08);
  padding: 0 5px;
  border-radius: 3px;
  font-size: 10px;
  font-family: 'JetBrains Mono', Menlo, 'Courier New', monospace;
}

:deep(.code-block) {
  background: rgba(0, 0, 0, 0.3);
  border-radius: 8px;
  margin: 8px 0;
  overflow: hidden;
}

:deep(.code-header) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 10px;
  background: rgba(255, 255, 255, 0.04);
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
}

:deep(.code-lang) {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.35);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

:deep(.copy-btn) {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.4);
  background: rgba(255, 255, 255, 0.06);
  border: none;
  padding: 2px 8px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

:deep(.copy-btn:hover) {
  color: rgba(255, 255, 255, 0.7);
  background: rgba(255, 255, 255, 0.1);
}

:deep(.code-block code) {
  display: block;
  padding: 10px 12px;
  font-size: 11px;
  font-family: 'JetBrains Mono', Menlo, 'Courier New', monospace;
  line-height: 1.6;
  overflow-x: auto;
  white-space: pre;
}

:deep(.chat-list) {
  list-style: disc;
  padding-left: 20px;
  margin: 4px 0;
}

:deep(.chat-list li) {
  margin: 2px 0;
}

:deep(p) {
  margin: 4px 0;
}

:deep(p:empty) {
  display: none;
}

:deep(strong) {
  color: rgba(255, 255, 255, 0.85);
  font-weight: 600;
}

:deep(em) {
  font-style: italic;
}
</style>
