<script setup lang="ts">
import { ref, nextTick } from 'vue'

interface ToolBlock {
  type: 'tool_call' | 'tool_result'
  name: string
  input?: string
  result?: string
}

interface ChatMessage {
  role: 'user' | 'agent'
  textParts: string[]
  toolBlocks: ToolBlock[]
  timestamp: number
}

const props = defineProps<{ agentId: string }>()

const messages = ref<ChatMessage[]>([])
const input = ref('')
const streaming = ref(false)
const streamText = ref('')
const streamTools = ref<ToolBlock[]>([])
const thinking = ref(false)
const chatEl = ref<HTMLElement | null>(null)
const expandedTools = ref<Set<number>>(new Set())

function toggleTool(idx: number) {
  if (expandedTools.value.has(idx)) {
    expandedTools.value.delete(idx)
  } else {
    expandedTools.value.add(idx)
  }
}

async function send() {
  const text = input.value.trim()
  if (!text || streaming.value) return

  messages.value.push({ role: 'user', textParts: [text], toolBlocks: [], timestamp: Date.now() })
  input.value = ''
  streaming.value = true
  thinking.value = true
  streamText.value = ''
  streamTools.value = []

  try {
    const res = await fetch(`/api/agents/${props.agentId}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text }),
    })

    const reader = res.body?.getReader()
    if (!reader) throw new Error('No reader')

    const decoder = new TextDecoder()
    let buffer = ''
    let pendingTool: Partial<ToolBlock> = {}

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
            pendingTool = { type: 'tool_call', name: chunk.tool_name, input: JSON.stringify(chunk.tool_input || {}).slice(0, 200) }
          } else if (chunk.type === 'tool_result') {
            if (pendingTool.type) {
              streamTools.value.push({
                type: 'tool_call',
                name: pendingTool.name || chunk.tool_name || '',
                input: pendingTool.input,
              })
              streamTools.value.push({
                type: 'tool_result',
                name: chunk.tool_name || '',
                result: (chunk.content || '').slice(0, 500),
              })
              pendingTool = {}
            }
          } else if (chunk.type === 'thinking_delta' || chunk.type === 'thinking_start') {
            thinking.value = true
          } else if (chunk.type === 'text_start') {
            thinking.value = false
          }
        } catch { /* skip */ }
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

  await nextTick()
  chatEl.value?.scrollTo({ top: chatEl.value.scrollHeight, behavior: 'smooth' })
}
</script>

<template>
  <div class="flex flex-col h-full">
    <!-- Messages -->
    <div ref="chatEl" class="flex-1 overflow-y-auto p-4 space-y-3 min-h-[200px] max-h-[360px]">
      <div v-if="messages.length === 0 && !streaming" class="text-xs text-text-tertiary text-center py-8">
        Send a message to start chatting with this agent
      </div>

      <div v-for="(msg, i) in messages" :key="i" class="flex gap-2" :class="msg.role === 'user' ? 'justify-end' : ''">
        <div v-if="msg.role === 'agent'" class="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold bg-accent/15 text-[#818CF8] shrink-0 mt-1">A</div>

        <div class="max-w-[80%] space-y-1.5" :class="msg.role === 'user' ? 'items-end' : ''">
          <!-- Text bubbles -->
          <div v-for="(part, pi) in msg.textParts" :key="'t'+pi" class="rounded-2xl px-3 py-2 text-xs leading-relaxed"
            :class="msg.role === 'user'
              ? 'bg-accent/12 border border-accent/15 text-text-primary rounded-br-md'
              : 'bg-white/4 border border-white/5 text-text-secondary rounded-bl-md'">
            {{ part }}
          </div>

          <!-- Tool call blocks -->
          <div v-for="(tb, ti) in msg.toolBlocks" :key="'tb'+ti" class="rounded-xl px-3 py-1.5 text-[11px] border cursor-pointer transition-colors"
            :class="tb.type === 'tool_call'
              ? 'bg-amber-500/8 border-amber-500/15 text-amber-400/80'
              : 'bg-success/8 border-success/15 text-success/70'"
            @click="toggleTool(i * 1000 + ti)">
            <div class="flex items-center gap-1.5">
              <span>{{ tb.type === 'tool_call' ? '🔧' : '✓' }}</span>
              <span class="font-medium">{{ tb.name }}</span>
              <span v-if="tb.type === 'tool_result' && !expandedTools.has(i * 1000 + ti)" class="text-text-muted truncate flex-1">{{ tb.result?.slice(0, 60) }}</span>
            </div>
            <div v-if="expandedTools.has(i * 1000 + ti)" class="mt-1.5 pt-1.5 border-t border-white/5 font-mono text-[10px] whitespace-pre-wrap break-all">
              <template v-if="tb.type === 'tool_call' && tb.input">{{ tb.input }}</template>
              <template v-else-if="tb.type === 'tool_result' && tb.result">{{ tb.result }}</template>
            </div>
          </div>
        </div>

        <div v-if="msg.role === 'user'" class="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold bg-white/6 text-text-tertiary shrink-0 mt-1">U</div>
      </div>

      <!-- Streaming: thinking indicator -->
      <div v-if="thinking" class="flex gap-2">
        <div class="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold bg-accent/15 text-[#818CF8] shrink-0 mt-1">A</div>
        <div class="rounded-2xl rounded-bl-md px-3 py-2 bg-white/4 border border-white/5">
          <div class="flex gap-1.5">
            <span class="w-1.5 h-1.5 rounded-full bg-text-muted animate-pulse" style="animation-delay:0ms" />
            <span class="w-1.5 h-1.5 rounded-full bg-text-muted animate-pulse" style="animation-delay:200ms" />
            <span class="w-1.5 h-1.5 rounded-full bg-text-muted animate-pulse" style="animation-delay:400ms" />
          </div>
        </div>
      </div>

      <!-- Streaming: text + tools -->
      <div v-if="(streamText || streamTools.length) && !thinking" class="flex gap-2">
        <div class="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold bg-accent/15 text-[#818CF8] shrink-0 mt-1">A</div>
        <div class="max-w-[80%] space-y-1.5">
          <div v-if="streamText" class="rounded-2xl rounded-bl-md px-3 py-2 text-xs leading-relaxed bg-white/4 border border-white/5 text-text-secondary">
            {{ streamText }}<span class="inline-block w-1.5 h-3.5 bg-accent/60 ml-0.5 animate-pulse align-middle" />
          </div>
          <div v-for="(tb, ti) in streamTools" :key="'st'+ti" class="rounded-xl px-3 py-1.5 text-[11px] border"
            :class="tb.type === 'tool_call'
              ? 'bg-amber-500/8 border-amber-500/15 text-amber-400/80'
              : 'bg-success/8 border-success/15 text-success/70'">
            <span>{{ tb.type === 'tool_call' ? '🔧' : '✓' }}</span>
            <span class="font-medium ml-1">{{ tb.name }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Input -->
    <div class="flex items-center gap-2 mx-4 mb-3 p-2 bg-white/3 border border-white/5 rounded-2xl">
      <input v-model="input" @keyup.enter="send" :disabled="streaming"
        placeholder="Message agent..." class="flex-1 bg-transparent border-none outline-none text-xs text-text-secondary placeholder:text-text-muted" />
      <button @click="send" :disabled="!input.trim() || streaming"
        class="w-7 h-7 rounded-full bg-accent flex items-center justify-center text-white text-xs disabled:opacity-30 transition-opacity shrink-0">↑</button>
    </div>
  </div>
</template>
