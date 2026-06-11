<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'

interface Session {
  id: string
  agent_id: string
  agent_name: string
  status: string
  turns: number
  tokens_in: number
  tokens_out: number
  model: string
  name?: string
  started_at: string
  ended_at?: string
}

interface TimelineEvent {
  id: string
  sessionId: string
  agent_name: string
  agent_id: string
  type: 'start' | 'turn' | 'end'
  time: Date
  label: string
  model: string
  tokens: number
}

const props = defineProps<{
  sessions: Session[]
  loading?: boolean
}>()

const emit = defineEmits<{
  'select-session': [sessionId: string]
}>()

// ── Zoom and scroll state ───────────────────────────────────────
const zoomLevel = ref(5) // pixels per minute
const autoScroll = ref(true)
const hideInactiveAgents = ref(false)
const timelineEl = ref<HTMLElement | null>(null)

// ── Build timeline events from sessions ────────────────────────
const events = computed<TimelineEvent[]>(() => {
  const result: TimelineEvent[] = []
  for (const s of props.sessions) {
    const start = new Date(s.started_at)
    result.push({
      id: `${s.id}-start`,
      sessionId: s.id,
      agent_name: s.agent_name,
      agent_id: s.agent_id,
      type: 'start',
      time: start,
      label: s.name || `${s.agent_name} started`,
      model: s.model,
      tokens: 0,
    })
    for (let t = 0; t < s.turns; t++) {
      const turnTime = new Date(start.getTime() + (t + 1) * 30000) // ~30s per turn
      result.push({
        id: `${s.id}-turn-${t}`,
        sessionId: s.id,
        agent_name: s.agent_name,
        agent_id: s.agent_id,
        type: 'turn',
        time: turnTime,
        label: `Turn ${t + 1}`,
        model: s.model,
        tokens: Math.round((s.tokens_in + s.tokens_out) / Math.max(s.turns, 1)),
      })
    }
    if (s.ended_at) {
      result.push({
        id: `${s.id}-end`,
        sessionId: s.id,
        agent_name: s.agent_name,
        agent_id: s.agent_id,
        type: 'end',
        time: new Date(s.ended_at),
        label: s.status,
        model: s.model,
        tokens: 0,
      })
    }
  }
  result.sort((a, b) => a.time.getTime() - b.time.getTime())
  return result
})

// ── Active agents (agents with sessions in view) ───────────────
const activeAgents = computed(() => {
  const names = new Set(events.value.map(e => e.agent_name))
  return [...names].sort()
})

const visibleAgents = computed(() => {
  if (!hideInactiveAgents.value) return activeAgents.value
  // Show only agents with recent activity (last hour)
  const oneHourAgo = Date.now() - 3600000
  const recent = new Set(
    events.value
      .filter(e => e.time.getTime() > oneHourAgo)
      .map(e => e.agent_name)
  )
  return activeAgents.value.filter(a => recent.has(a))
})

// ── Time range ─────────────────────────────────────────────────
const now = ref(Date.now())
const timeStart = computed(() => {
  if (events.value.length === 0) return new Date(now.value - 3600000)
  return new Date(Math.min(...events.value.map(e => e.time.getTime())) - 60000)
})
const timeEnd = computed(() => new Date(now.value + 60000))
const totalMinutes = computed(() =>
  Math.max(1, (timeEnd.value.getTime() - timeStart.value.getTime()) / 60000)
)
const pixelsPerMinute = computed(() => zoomLevel.value)

// ── Agent colors ───────────────────────────────────────────────
const agentColors = ref<Record<string, string>>({})
const palette = ['#9DD522', '#22C55E', '#F59E0B', '#EF4444', '#A855F7', '#22D3EE', '#EC4899', '#14B8A6']

function getAgentColor(name: string): string {
  if (!agentColors.value[name]) {
    const idx = Object.keys(agentColors.value).length % palette.length
    agentColors.value[name] = palette[idx]
  }
  return agentColors.value[name]
}

// ── Time axis ticks ────────────────────────────────────────────
const ticks = computed(() => {
  const result: { time: Date; x: number; label: string }[] = []
  const start = timeStart.value.getTime()
  const end = timeEnd.value.getTime()
  // Every 15 minutes
  const interval = 15 * 60000
  let t = Math.floor(start / interval) * interval
  while (t <= end) {
    const d = new Date(t)
    result.push({
      time: d,
      x: ((t - start) / 60000) * pixelsPerMinute.value,
      label: d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    })
    t += interval
  }
  return result
})

// ── Event positions ────────────────────────────────────────────
interface PositionedEvent extends TimelineEvent {
  x: number
  y: number
  lane: number
}

const positionedEvents = computed(() => {
  const startMs = timeStart.value.getTime()
  const agentLanes: Record<string, number> = {}
  let nextLane = 0

  return events.value.map(e => {
    if (!(e.agent_name in agentLanes)) {
      agentLanes[e.agent_name] = nextLane++
    }
    return {
      ...e,
      x: ((e.time.getTime() - startMs) / 60000) * pixelsPerMinute.value,
      y: agentLanes[e.agent_name] * 36,
      lane: agentLanes[e.agent_name],
    }
  })
})

// ── Timeline width ─────────────────────────────────────────────
const timelineWidth = computed(() =>
  Math.max(800, totalMinutes.value * pixelsPerMinute.value)
)
const timelineHeight = computed(() =>
  Math.max(100, visibleAgents.value.length * 36 + 20)
)

// ── Scroll to now ──────────────────────────────────────────────
function jumpToNow() {
  if (!timelineEl.value) return
  const startMs = timeStart.value.getTime()
  const nowX = ((Date.now() - startMs) / 60000) * pixelsPerMinute.value
  timelineEl.value.scrollLeft = nowX - timelineEl.value.clientWidth / 2
}

// ── Auto-scroll to now ─────────────────────────────────────────
let scrollInterval: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  if (autoScroll.value) {
    setTimeout(jumpToNow, 100)
  }
  scrollInterval = setInterval(() => {
    now.value = Date.now()
    if (autoScroll.value) {
      jumpToNow()
    }
  }, 10000)
})

onUnmounted(() => {
  if (scrollInterval) clearInterval(scrollInterval)
})

function onSelectSession(sessionId: string) {
  emit('select-session', sessionId)
}
</script>

<template>
  <div class="replay-timeline">
    <!-- Toolbar -->
    <div class="flex items-center justify-between mb-3">
      <div class="flex items-center gap-3">
        <span class="text-xs text-text-tertiary">{{ props.sessions.length }} sessions</span>
        <div class="flex items-center gap-1">
          <button
            class="timeline-btn"
            @click="zoomLevel = Math.max(1, zoomLevel - 1)"
            title="Zoom out"
          >−</button>
          <span class="text-[10px] text-text-tertiary w-8 text-center">{{ zoomLevel }}px/m</span>
          <button
            class="timeline-btn"
            @click="zoomLevel = Math.min(50, zoomLevel + 1)"
            title="Zoom in"
          >+</button>
        </div>
        <label class="flex items-center gap-1.5 text-[10px] text-text-tertiary cursor-pointer">
          <input type="checkbox" v-model="autoScroll" class="accent-accent" />
          Auto-scroll
        </label>
        <label class="flex items-center gap-1.5 text-[10px] text-text-tertiary cursor-pointer">
          <input type="checkbox" v-model="hideInactiveAgents" class="accent-accent" />
          Active only
        </label>
      </div>
      <button
        v-if="!autoScroll"
        class="timeline-btn text-accent"
        @click="jumpToNow"
      >Jump to now</button>
    </div>

    <!-- Timeline canvas -->
    <div
      ref="timelineEl"
      class="timeline-scroll"
      :class="{ 'border border-white/6 rounded-xl': true }"
    >
      <div class="timeline-inner" :style="{ width: timelineWidth + 'px', height: timelineHeight + 'px' }">
        <!-- Grid lines -->
        <svg class="absolute inset-0 w-full h-full pointer-events-none" :style="{ width: timelineWidth + 'px', height: timelineHeight + 'px' }">
          <!-- Horizontal agent lanes -->
          <line
            v-for="(name, i) in visibleAgents"
            :key="'hl-' + name"
            :x1="0"
            :y1="(i + 1) * 36"
            :x2="timelineWidth"
            :y2="(i + 1) * 36"
            stroke="rgba(255,255,255,0.04)"
            stroke-width="1"
          />
          <!-- Vertical time ticks -->
          <line
            v-for="tick in ticks"
            :key="'vt-' + tick.time.getTime()"
            :x1="tick.x"
            :y1="0"
            :x2="tick.x"
            :y2="timelineHeight"
            stroke="rgba(255,255,255,0.03)"
            stroke-width="1"
          />
        </svg>

        <!-- Agent lane labels -->
        <div
          v-for="(name, i) in visibleAgents"
          :key="'label-' + name"
          class="absolute left-1 text-[9px] font-medium truncate"
          :style="{ top: (i * 36 + 2) + 'px', color: getAgentColor(name), maxWidth: '120px' }"
        >{{ name }}</div>

        <!-- Events -->
        <template v-for="e in positionedEvents" :key="e.id">
          <div
            v-if="visibleAgents.includes(e.agent_name)"
            class="timeline-event"
            :style="{
              left: e.x + 'px',
              top: e.y + 'px',
              background: getAgentColor(e.agent_name),
              opacity: e.type === 'turn' ? 0.7 : 1,
              width: e.type === 'turn' ? '6px' : '10px',
              height: e.type === 'turn' ? '6px' : '10px',
              borderRadius: e.type === 'end' ? '50%' : '2px',
            }"
            :title="e.agent_name + ': ' + e.label"
            @click="onSelectSession(e.sessionId)"
          />
        </template>

        <!-- Time labels -->
        <div
          v-for="tick in ticks"
          :key="'tl-' + tick.time.getTime()"
          class="absolute text-[8px] text-text-tertiary"
          :style="{ left: (tick.x - 20) + 'px', bottom: '-16px', width: '40px', textAlign: 'center' }"
        >{{ tick.label }}</div>
      </div>
    </div>

    <!-- Empty state -->
    <div
      v-if="props.sessions.length === 0 && !props.loading"
      class="text-center py-8 text-text-tertiary text-xs"
    >
      No sessions yet. Start a chat to see it here.
    </div>
  </div>
</template>

<style scoped>
.timeline-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 2px 8px;
  border-radius: 6px;
  border: none;
  background: rgba(255,255,255,0.03);
  color: rgba(255,255,255,0.4);
  font-size: 11px;
  cursor: pointer;
  transition: all 0.2s;
}
.timeline-btn:hover {
  background: rgba(255,255,255,0.07);
  color: rgba(255,255,255,0.7);
}

.timeline-scroll {
  overflow-x: auto;
  overflow-y: hidden;
  position: relative;
  background: rgba(255,255,255,0.01);
}
.timeline-scroll::-webkit-scrollbar {
  height: 6px;
}
.timeline-scroll::-webkit-scrollbar-track {
  background: transparent;
}
.timeline-scroll::-webkit-scrollbar-thumb {
  background: rgba(255,255,255,0.06);
  border-radius: 3px;
}

.timeline-inner {
  position: relative;
  min-height: 80px;
  padding-bottom: 20px;
}

.timeline-event {
  position: absolute;
  cursor: pointer;
  transition: transform 0.15s, opacity 0.15s;
  z-index: 2;
}
.timeline-event:hover {
  transform: scale(1.5);
  opacity: 1 !important;
  z-index: 5;
}
</style>
