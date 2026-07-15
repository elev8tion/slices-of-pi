<script setup lang="ts">
import { ref, onMounted } from 'vue'
import AppShell from '@/components/AppShell.vue'
import PageHeader from '@/components/PageHeader.vue'
import OperatorQueue from '@/components/OperatorQueue.vue'

interface QueueStats {
  pending: number
  acknowledged: number
  resolved: number
  rejected: number
  total: number
}

const stats = ref<QueueStats>({ pending: 0, acknowledged: 0, resolved: 0, rejected: 0, total: 0 })
const loading = ref(true)

async function fetchStats() {
  try {
    const res = await fetch('/api/operator-queue/stats')
    stats.value = await res.json()
  } catch {
    // Silent
  } finally {
    loading.value = false
  }
}

onMounted(fetchStats)
</script>

<template>
  <AppShell>
    <div class="ops-inner">
      <PageHeader title="Operator Room" subtitle="Items requiring your attention" />

      <div class="ops-stats fade-up fade-up-d3">
        <div class="ops-stat">
          <span class="ops-stat-value" style="color:#F59E0B">{{ stats.pending }}</span>
          <span class="ops-stat-label">Pending</span>
        </div>
        <div class="ops-stat">
          <span class="ops-stat-value" style="color:#9DD522">{{ stats.acknowledged }}</span>
          <span class="ops-stat-label">Acknowledged</span>
        </div>
        <div class="ops-stat">
          <span class="ops-stat-value" style="color:#22C55E">{{ stats.resolved }}</span>
          <span class="ops-stat-label">Resolved</span>
        </div>
        <div class="ops-stat">
          <span class="ops-stat-value" style="color:#EF4444">{{ stats.rejected }}</span>
          <span class="ops-stat-label">Rejected</span>
        </div>
        <div class="ops-stat">
          <span class="ops-stat-value">{{ stats.total }}</span>
          <span class="ops-stat-label">Total</span>
        </div>
      </div>

      <div class="ops-queue fade-up fade-up-d4">
        <OperatorQueue />
      </div>
    </div>
  </AppShell>
</template>

<style scoped>
.ops-inner {
  display: flex;
  flex-direction: column;
  min-height: calc(100vh - 100px);
}
.ops-stats {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.ops-stat {
  flex: 1;
  min-width: 100px;
  padding: 14px 16px;
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.05);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.ops-stat-value {
  font-size: 24px;
  font-weight: 600;
  letter-spacing: -0.03em;
  color: #E9ECE0;
}
.ops-stat-label {
  font-size: 11px;
  font-weight: 500;
  color: rgba(255,255,255,0.3);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.ops-queue {
  flex: 1;
  min-height: 0;
}
</style>
