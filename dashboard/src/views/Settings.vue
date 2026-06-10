<script setup lang="ts">
import { onMounted, ref } from 'vue'
import NavIsland from '@/components/NavIsland.vue'
import Sidebar from '@/components/Sidebar.vue'

const health = ref<Record<string, any>>({})

onMounted(async () => {
  try {
    const res = await fetch('/api/health')
    health.value = await res.json()
  } catch (e) { /* ignore */ }
})
</script>

<template>
  <NavIsland />
  <div class="dashboard">
    <Sidebar />
    <main class="main">
      <div class="dash-header">
        <div class="dash-title">
          <h1>Settings</h1>
          <p>Orchestrator status</p>
        </div>
      </div>

      <div class="grid grid-cols-2 gap-3">
        <div class="card p-5">
          <h3 class="font-semibold text-sm text-text-primary mb-3">System</h3>
          <div class="space-y-2 text-xs">
            <div class="flex justify-between"><span class="text-text-tertiary">Version</span><span class="text-text-secondary">{{ health.version || '-' }}</span></div>
            <div class="flex justify-between"><span class="text-text-tertiary">Status</span><span class="text-success">{{ health.status || '-' }}</span></div>
            <div class="flex justify-between"><span class="text-text-tertiary">Agents</span><span class="text-text-secondary">{{ health.agent_count ?? '-' }}</span></div>
            <div class="flex justify-between"><span class="text-text-tertiary">Active Sessions</span><span class="text-text-secondary">{{ health.active_session_count ?? '-' }}</span></div>
          </div>
        </div>
        <div class="card p-5">
          <h3 class="font-semibold text-sm text-text-primary mb-3">Paths</h3>
          <div class="space-y-2 text-[10px] font-mono text-text-muted break-all">
            <div>~/.pi/agent/orchestrator.db</div>
            <div>~/.pi/agent/sessions/managed/</div>
            <div>~/.pi/agent/skills/</div>
            <div>~/.pi/agent/extensions/</div>
            <div>~/.pi/agent/agents/</div>
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
