<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useAppStore } from '@/stores/app'
import type { Agent } from '@/stores/app'
import AppShell from '@/components/AppShell.vue'
import PageHeader from '@/components/PageHeader.vue'
import StatCard from '@/components/StatCard.vue'
import AgentCard from '@/components/AgentCard.vue'
import AgentDetail from '@/components/AgentDetail.vue'
import ActivityFeed from '@/components/ActivityFeed.vue'
import OpsQueue from '@/components/OpsQueue.vue'
import ComsPanel from '@/components/ComsPanel.vue'
import TagCloud from '@/components/TagCloud.vue'
import SectionBar from '@/components/SectionBar.vue'
import CapacityMeter from '@/components/CapacityMeter.vue'
import ResourceModal from '@/components/ResourceModal.vue'

const store = useAppStore()
const showCreate = ref(false)
const selectedAgent = ref<Agent | null>(null)
const startTab = ref<string | undefined>(undefined)
const host = ref<{
  cpu?: { percent: number }
  memory?: { used_gb: number; total_gb: number; percent: number }
  disk?: { used_gb: number; total_gb: number; percent: number }
} | null>(null)

onMounted(() => {
  store.fetchAgents()
  store.fetchActivities()
  store.connectWebSocket()
  fetchHost()
  // Poll host meters so capacity stays live (matches HostTelemetry cadence)
  setInterval(fetchHost, 10000)
})

async function fetchHost() {
  try {
    const res = await fetch('/api/telemetry/host')
    if (res.ok) host.value = await res.json()
  } catch { /* optional */ }
}

function openDetail(agent: Agent, tab?: string) {
  selectedAgent.value = agent
  startTab.value = tab
}
function closeDetail() {
  selectedAgent.value = null
  startTab.value = undefined
}

async function onCreateAgent(config: { name: string; model: string; tools: string[]; skills: string[] }) {
  const agent = await store.createAgent(config)
  if (agent) {
    selectedAgent.value = agent
  }
}

// Command palette → open agent / create
watch(() => store.commandOpenAgentId, (id) => {
  if (!id) return
  const agent = store.agents.find(a => a.id === id)
  if (agent) {
    openDetail(agent, store.commandOpenTab || 'chat')
  }
  store.clearCommandOpenAgent()
})
watch(() => store.requestCreateAgent, (v) => {
  if (v) {
    showCreate.value = true
    store.clearRequestCreateAgent()
  }
})

function hintCommandPalette() {
  window.dispatchEvent(new CustomEvent('sop:open-command-palette'))
}
</script>

<template>
  <AppShell>
    <PageHeader
      title="Local operator overview"
      :subtitle="`${store.agents.length} agents · ${store.onlineAgents} online · ${store.errorAgents} alerts`"
    >
      <template #actions>
        <router-link to="/flixz" class="btn btn-secondary" title="General frame extraction — no agent required">
          <span>🎞 Flixz</span>
        </router-link>
        <button type="button" class="btn btn-secondary" @click="showCreate = true">
          + New agent
        </button>
        <button type="button" class="btn btn-ghost-cmd" title="Command palette (⌘K)" @click="hintCommandPalette">
          ⌘K
        </button>
      </template>
    </PageHeader>

    <!-- Capacity (D1) -->
    <div class="capacity-row fade-up fade-up-d3">
      <div class="capacity-card">
        <div class="capacity-card-title">Agents online</div>
        <CapacityMeter
          :used="store.onlineAgents"
          :total="Math.max(store.agents.length, 1)"
          label="online"
        />
      </div>
      <div v-if="host?.memory" class="capacity-card">
        <div class="capacity-card-title">Host RAM</div>
        <CapacityMeter
          :used="Math.round(host.memory.used_gb * 10) / 10"
          :total="Math.round(host.memory.total_gb * 10) / 10"
          label="GB"
        />
      </div>
      <div v-if="host?.disk" class="capacity-card">
        <div class="capacity-card-title">Host disk</div>
        <CapacityMeter
          :used="Math.round(host.disk.used_gb)"
          :total="Math.round(host.disk.total_gb)"
          label="GB"
        />
      </div>
      <div v-if="host?.cpu" class="capacity-card">
        <div class="capacity-card-title">Host CPU</div>
        <CapacityMeter
          :used="Math.round(host.cpu.percent)"
          :total="100"
          label="%"
        />
      </div>
    </div>

    <!-- Stats Row -->
    <div class="stats-row fade-up fade-up-d3">
      <StatCard label="Agents Online" :value="store.onlineAgents" :sub="`of ${store.agents.length} registered`" />
      <StatCard label="Busy now" :value="store.busyAgents" sub="concurrent sessions" />
      <StatCard label="Total Tokens" :value="store.agents.reduce((s, a) => s + a.tokens_used, 0).toLocaleString()" sub="cumulative" />
      <StatCard label="Connection" :value="store.connected ? 'Live' : '…'" sub="event bus" />
    </div>

    <!-- General Flixz entry -->
    <router-link to="/flixz" class="flixz-dash-card fade-up fade-up-d4">
      <div class="flixz-dash-icon">🎞</div>
      <div class="flixz-dash-copy">
        <div class="flixz-dash-title">Flixz — general frame extraction</div>
        <div class="flixz-dash-sub">
          Drop a path or URL, extract frames for analysis. Not tied to any agent.
          Local files: place under ~/.pi/flixz/input or set PI_FLIXZ_ALLOW_ROOTS.
        </div>
      </div>
      <span class="flixz-dash-cta">Open →</span>
    </router-link>

    <TagCloud class="fade-up fade-up-d5" />

    <SectionBar title="Your agents" class="fade-up fade-up-d6" />
    <div class="agent-grid fade-up fade-up-d7">
      <AgentCard
        v-for="agent in store.agents"
        :key="agent.id"
        :agent="agent"
        @click="openDetail(agent)"
      />
      <button
        v-if="store.agents.length === 0"
        type="button"
        class="agent-card header-card empty-cta"
        style="grid-column: 1 / -1;"
        @click="showCreate = true"
      >
        <div class="text-4xl mb-2 opacity-30">+</div>
        <div class="text-sm font-semibold text-text-secondary">Create your first local agent</div>
        <div class="text-xs text-text-tertiary mt-1">Opens create dialog — runs as a pi process on this machine</div>
      </button>
    </div>

    <div class="bottom-row fade-up fade-up-d8">
      <ActivityFeed :activities="store.activities" />
      <OpsQueue :agents="store.agents" />
      <ComsPanel />
    </div>
  </AppShell>
  <AgentDetail :agent="selectedAgent" :start-tab="startTab" @close="closeDetail" />
  <ResourceModal v-model:show="showCreate" @create="onCreateAgent" />
</template>

<style scoped>
.capacity-row {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}
.capacity-card {
  padding: 12px 14px;
  border-radius: 12px;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.06);
}
.capacity-card-title {
  font-size: 11px;
  font-weight: 600;
  color: rgba(255,255,255,0.4);
  margin-bottom: 8px;
}
.stats-row {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 12px;
  margin-bottom: 24px;
}
.agent-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
  margin-bottom: 24px;
}
.header-card {
  background: rgba(157,213,34,0.06);
  border-color: rgba(157,213,34,0.12);
  min-height: 120px;
}
.empty-cta {
  border: 1px dashed rgba(157,213,34,0.25);
  cursor: pointer;
  width: 100%;
  font: inherit;
  color: inherit;
}
.empty-cta:hover {
  background: rgba(157,213,34,0.1);
}
.bottom-row {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
}
.btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 18px;
  border-radius: 12px;
  font-size: 12.5px;
  font-weight: 500;
  font-family: inherit;
  border: none;
  text-decoration: none;
  cursor: pointer;
  transition: all 0.4s cubic-bezier(0.32,0.72,0,1);
}
.btn-secondary {
  background: rgba(255, 255, 255, 0.06);
  color: rgba(240, 240, 242, 0.85);
  border: 1px solid rgba(255, 255, 255, 0.08);
}
.btn-secondary:hover {
  background: rgba(157, 213, 34, 0.12);
  border-color: rgba(157, 213, 34, 0.25);
  color: #D3ED2F;
}
.btn-ghost-cmd {
  background: transparent;
  color: rgba(233, 236, 224, 0.4);
  border: 1px solid rgba(233, 236, 224, 0.1);
  padding: 8px 12px;
  font-size: 11px;
  font-family: 'JetBrains Mono', monospace;
}
.btn-ghost-cmd:hover {
  color: #9DD522;
  border-color: rgba(157, 213, 34, 0.3);
}
.flixz-dash-card {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
  padding: 16px 18px;
  border-radius: 14px;
  text-decoration: none;
  background: linear-gradient(135deg, rgba(157, 213, 34, 0.08), rgba(18, 26, 17, 0.6));
  border: 1px solid rgba(157, 213, 34, 0.18);
  transition: border-color 0.25s ease, transform 0.25s ease;
}
.flixz-dash-card:hover {
  border-color: rgba(157, 213, 34, 0.4);
  transform: translateY(-1px);
}
.flixz-dash-icon { font-size: 28px; line-height: 1; flex-shrink: 0; }
.flixz-dash-copy { flex: 1; min-width: 0; }
.flixz-dash-title {
  font-size: 14px;
  font-weight: 600;
  color: #E9ECE0;
  margin-bottom: 4px;
}
.flixz-dash-sub {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.35);
  line-height: 1.4;
}
.flixz-dash-cta {
  font-size: 12px;
  font-weight: 600;
  color: #9DD522;
  flex-shrink: 0;
}
</style>
