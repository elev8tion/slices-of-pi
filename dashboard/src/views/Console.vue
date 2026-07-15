<script setup lang="ts">
import { ref, onMounted } from 'vue'
import NavIsland from '@/components/NavIsland.vue'
import Sidebar from '@/components/Sidebar.vue'
import SystemConsole from '@/components/SystemConsole.vue'
import SystemFlixzPanel from '@/components/SystemFlixzPanel.vue'

const activeTab = ref<'logs' | 'flixz'>('logs')
const mossyStatus = ref<'checking' | 'online' | 'offline'>('checking')

const tabs = [
  { id: 'logs' as const, label: 'Logs', icon: '📋' },
  { id: 'flixz' as const, label: 'Flixz', icon: '🎞' },
]

async function checkMossy() {
  try {
    const res = await fetch('/api/voice/tts/status')
    if (res.ok) {
      const data = await res.json()
      mossyStatus.value = data.available ? 'online' : 'offline'
    } else {
      mossyStatus.value = 'offline'
    }
  } catch {
    mossyStatus.value = 'offline'
  }
}

onMounted(() => {
  checkMossy()
  setInterval(checkMossy, 30000) // Poll every 30s
})
</script>

<template>
  <NavIsland />
  <div class="console-page">
    <Sidebar />
    <main class="main">
      <!-- Header -->
      <div class="console-header fade-up">
        <div class="console-title">
          <h1>System Console</h1>
          <p>Live orchestrator log stream — <code class="inline-code">~/.pi/agent/orchestrator.log</code></p>
        </div>
        <div class="mossy-status" :class="mossyStatus">
          <span class="mossy-dot" />
          <span class="mossy-label">
            {{ mossyStatus === 'checking' ? 'TTS...' : mossyStatus === 'online' ? 'Mossy TTS' : 'Mossy Offline' }}
          </span>
        </div>
      </div>

      <!-- Tab bar -->
      <div class="console-tabs">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          class="console-tab"
          :class="{ active: activeTab === tab.id }"
          @click="activeTab = tab.id"
        >
          <span class="console-tab-icon">{{ tab.icon }}</span>
          {{ tab.label }}
        </button>
      </div>

      <!-- Console body -->
      <div class="console-body fade-up fade-up-d2">
        <SystemConsole v-if="activeTab === 'logs'" />
        <SystemFlixzPanel v-else-if="activeTab === 'flixz'" />
      </div>
    </main>
  </div>
</template>

<style scoped>
.console-page {
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
.console-header {
  margin-bottom: 16px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}
.console-title h1 {
  font-family: 'Clash Display', sans-serif;
  font-size: 26px;
  font-weight: 600;
  letter-spacing: -0.03em;
  color: #F0F0F2;
}
.console-title p {
  font-size: 13px;
  color: rgba(255,255,255,0.3);
  font-weight: 500;
  margin-top: 2px;
}
.inline-code {
  font-family: 'JetBrains Mono', Menlo, monospace;
  font-size: 12px;
  background: rgba(255,255,255,0.04);
  padding: 1px 6px;
  border-radius: 4px;
  color: rgba(255,255,255,0.5);
}
.console-body {
  flex: 1;
  min-height: 0;
  border-radius: 16px;
  border: 1px solid rgba(255,255,255,0.05);
  background: rgba(255,255,255,0.01);
  overflow: auto;
}

.console-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 2px;
}

.console-tab {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 6px 14px;
  border-radius: 8px 8px 0 0;
  border: 1px solid transparent;
  background: transparent;
  color: rgba(255,255,255,0.3);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  font-family: inherit;
}

.console-tab:hover {
  color: rgba(255,255,255,0.55);
  background: rgba(255,255,255,0.02);
}

.console-tab.active {
  color: rgba(255,255,255,0.8);
  background: rgba(255,255,255,0.03);
  border-color: rgba(255,255,255,0.06);
  border-bottom-color: transparent;
}

.console-tab-icon {
  font-size: 13px;
}

.fade-up {
  opacity: 0;
  transform: translateY(16px);
  animation: fadeUp 0.7s cubic-bezier(0.32,0.72,0,1) forwards;
}
.fade-up-d2 {
  animation-delay: 0.1s;
}
@keyframes fadeUp {
  to { opacity: 1; transform: translateY(0); }
}

@media (max-width: 968px) {
  .console-page {
    padding: 16px;
    flex-direction: column;
  }
}

.mossy-status {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  border-radius: 8px;
  font-size: 11px;
  font-weight: 500;
  border: 1px solid;
  transition: all 0.3s;
}

.mossy-status.checking {
  background: rgba(255,255,255,0.02);
  border-color: rgba(255,255,255,0.06);
  color: rgba(255,255,255,0.3);
}

.mossy-status.online {
  background: rgba(34,197,94,0.06);
  border-color: rgba(34,197,94,0.15);
  color: #4ADE80;
}

.mossy-status.offline {
  background: rgba(255,255,255,0.02);
  border-color: rgba(255,255,255,0.05);
  color: rgba(255,255,255,0.2);
}

.mossy-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.mossy-status.online .mossy-dot {
  background: #4ADE80;
  box-shadow: 0 0 6px rgba(74,222,128,0.4);
}

.mossy-status.offline .mossy-dot {
  background: rgba(255,255,255,0.2);
}

.mossy-status.checking .mossy-dot {
  background: rgba(255,255,255,0.3);
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 1; }
}
</style>
