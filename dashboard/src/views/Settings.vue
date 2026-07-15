<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import NavIsland from '@/components/NavIsland.vue'
import Sidebar from '@/components/Sidebar.vue'
import McpKeysPanel from '@/components/McpKeysPanel.vue'
import SlicesPanel from '@/components/SlicesPanel.vue'
import CapacityMeter from '@/components/CapacityMeter.vue'
import YamlEditor from '@/components/YamlEditor.vue'
import { toastBus } from '@/main'

const health = ref<Record<string, any>>({})
const host = ref<{
  cpu?: { percent: number }
  memory?: { used_gb: number; total_gb: number }
  disk?: { used_gb: number; total_gb: number }
} | null>(null)
const activeSection = ref<'status' | 'ops' | 'mcp' | 'config'>('status')

const configText = ref('')
const configPath = ref('')
const configLoading = ref(false)
const configSaving = ref(false)

onMounted(async () => {
  try {
    const res = await fetch('/health')
    health.value = await res.json()
  } catch { /* ignore */ }
  try {
    const res = await fetch('/api/telemetry/host')
    if (res.ok) host.value = await res.json()
  } catch { /* ignore */ }
})

watch(activeSection, async (s) => {
  if (s === 'config' && !configText.value) {
    await loadOrchestratorConfig()
  }
})

async function loadOrchestratorConfig() {
  configLoading.value = true
  try {
    const res = await fetch('/api/settings/orchestrator-config')
    if (!res.ok) throw new Error('Failed to load')
    const data = await res.json()
    configText.value = data.text || JSON.stringify(data.config || {}, null, 2)
    configPath.value = data.path || '~/.pi/agent/orchestrator.json'
  } catch {
    toastBus.error('Could not load orchestrator config')
  } finally {
    configLoading.value = false
  }
}

async function saveOrchestratorConfig() {
  configSaving.value = true
  try {
    let parsed: Record<string, unknown>
    try {
      parsed = JSON.parse(configText.value)
    } catch {
      toastBus.error('Invalid JSON — fix syntax before save')
      return
    }
    if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
      toastBus.error('Config must be a JSON object')
      return
    }
    const res = await fetch('/api/settings/orchestrator-config', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ config: parsed }),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Save failed')
    }
    toastBus.success('Saved local orchestrator config')
    await loadOrchestratorConfig()
  } catch (e: any) {
    toastBus.error(e.message || 'Save failed')
  } finally {
    configSaving.value = false
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
          <h1>Settings</h1>
          <p>Local operator status, ops, MCP keys, config</p>
        </div>
      </div>

      <div class="settings-tabs">
        <button class="settings-tab" :class="{ active: activeSection === 'status' }" @click="activeSection = 'status'">Status</button>
        <button class="settings-tab" :class="{ active: activeSection === 'ops' }" @click="activeSection = 'ops'">Slice Ops</button>
        <button class="settings-tab" :class="{ active: activeSection === 'mcp' }" @click="activeSection = 'mcp'">MCP Keys</button>
        <button class="settings-tab" :class="{ active: activeSection === 'config' }" @click="activeSection = 'config'">Config</button>
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
            <div>~/.pi/agent/orchestrator.json</div>
            <div>~/.pi/agent/sessions/managed/</div>
            <div>~/.pi/agent/skills/</div>
            <div>~/.pi/flixz/input/</div>
          </div>
        </div>

        <div v-if="host" class="card p-5 col-span-2">
          <h3 class="font-semibold text-sm text-text-primary mb-3">This machine</h3>
          <div class="host-meters">
            <div v-if="host.memory">
              <div class="meter-label">RAM</div>
              <CapacityMeter
                :used="Math.round((host.memory.used_gb || 0) * 10) / 10"
                :total="Math.round((host.memory.total_gb || 1) * 10) / 10"
                label="GB"
              />
            </div>
            <div v-if="host.disk">
              <div class="meter-label">Disk</div>
              <CapacityMeter
                :used="Math.round(host.disk.used_gb || 0)"
                :total="Math.round(host.disk.total_gb || 1)"
                label="GB"
              />
            </div>
            <div v-if="host.cpu">
              <div class="meter-label">CPU</div>
              <CapacityMeter :used="Math.round(host.cpu.percent || 0)" :total="100" label="%" />
            </div>
          </div>
        </div>

        <div class="card p-5 col-span-2">
          <h3 class="font-semibold text-sm text-text-primary mb-2">Product packages</h3>
          <p class="text-xs text-text-tertiary leading-relaxed">
            <strong class="text-text-secondary">Runnable product:</strong> <code>pi_orchestrator</code> + <code>dashboard</code>
            (local single-operator). <strong class="text-text-secondary">Contracts package:</strong>
            <code>slice_of_pi</code> is abstract ABCs only and is not imported by the orchestrator.
          </p>
        </div>
      </div>

      <div v-else-if="activeSection === 'ops'" class="settings-panel">
        <SlicesPanel />
      </div>

      <div v-else-if="activeSection === 'mcp'" class="settings-panel">
        <McpKeysPanel />
      </div>

      <div v-else class="settings-panel config-panel">
        <div class="config-header">
          <div>
            <h3 class="font-semibold text-sm text-text-primary">orchestrator.json</h3>
            <p class="text-[11px] text-text-tertiary mt-1">
              Local profiles only — fixed path <code>{{ configPath || '~/.pi/agent/orchestrator.json' }}</code>.
              Edit as JSON (YamlEditor UI). No cloud sync.
            </p>
          </div>
          <div class="config-actions">
            <button type="button" class="settings-tab" :disabled="configLoading" @click="loadOrchestratorConfig">Reload</button>
            <button type="button" class="settings-tab active" :disabled="configSaving" @click="saveOrchestratorConfig">
              {{ configSaving ? 'Saving…' : 'Save' }}
            </button>
          </div>
        </div>
        <div v-if="configLoading" class="text-xs text-text-tertiary py-8 text-center">Loading…</div>
        <YamlEditor v-else v-model="configText" filename="orchestrator.json" />
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
.settings-tabs { display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }
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
.settings-tab:disabled { opacity: 0.5; cursor: not-allowed; }
.settings-panel {
  background: rgba(18,26,17,0.4);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 14px;
  padding: 12px;
  min-height: 280px;
}
.config-panel { padding: 16px; }
.config-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.config-actions { display: flex; gap: 8px; }
.host-meters {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 16px;
}
.meter-label {
  font-size: 11px;
  font-weight: 600;
  color: rgba(255,255,255,0.4);
  margin-bottom: 6px;
}
.col-span-2 { grid-column: 1 / -1; }
code { font-size: 11px; color: rgba(211,237,47,0.85); }
</style>
