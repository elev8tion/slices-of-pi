<script setup lang="ts">
import { ref, onMounted } from 'vue'
import NavIsland from '@/components/NavIsland.vue'
import Sidebar from '@/components/Sidebar.vue'
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
  <NavIsland />
  <div class="ops-page">
    <Sidebar />
    <main class="main">
      <!-- Header -->
      <div class="ops-header fade-up">
        <div class="ops-title">
          <h1>Operator Room</h1>
          <p>Items requiring your attention</p>
        </div>
      </div>

      <!-- Stats bar -->
      <div class="ops-stats fade-up fade-up-d2">
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

      <!-- Queue -->
      <div class="ops-queue fade-up fade-up-d3">
        <OperatorQueue />
      </div>
    </main>
  </div>
</template>

<style scoped>
.ops-page {
  display: flex;
  gap: 0;
  padding: 24px 32px 32px;
  margin-top: 8px;
  max-width: 1440px;
  margin-left: auto;
  margin-right: auto;
  height: calc(100vh - 60px);
}
.main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.ops-header {
  margin-bottom: 16px;
}
.ops-title h1 {
  font-family: 'Clash Display', sans-serif;
  font-size: 26px;
  font-weight: 600;
  letter-spacing: -0.03em;
  color: #F0F0F2;
}
.ops-title p {
  font-size: 13px;
  color: rgba(255,255,255,0.3);
  font-weight: 500;
  margin-top: 2px;
}
.ops-stats {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
}
.ops-stat {
  flex: 1;
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.04);
  border-radius: 12px;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.ops-stat-value {
  font-size: 22px;
  font-weight: 700;
  font-family: 'Clash Display', sans-serif;
  letter-spacing: -0.03em;
  color: #F0F0F2;
}
.ops-stat-label {
  font-size: 10.5px;
  font-weight: 500;
  color: rgba(255,255,255,0.3);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.ops-queue {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}

.fade-up {
  opacity: 0;
  transform: translateY(16px);
  animation: fadeUp 0.7s cubic-bezier(0.32,0.72,0,1) forwards;
}
.fade-up-d2 { animation-delay: 0.1s; }
.fade-up-d3 { animation-delay: 0.2s; }
@keyframes fadeUp {
  to { opacity: 1; transform: translateY(0); }
}

@media (max-width: 968px) {
  .ops-page {
    padding: 16px;
    flex-direction: column;
    height: auto;
  }
  .ops-stats { flex-wrap: wrap; }
  .ops-stat { min-width: calc(33% - 8px); }
}
</style>
