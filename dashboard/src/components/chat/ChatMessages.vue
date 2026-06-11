<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick, watch, computed } from 'vue'
import ChatBubble from './ChatBubble.vue'
import type { ToolCallBlock } from './ChatBubble.vue'

interface ChatMessage {
  role: 'user' | 'agent'
  textParts: string[]
  toolBlocks: ToolCallBlock[]
  timestamp: number
}

const props = defineProps<{
  messages: ChatMessage[]
  streaming?: boolean
  streamText?: string
  streamTools?: ToolCallBlock[]
  thinking?: boolean
  loading?: boolean
}>()

const emit = defineEmits<{
  'scroll-changed': [userScrolledUp: boolean]
}>()

const messageList = ref<HTMLElement | null>(null)
const userScrolledUp = ref(false)
const showJumpButton = ref(false)
let resizeObserver: ResizeObserver | null = null

// ── Auto-scroll logic ────────────────────────────────────────────

function scrollToBottom(smooth = true) {
  if (!messageList.value) return
  messageList.value.scrollTo({
    top: messageList.value.scrollHeight,
    behavior: smooth ? 'smooth' : 'instant',
  })
}

function onScroll() {
  if (!messageList.value) return
  const el = messageList.value
  const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 100
  userScrolledUp.value = !atBottom
  showJumpButton.value = !atBottom
  emit('scroll-changed', userScrolledUp.value)
}

function jumpToBottom() {
  userScrolledUp.value = false
  showJumpButton.value = false
  scrollToBottom(true)
  emit('scroll-changed', false)
}

// ── Auto-scroll on new messages ──────────────────────────────────

let prevMsgCount = 0

watch(
  () => props.messages.length,
  (newCount) => {
    if (newCount > prevMsgCount && !userScrolledUp.value) {
      nextTick(() => scrollToBottom(true))
    }
    prevMsgCount = newCount
  }
)

watch(
  () => props.streaming,
  (isStreaming) => {
    if (isStreaming && !userScrolledUp.value) {
      nextTick(() => scrollToBottom(false))
    }
  }
)

// ── ResizeObserver for container resize ──────────────────────────

onMounted(() => {
  if (messageList.value) {
    resizeObserver = new ResizeObserver(() => {
      if (!userScrolledUp.value) {
        scrollToBottom(false)
      }
    })
    resizeObserver.observe(messageList.value)
  }
})

onUnmounted(() => {
  if (resizeObserver) {
    resizeObserver.disconnect()
    resizeObserver = null
  }
})

// ── Loading skeleton ─────────────────────────────────────────────

const skeletonMessages = computed(() => [
  { width: '60%', lines: 2, role: 'agent' as const },
  { width: '40%', lines: 1, role: 'user' as const },
  { width: '75%', lines: 3, role: 'agent' as const },
])

// ── Flatten messages into renderable items ───────────────────────

interface RenderItem {
  id: string
  role: 'user' | 'agent'
  content: string
  timestamp: number
  toolCalls?: ToolCallBlock[]
  streaming?: boolean
  thinking?: boolean
}

const renderItems = computed<RenderItem[]>(() => {
  const items: RenderItem[] = []
  let toolAccum: ToolCallBlock[] = []

  for (const msg of props.messages) {
    const content = msg.textParts.join('\n')

    // Collect tool blocks
    if (msg.toolBlocks?.length) {
      toolAccum.push(...msg.toolBlocks)
    }

    if (content) {
      items.push({
        id: `msg-${items.length}-${msg.timestamp}`,
        role: msg.role,
        content,
        timestamp: msg.timestamp,
        toolCalls: toolAccum.length > 0 ? [...toolAccum] : undefined,
      })
      toolAccum = []
    } else if (toolAccum.length > 0) {
      // Tool-only message (no text)
      items.push({
        id: `msg-${items.length}-${msg.timestamp}`,
        role: msg.role,
        content: '',
        timestamp: msg.timestamp,
        toolCalls: [...toolAccum],
      })
      toolAccum = []
    }
  }

  // Streaming message
  if (props.streaming) {
    const streamToolCalls = props.streamTools?.length ? [...props.streamTools] : undefined

    if (props.thinking) {
      items.push({
        id: 'stream-thinking',
        role: 'agent',
        content: '',
        timestamp: Date.now(),
        thinking: true,
      })
    } else if (props.streamText || streamToolCalls) {
      items.push({
        id: 'streaming',
        role: 'agent',
        content: props.streamText || '',
        timestamp: Date.now(),
        toolCalls: streamToolCalls,
        streaming: true,
      })
    }
  }

  return items
})
</script>

<template>
  <div class="messages-container">
    <!-- Message list -->
    <div
      ref="messageList"
      class="messages-scroll"
      @scroll="onScroll"
    >
      <!-- Loading skeleton -->
      <div v-if="loading" class="skeleton-container">
        <div
          v-for="(s, i) in skeletonMessages"
          :key="'skeleton-' + i"
          class="flex gap-2 items-start mb-4"
          :class="s.role === 'user' ? 'flex-row-reverse' : 'flex-row'"
        >
          <div class="skeleton-avatar" />
          <div
            class="skeleton-bubble"
            :class="s.role === 'user' ? 'skeleton-bubble-user' : 'skeleton-bubble-agent'"
            :style="{ width: s.width }"
          >
            <div
              v-for="l in s.lines"
              :key="'l-' + l"
              class="skeleton-line"
              :style="{ width: l === s.lines ? '60%' : '100%' }"
            />
          </div>
        </div>
      </div>

      <!-- Empty state -->
      <div
        v-else-if="renderItems.length === 0 && !loading"
        class="empty-state"
      >
        <div class="text-3xl mb-3 opacity-20">⟐</div>
        <div>Send a message to start chatting with Slice of Pi</div>
      </div>

      <!-- Messages -->
      <div v-else class="messages-list">
        <ChatBubble
          v-for="(item, idx) in renderItems"
          :key="item.id"
          :role="item.role"
          :content="item.content"
          :timestamp="item.timestamp"
          :tool-calls="item.toolCalls"
          :streaming="item.streaming"
          :thinking="item.thinking"
          :class="{ 'message-fade-in': idx >= renderItems.length - 2 }"
        />
      </div>
    </div>

    <!-- Jump to bottom button -->
    <Transition name="jump-fade">
      <button
        v-if="showJumpButton"
        class="jump-button"
        @click="jumpToBottom"
      >
        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 14l-7 7m0 0l-7-7m7 7V3" />
        </svg>
        New messages
      </button>
    </Transition>
  </div>
</template>

<style scoped>
.messages-container {
  position: relative;
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.messages-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  scroll-behavior: smooth;
}

.messages-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* ── Scrollbar styling ─────────────────────────────────────────── */

.messages-scroll::-webkit-scrollbar {
  width: 6px;
}

.messages-scroll::-webkit-scrollbar-track {
  background: transparent;
}

.messages-scroll::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.06);
  border-radius: 3px;
}

.messages-scroll::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.1);
}

/* ── Empty state ───────────────────────────────────────────────── */

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 200px;
  color: rgba(255, 255, 255, 0.25);
  font-size: 13px;
  text-align: center;
}

/* ── Jump button ───────────────────────────────────────────────── */

.jump-button {
  position: absolute;
  bottom: 12px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 9999px;
  background: #9DD522;
  color: #fff;
  font-size: 11px;
  font-weight: 500;
  border: none;
  cursor: pointer;
  box-shadow: 0 4px 16px rgba(99, 102, 241, 0.35);
  transition: all 0.3s cubic-bezier(0.32, 0.72, 0, 1);
  z-index: 10;
  white-space: nowrap;
}

.jump-button:hover {
  background: #8BC01E;
  box-shadow: 0 6px 24px rgba(99, 102, 241, 0.5);
  transform: translateX(-50%) translateY(-1px);
}

.jump-fade-enter-active,
.jump-fade-leave-active {
  transition: all 0.3s cubic-bezier(0.32, 0.72, 0, 1);
}

.jump-fade-enter-from,
.jump-fade-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(10px);
}

/* ── Loading skeleton ──────────────────────────────────────────── */

.skeleton-container {
  padding: 8px 0;
}

.skeleton-avatar {
  width: 24px;
  height: 24px;
  border-radius: 9999px;
  background: rgba(255, 255, 255, 0.04);
  flex-shrink: 0;
  animation: shimmer 1.5s ease-in-out infinite;
}

.skeleton-bubble {
  border-radius: 16px;
  padding: 10px 12px;
  animation: shimmer 1.5s ease-in-out infinite;
}

.skeleton-bubble-agent {
  background: rgba(255, 255, 255, 0.03);
  border-bottom-left-radius: 6px;
}

.skeleton-bubble-user {
  background: rgba(99, 102, 241, 0.08);
  border-bottom-right-radius: 6px;
}

.skeleton-line {
  height: 8px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.06);
  margin-bottom: 6px;
}

.skeleton-line:last-child {
  margin-bottom: 0;
}

@keyframes shimmer {
  0% { opacity: 0.4; }
  50% { opacity: 0.7; }
  100% { opacity: 0.4; }
}

/* ── Message fade-in ───────────────────────────────────────────── */

.message-fade-in {
  animation: msgFadeIn 0.4s cubic-bezier(0.32, 0.72, 0, 1);
}

@keyframes msgFadeIn {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
