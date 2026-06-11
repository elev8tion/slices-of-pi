<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import SparklineChart from './SparklineChart.vue'

interface HostStats {
  cpu: { percent: number }
  memory: { total_gb?: number; used_gb?: number; percent: number }
  disk: { total_gb?: number; used_gb?: number; percent: number }
}

const MAX_POINTS = 30
const stats = ref<HostStats | null>(null)
const cpuHistory = ref<(number | null)[]>(Array(MAX_POINTS).fill(null))
const memHistory = ref<(number | null)[]>(Array(MAX_POINTS).fill(null))
const loading = ref(true)
let interval: ReturnType<typeof setInterval> | null = null

const cpuColor = computed(() => {
  const p = stats.value?.cpu?.percent ?? 0
  if (p > 80) return '#EF4444'
  if (p > 50) return '#F59E0B'
  return '#22C55E'
})

const memColor = computed(() => {
  const p = stats.value?.memory?.percent ?? 0
  if (p > 80) return '#EF4444'
  if (p > 50) return '#F59E0B'
  return '#22C55E'
})

async function fetchStats() {
  try {
    const res = await fetch('/api/telemetry/host')
    if (!res.ok) return
    const data: HostStats = await res.json()
    stats.value = data

    cpuHistory.value.push(data.cpu.percent)
    memHistory.value.push(data.memory.percent)
    if (cpuHistory.value.length > MAX_POINTS) cpuHistory.value.shift()
    if (memHistory.value.length > MAX_POINTS) memHistory.value.shift()
    loading.value = false
  } catch {
    // Silent
  }
}

function formatPercent(pct: number | undefined): string {
  return (pct ?? 0).toFixed(0)
}

function formatMemory(gb: number | undefined): string {
  return (gb ?? 0).toFixed(1)
}

onMounted(() => {
  fetchStats()
  interval = setInterval(fetchStats, 5000)
})

onUnmounted(() => {
  if (interval) clearInterval(interval)
})
</script>

<template>
  <div class="host-telemetry" :class="{ loading }">
    <!-- CPU -->
    <div class="metric">
      <div class="metric-header">
        <span class="metric-label">CPU</span>
        <span class="metric-value" :style="{ color: cpuColor }">{{ formatPercent(stats?.cpu?.percent) }}%</span>
      </div>
      <SparklineChart :data="cpuHistory" :color="cpuColor" :height="20" />
    </div>

    <!-- Memory -->
    <div class="metric">
      <div class="metric-header">
        <span class="metric-label">RAM</span>
        <span class="metric-value" :style="{ color: memColor }">
          {{ formatMemory(stats?.memory?.used_gb) }}/{{ formatMemory(stats?.memory?.total_gb) }}G
        </span>
      </div>
      <SparklineChart :data="memHistory" :color="memColor" :height="20" />
    </div>

    <!-- Disk -->
    <div class="metric metric-disk" title="Disk usage on home partition">
      <div class="metric-header">
        <span class="metric-label">Disk</span>
        <span class="metric-value">{{ formatPercent(stats?.disk?.percent) }}%</span>
      </div>
      <div class="disk-bar-track">
        <div class="disk-bar-fill" :style="{ width: formatPercent(stats?.disk?.percent) + '%' }" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.host-telemetry {
  display: flex;
  align-items: center;
  gap: 16px;
}
.metric {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 80px;
}
.metric-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
}
.metric-label {
  font-size: 10px;
  font-weight: 600;
  color: rgba(255,255,255,0.3);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.metric-value {
  font-size: 11px;
  font-weight: 600;
  color: rgba(255,255,255,0.5);
  font-variant-numeric: tabular-nums;
}
.metric-disk {
  min-width: 60px;
}
.disk-bar-track {
  width: 100%;
  height: 3px;
  background: rgba(255,255,255,0.06);
  border-radius: 2px;
  overflow: hidden;
}
.disk-bar-fill {
  height: 100%;
  background: rgba(255,255,255,0.25);
  border-radius: 2px;
  transition: width 1s ease;
}
.loading {
  opacity: 0.4;
}
</style>
