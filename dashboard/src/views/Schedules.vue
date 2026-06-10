<script setup lang="ts">
import { onMounted, ref } from 'vue'
import NavIsland from '@/components/NavIsland.vue'
import Sidebar from '@/components/Sidebar.vue'

interface Schedule {
  id: string
  agent_id: string
  agent_name?: string
  cron_expression: string
  message: string
  enabled: boolean
  model?: string
  last_run_at?: string
  next_run_at?: string
  created_at: string
}

const schedules = ref<Schedule[]>([])
const loading = ref(true)

onMounted(async () => {
  await loadSchedules()
})

async function loadSchedules() {
  try {
    const res = await fetch('/api/schedules')
    schedules.value = await res.json()
  } catch (e) {
    console.error('Failed to load schedules', e)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <NavIsland />
  <div class="dashboard">
    <Sidebar />
    <main class="main">
      <div class="dash-header">
        <div class="dash-title">
          <h1>Schedules</h1>
          <p>{{ schedules.length }} configured</p>
        </div>
      </div>

      <div v-if="loading" class="card p-8 text-center text-text-tertiary text-sm">Loading...</div>

      <div v-else-if="schedules.length === 0" class="card p-8 text-center text-text-tertiary text-sm">
        No schedules configured. Create one via the API.
      </div>

      <div v-else class="grid grid-cols-2 gap-3">
        <div v-for="s in schedules" :key="s.id" class="card p-5">
          <div class="flex items-center justify-between mb-2">
            <h3 class="font-semibold text-sm text-text-primary">{{ s.agent_name || s.agent_id.slice(0,8) }}</h3>
            <span class="text-[10px] font-semibold px-2 py-0.5 rounded-full" :class="s.enabled ? 'bg-success/10 text-success border border-success/15' : 'bg-white/5 text-text-tertiary'">
              {{ s.enabled ? 'Active' : 'Paused' }}
            </span>
          </div>
          <code class="text-xs text-accent font-mono">{{ s.cron_expression }}</code>
          <p class="text-xs text-text-tertiary mt-2 mb-2 line-clamp-2">{{ s.message }}</p>
          <div class="flex gap-3 text-[10px] text-text-muted">
            <span v-if="s.model">Model: {{ s.model }}</span>
            <span v-if="s.last_run_at">Last: {{ new Date(s.last_run_at).toLocaleString() }}</span>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.dashboard { display: flex; gap: 0; padding: 24px 32px 32px; margin-top: 8px; max-width: 1440px; margin-left: auto; margin-right: auto; }
.main { flex: 1; min-width: 0; }
.dash-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px; }
.dash-title h1 { font-family: 'Clash Display', sans-serif; font-size: 26px; font-weight: 600; letter-spacing: -0.03em; color: #F0F0F2; }
.dash-title p { font-size: 13px; color: rgba(255,255,255,0.3); font-weight: 500; margin-top: 2px; }
</style>
