<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useAppStore } from '@/stores/app'
import type { Agent } from '@/stores/app'
import NavIsland from '@/components/NavIsland.vue'
import Sidebar from '@/components/Sidebar.vue'
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
import { toastBus } from '@/main'

const store = useAppStore()
const showCreate = ref(false)
const selectedAgent = ref<Agent | null>(null)
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
})

async function fetchHost() {
  try {
    const res = await fetch('/api/telemetry/host')
    if (res.ok) host.value = await res.json()
  } catch { /* optional */ }
}

function openDetail(agent: Agent) { selectedAgent.value = agent }
function closeDetail() { selectedAgent.value = null }

async function onCreateAgent(config: { name: string; model: string; tools: string[]; skills: string[] }) {
  const agent = await store.createAgent(config)
  if (agent) {
    selectedAgent.value = agent
  }
}
</script>

<template>
  <NavIsland />
  <div class="dashboard">
    <Sidebar />
    <main class="main">
      <!-- Header -->
      <div class="dash-header fade-up fade-up-d2">
        <div class="dash-title">
          <h1>Local operator overview</h1>
          <p>{{ store.agents.length }} agents · {{ store.onlineAgents }} online · {{ store.errorAgents }} alerts</p>
        </div>
        <div class="dash-actions gap-2">
          <router-link to="/flixz" class="btn btn-secondary" title="General frame extraction — no agent required">
            <span>🎞 Flixz</span>
          </router-link>
          <button type="button" class="btn btn-secondary" @click="showCreate = true">
            + New agent
          </button>
        </div>
      </div>

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
    </main>
  </div>
  <AgentDetail :agent="selectedAgent" @close="closeDetail" />
  <ResourceModal v-model:show="showCreate" @create="onCreateAgent" />
</template>

<style scoped>
.dashboard {
  display: flex;
  gap: 0;
  padding: 24px 32px 32px;
  margin-top: 8px;
  max-width: 1440px;
  margin-left: auto;
  margin-right: auto;
}
.main { flex: 1; min-width: 0; }
.dash-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}
.dash-title h1 {
  font-family: 'Clash Display', sans-serif;
  font-size: 26px;
  font-weight: 600;
  letter-spacing: -0.03em;
  color: #F0F0F2;
}
.dash-title p {
  font-size: 13px;
  color: rgba(255,255,255,0.3);
  font-weight: 500;
  margin-top: 2px;
}
.dash-actions { display: flex; gap: 8px; flex-wrap: wrap; }
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

.fade-up { opacity: 0; transform: translateY(16px); animation: fadeUp 0.7s cubic-bezier(0.32,0.72,0,1) forwards; }
.fade-up-d2 { animation-delay: 0.05s; }
.fade-up-d3 { animation-delay: 0.1s; }
.fade-up-d4 { animation-delay: 0.15s; }
.fade-up-d5 { animation-delay: 0.2s; }
.fade-up-d6 { animation-delay: 0.25s; }
.fade-up-d7 { animation-delay: 0.3s; }
.fade-up-d8 { animation-delay: 0.35s; }

@keyframes fadeUp { to { opacity: 1; transform: translateY(0); } }

@media (max-width: 968px) {
  .dashboard { padding: 16px; }
}
@media (max-width: 768px) {
  .dash-header { flex-direction: column; align-items: flex-start; gap: 12px; }
}
</style>
