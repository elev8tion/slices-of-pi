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

const store = useAppStore()

onMounted(() => {
  store.fetchAgents()
  store.fetchActivities()
  store.connectWebSocket()
})

const selectedAgent = ref<Agent | null>(null)
function openDetail(agent: Agent) { selectedAgent.value = agent }
function closeDetail() { selectedAgent.value = null }
</script>

<template>
  <NavIsland />
  <div class="dashboard">
    <Sidebar />
    <main class="main">
      <!-- Header -->
      <div class="dash-header fade-up fade-up-d2">
        <div class="dash-title">
          <h1>Slices Overview</h1>
          <p>{{ store.agents.length }} agents &middot; {{ store.onlineAgents }} online &middot; {{ store.errorAgents }} alerts</p>
        </div>
        <div class="dash-actions gap-2">
          <router-link to="/templates" class="btn btn-secondary">
            <span>New Agent</span>
          </router-link>
        </div>
      </div>

      <!-- Stats Row -->
      <div class="stats-row fade-up fade-up-d3">
        <StatCard label="Agents Online" :value="store.onlineAgents" trend="+2" :sub="`of ${store.agents.length} registered`" />
        <StatCard label="Active Sessions" :value="store.busyAgents" trend="+3" sub="concurrent" />
        <StatCard label="Total Tokens" :value="store.agents.reduce((s, a) => s + a.tokens_used, 0).toLocaleString()" sub="cumulative" />
        <StatCard label="Uptime" value="99.8%" sub="7d avg" />
      </div>

      <!-- Tag Cloud -->
      <TagCloud class="fade-up fade-up-d4" />

      <!-- Agent Grid -->
      <SectionBar title="Active Agents" class="fade-up fade-up-d5" />
      <div class="agent-grid fade-up fade-up-d6">
        <AgentCard
          v-for="agent in store.agents"
          :key="agent.id"
          :agent="agent"
          @click="openDetail(agent)"
        />
        <div v-if="store.agents.length === 0" class="agent-card header-card flex items-center justify-center text-center" style="grid-column: 1 / -1;">
          <div>
            <div class="text-4xl mb-2 opacity-30">+</div>
            <div class="text-sm font-semibold text-text-secondary">Deploy Your First Agent</div>
            <div class="text-xs text-text-tertiary mt-1">from a template or create custom</div>
          </div>
        </div>
      </div>

      <!-- Bottom Row -->
      <div class="bottom-row fade-up fade-up-d8">
        <ActivityFeed :activities="store.activities" />
        <OpsQueue :agents="store.agents" />
        <ComsPanel />
      </div>
    </main>
  </div>
  <AgentDetail :agent="selectedAgent" @close="closeDetail" />
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
.main {
  flex: 1;
  min-width: 0;
}
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
  transition: all 0.4s cubic-bezier(0.32,0.72,0,1);
}
.btn-secondary {
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.06);
  color: rgba(255,255,255,0.6);
}
.btn-secondary:hover {
  background: rgba(255,255,255,0.07);
  color: #fff;
}

.fade-up { opacity: 0; transform: translateY(16px); animation: fadeUp 0.7s cubic-bezier(0.32,0.72,0,1) forwards; }
.fade-up-d2 { animation-delay: 0.05s; }
.fade-up-d3 { animation-delay: 0.1s; }
.fade-up-d4 { animation-delay: 0.15s; }
.fade-up-d5 { animation-delay: 0.2s; }
.fade-up-d6 { animation-delay: 0.25s; }
.fade-up-d8 { animation-delay: 0.35s; }

@keyframes fadeUp { to { opacity: 1; transform: translateY(0); } }

@media (max-width: 968px) {
  .dashboard { padding: 16px; }
}
@media (max-width: 768px) {
  .dash-header { flex-direction: column; align-items: flex-start; gap: 12px; }
}
</style>
