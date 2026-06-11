<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { toastBus } from '@/main'

interface SlicesStatus {
  total_agents: number
  running_sessions: number
  agents_by_status: Record<string, number>
  scheduler_running: boolean
  uptime_hours: number
}

const status = ref<SlicesStatus | null>(null)
const loading = ref(true)
const error = ref('')
const actionLoading = ref<'stop' | 'restart' | 'emergency' | null>(null)
const showConfirm = ref<'stop' | 'restart' | 'emergency' | null>(null)
const schedulerLoading = ref(false)

const statusColors: Record<string, string> = {
  idle: '#22C55E',
  busy: '#9DD522',
  error: '#EF4444',
  created: '#6B7280',
  stopped: '#6B7280',
}

onMounted(async () => {
  await fetchStatus()
})

async function fetchStatus() {
  loading.value = true
  error.value = ''
  try {
    const res = await fetch('/api/ops/status')
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    status.value = await res.json()
  } catch (e: any) {
    error.value = e.message || 'Failed to load slice status'
  } finally {
    loading.value = false
  }
}

async function stopAll() {
  actionLoading.value = 'stop'
  showConfirm.value = null
  try {
    const res = await fetch('/api/ops/agents/stop-all', { method: 'POST' })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    toastBus.success(`Stopped ${data.stopped} running sessions`)
    await fetchStatus()
  } catch (e: any) {
    toastBus.error(`Stop failed: ${e.message}`)
  } finally {
    actionLoading.value = null
  }
}

async function restartAll() {
  actionLoading.value = 'restart'
  showConfirm.value = null
  try {
    const res = await fetch('/api/ops/agents/restart-all', { method: 'POST' })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    toastBus.success(`Restarted ${data.restarted} agents`)
    await fetchStatus()
  } catch (e: any) {
    toastBus.error(`Restart failed: ${e.message}`)
  } finally {
    actionLoading.value = null
  }
}

async function emergencyStop() {
  actionLoading.value = 'emergency'
  showConfirm.value = null
  try {
    const res = await fetch('/api/ops/agents/stop-all', { method: 'POST' })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    toastBus.success(`Emergency stop complete — ${data.stopped} sessions killed`)
    await fetchStatus()
  } catch (e: any) {
    toastBus.error(`Emergency stop failed: ${e.message}`)
  } finally {
    actionLoading.value = null
  }
}

async function toggleScheduler() {
  if (!status.value) return
  schedulerLoading.value = true
  try {
    const endpoint = status.value.scheduler_running ? '/api/ops/scheduler/pause' : '/api/ops/scheduler/resume'
    const res = await fetch(endpoint, { method: 'POST' })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    toastBus.success(`Scheduler ${data.status}`)
    status.value.scheduler_running = data.status === 'resumed'
  } catch (e: any) {
    toastBus.error(`Scheduler toggle failed: ${e.message}`)
  } finally {
    schedulerLoading.value = false
  }
}
</script>

<template>
  <div class="space-y-4">
    <!-- Loading -->
    <div v-if="loading && !status" class="card p-6 text-center text-text-tertiary text-sm">
      <div class="animate-pulse">Loading slice status...</div>
    </div>

    <!-- Error -->
    <div v-else-if="error && !status" class="card p-6 text-center">
      <div class="text-danger text-sm mb-2">{{ error }}</div>
      <button @click="fetchStatus" class="text-xs font-medium px-3 py-1.5 rounded-btn bg-accent/10 text-accent border border-accent/20 hover:bg-accent/20 transition-all">
        Retry
      </button>
    </div>

    <!-- Slice status -->
    <template v-else-if="status">
      <!-- Status cards row -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div class="card p-4">
          <div class="text-[10px] font-semibold text-text-tertiary uppercase tracking-wider mb-1">Total Agents</div>
          <div class="text-2xl font-bold text-text-primary">{{ status.total_agents }}</div>
        </div>
        <div class="card p-4">
          <div class="text-[10px] font-semibold text-text-tertiary uppercase tracking-wider mb-1">Running Sessions</div>
          <div class="text-2xl font-bold text-text-primary">{{ status.running_sessions }}</div>
        </div>
        <div class="card p-4">
          <div class="text-[10px] font-semibold text-text-tertiary uppercase tracking-wider mb-1">Uptime</div>
          <div class="text-2xl font-bold text-text-primary">{{ status.uptime_hours }}h</div>
        </div>
        <div class="card p-4">
          <div class="text-[10px] font-semibold text-text-tertiary uppercase tracking-wider mb-1">Scheduler</div>
          <div class="flex items-center gap-2">
            <div class="text-2xl font-bold" :class="status.scheduler_running ? 'text-success' : 'text-text-muted'">
              {{ status.scheduler_running ? 'Active' : 'Paused' }}
            </div>
          </div>
        </div>
      </div>

      <!-- By-status breakdown -->
      <div class="card p-4">
        <h3 class="text-[11px] font-semibold text-text-tertiary uppercase tracking-wider mb-3">Agents by Status</h3>
        <div class="flex flex-wrap gap-4">
          <div v-for="(count, s) in status.agents_by_status" :key="s" class="flex items-center gap-2">
            <span class="w-2 h-2 rounded-full" :style="{ background: statusColors[s] || '#6B7280' }" />
            <span class="text-xs capitalize text-text-secondary">{{ s }}</span>
            <span class="text-xs font-semibold text-text-primary">{{ count }}</span>
          </div>
          <div v-if="Object.keys(status.agents_by_status).length === 0" class="text-xs text-text-tertiary">
            No agents registered
          </div>
        </div>
      </div>

      <!-- Actions -->
      <div class="card p-4">
        <h3 class="text-[11px] font-semibold text-text-tertiary uppercase tracking-wider mb-3">Slice Operations</h3>
        <div class="flex flex-wrap gap-2">

          <!-- Stop All -->
          <div class="relative">
            <button
              v-if="showConfirm !== 'stop'"
              @click="showConfirm = 'stop'"
              :disabled="actionLoading !== null"
              class="text-xs font-medium px-4 py-2 rounded-btn bg-amber-500/10 text-amber-400 border border-amber-500/20 hover:bg-amber-500/20 transition-all disabled:opacity-30"
            >
              <span v-if="actionLoading === 'stop'" class="inline-block animate-spin mr-1.5">⟳</span>
              Stop All
            </button>
            <div v-else class="flex items-center gap-2 p-2 rounded-btn bg-amber-500/10 border border-amber-500/20">
              <span class="text-[11px] text-amber-400/80">Stop all sessions?</span>
              <button @click="stopAll" :disabled="actionLoading === 'stop'"
                class="text-[10px] font-semibold px-2 py-1 rounded bg-amber-500 text-white hover:bg-amber-600 transition-all">Yes</button>
              <button @click="showConfirm = null"
                class="text-[10px] px-2 py-1 rounded bg-white/5 text-text-tertiary hover:text-text-secondary transition-all">No</button>
            </div>
          </div>

          <!-- Restart All -->
          <div class="relative">
            <button
              v-if="showConfirm !== 'restart'"
              @click="showConfirm = 'restart'"
              :disabled="actionLoading !== null"
              class="text-xs font-medium px-4 py-2 rounded-btn bg-accent/10 text-accent border border-accent/20 hover:bg-accent/20 transition-all disabled:opacity-30"
            >
              <span v-if="actionLoading === 'restart'" class="inline-block animate-spin mr-1.5">⟳</span>
              Restart All
            </button>
            <div v-else class="flex items-center gap-2 p-2 rounded-btn bg-accent/10 border border-accent/20">
              <span class="text-[11px] text-accent/80">Restart all agents?</span>
              <button @click="restartAll" :disabled="actionLoading === 'restart'"
                class="text-[10px] font-semibold px-2 py-1 rounded bg-accent text-white hover:bg-accent-hover transition-all">Yes</button>
              <button @click="showConfirm = null"
                class="text-[10px] px-2 py-1 rounded bg-white/5 text-text-tertiary hover:text-text-secondary transition-all">No</button>
            </div>
          </div>

          <!-- Emergency Stop -->
          <div class="relative">
            <button
              v-if="showConfirm !== 'emergency'"
              @click="showConfirm = 'emergency'"
              :disabled="actionLoading !== null"
              class="text-xs font-medium px-4 py-2 rounded-btn bg-danger/10 text-danger border border-danger/20 hover:bg-danger/20 transition-all disabled:opacity-30"
            >
              <span v-if="actionLoading === 'emergency'" class="inline-block animate-spin mr-1.5">⟳</span>
              Emergency Stop
            </button>
            <div v-else class="flex items-center gap-2 p-2 rounded-btn bg-danger/10 border border-danger/20">
              <span class="text-[11px] text-danger/80">Force-stop all pi processes?</span>
              <button @click="emergencyStop" :disabled="actionLoading === 'emergency'"
                class="text-[10px] font-semibold px-2 py-1 rounded bg-danger text-white hover:bg-red-700 transition-all">Yes</button>
              <button @click="showConfirm = null"
                class="text-[10px] px-2 py-1 rounded bg-white/5 text-text-tertiary hover:text-text-secondary transition-all">No</button>
            </div>
          </div>

          <!-- Scheduler Toggle -->
          <button
            @click="toggleScheduler"
            :disabled="schedulerLoading"
            class="text-xs font-medium px-4 py-2 rounded-btn bg-white/4 text-text-tertiary border border-white/8 hover:text-text-secondary hover:bg-white/8 transition-all disabled:opacity-30"
          >
            <span v-if="schedulerLoading" class="inline-block animate-spin mr-1.5">⟳</span>
            {{ status.scheduler_running ? 'Pause Scheduler' : 'Resume Scheduler' }}
          </button>

        </div>
      </div>
    </template>
  </div>
</template>
