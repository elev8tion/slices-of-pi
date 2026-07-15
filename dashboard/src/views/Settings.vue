<script setup lang="ts">
import { onMounted, ref } from 'vue'
import NavIsland from '@/components/NavIsland.vue'
import Sidebar from '@/components/Sidebar.vue'
import McpKeysPanel from '@/components/McpKeysPanel.vue'
import SlicesPanel from '@/components/SlicesPanel.vue'

const health = ref<Record<string, any>>({})
const activeSection = ref<'status' | 'ops' | 'mcp'>('status')

onMounted(async () => {
  try {
    const res = await fetch('/health')
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
          <p>Orchestrator status, fleet ops, MCP keys</p>
        </div>
      </div>

      <div class="settings-tabs">
        <button
          class="settings-tab"
          :class="{ active: activeSection === 'status' }"
          @click="activeSection = 'status'"
        >Status</button>
        <button
          class="settings-tab"
          :class="{ active: activeSection === 'ops' }"
          @click="activeSection = 'ops'"
        >Slice Ops</button>
        <button
          class="settings-tab"
          :class="{ active: activeSection === 'mcp' }"
          @click="activeSection = 'mcp'"
        >MCP Keys</button>
      </div>

      <div v-if="activeSection === 'status'" class="grid grid-cols-2 gap-3">
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
            <div>~/.pi/agents/</div>
            <div>~/.pi/flixz/input/</div>
          </div>
        </div>
        <div class="card p-5 col-span-2">
          <h3 class="font-semibold text-sm text-text-primary mb-2">Product packages</h3>
          <p class="text-xs text-text-tertiary leading-relaxed">
            <strong class="text-text-secondary">Runnable product:</strong> <code>pi_orchestrator</code> + <code>dashboard</code>
            (local single-operator). <strong class="text-text-secondary">Contracts package:</strong>
            <code>slice_of_pi</code> is abstract ABCs only and is not imported by the orchestrator.
            See AGENTS.md and docs/PRODUCT_INTENT.md.
          </p>
        </div>
      </div>

      <div v-else-if="activeSection === 'ops'" class="settings-panel">
        <SlicesPanel />
      </div>

      <div v-else class="settings-panel">
        <McpKeysPanel />
      </div>
    </main>
  </div>
</template>

<style scoped>
.dashboard { display: flex; gap: 0; padding: 24px 32px 32px; margin-top: 8px; max-width: 1440px; margin-left: auto; margin-right: auto; }
.main { flex: 1; min-width: 0; }
.dash-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; }
.dash-title h1 { font-family: 'Clash Display', sans-serif; font-size: 26px; font-weight: 600; letter-spacing: -0.03em; color: #F0F0F2; }
.dash-title p { font-size: 13px; color: rgba(255,255,255,0.3); font-weight: 500; margin-top: 2px; }
.settings-tabs { display: flex; gap: 8px; margin-bottom: 16px; }
.settings-tab {
  padding: 8px 14px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 500;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.06);
  color: rgba(255,255,255,0.45);
  cursor: pointer;
}
.settings-tab.active {
  background: rgba(157,213,34,0.12);
  border-color: rgba(157,213,34,0.28);
  color: #D3ED2F;
}
.settings-panel {
  background: rgba(18,26,17,0.4);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 14px;
  padding: 12px;
  min-height: 280px;
}
.col-span-2 { grid-column: 1 / -1; }
code { font-size: 11px; color: rgba(211,237,47,0.85); }
</style>
